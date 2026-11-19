"""Fresh matched three-arm JSON grammar control; no semantic answer repair or deployment."""
import argparse
import copy
import gc
import json
import os
from pathlib import Path
import time

from qwen_service.task_understanding import TASK_SCHEMA
from .data import ROOT, PLAN, canonical_hash, load_jsonl, output_directory, baseline_guard
from .compare_7b import encode_prompt, verify_reference
from .diagnose import diagnose_case
from .semantic_metrics import summarize, baseline_regressions
from .synthetic_smoke import production_health
from .train import sha, select_idle_gpu, artifact_fingerprint, verify_release
from integration.evidence_provenance import collect_provenance


CONDITION_GUIDANCE = (
    "\n提交JSON前逐步核查condition：先区分单纯顺序与真正的触发前提。"
    "安全间隙、放行、到达指定位置或前序动作完成等明确前提，不可因为已有安全层或已有步骤顺序而省略。"
    "把前提绑定到它实际限制的步骤；同一前提覆盖明确并列任务时各自保留，"
    "不要把它挪给后面的独立任务。只引用原文中的前提部分，不把动作本身或目标描述抄成条件。"
    "只有先后顺序、没有明确前提时填null。其余字段仍按原协议完整输出。"
)


def with_condition_guidance(record):
    updated = copy.deepcopy(record)
    updated['messages'][0]['content'] += CONDITION_GUIDANCE
    return updated


def control_schema():
    # No source spans, gold labels, expected step count, or example answers enter this grammar.
    schema=copy.deepcopy(TASK_SCHEMA)
    def canonical_properties(value):
        if isinstance(value,dict):
            for key,item in list(value.items()):
                if key=='properties': value[key]={n:item[n] for n in sorted(item)}
                if key=='required': value[key]=sorted(item)
                canonical_properties(value[key])
        elif isinstance(value,list):
            for item in value: canonical_properties(item)
    canonical_properties(schema)
    return schema


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu-index',type=int,choices=range(1,8),required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--condition-prompt', action='store_true',
        help='Run only V5 with the condition prompt addendum against the completed V5 grammar baseline')
    args=parser.parse_args()
    if not baseline_guard()['passed']: raise ValueError('isolated branch guard failed')
    provenance=collect_provenance(ROOT)
    if provenance['source']['dirty']: raise ValueError('freeze source before running')
    artifacts=ROOT/'artifacts/semantic_sft'
    previous_dir=artifacts/'semantic_text_lora_v5_20261102_01'
    previous=json.loads((previous_dir/'report.json').read_text())
    release=artifacts/'releases/semantic_text_sft_v3_20261102'
    records,version,_=verify_release(release,previous['release_manifest_sha256'],artifacts/'frozen_329_v3_token_audit_20261102/report.json')
    if len(records['val'])!=75: raise ValueError('wrong Dev cohort')
    adapter=previous_dir/previous['reload_verified_adapter']
    if any(sha(adapter/n)!=h for n,h in previous['adapter_sha256'].items()): raise ValueError('V5 checkpoint changed')
    paths={'2B':Path('/home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B')}
    if not args.condition_prompt:
        download=json.loads((artifacts/'seven_b_comparison_20261103/download.json').read_text())
        if download['status']!='COMPLETED' or download['revision']!='cc594898137f460bfe9f0759e9844b3ce807cfb5':
            raise ValueError('wrong 7B artifact')
        paths['7B']=Path(download['destination'])
    fingerprints={key:artifact_fingerprint(path) for key,path in paths.items()}
    if fingerprints['2B']['artifact_sha256']!=PLAN['expected_base_artifact_sha256']: raise ValueError('2B fingerprint mismatch')
    if '7B' in fingerprints:
        expected7=json.loads((artifacts/'seven_b_comparison_20261103/official_weights.json').read_text())['sha256']
        actual7={f['path']:f['sha256'] for f in fingerprints['7B']['files']}
        if any(actual7.get(n)!=h for n,h in expected7.items()): raise ValueError('7B official shard hash mismatch')
    import fcntl
    lock=(artifacts/f'locks/gpu{args.gpu_index}.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    gpu=select_idle_gpu(args.gpu_index)
    os.environ.update(CUDA_VISIBLE_DEVICES=gpu,HF_HUB_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
    output=output_directory(args.output_dir);output.mkdir(parents=True,exist_ok=False)
    report=dict(scope='MATCHED_GRAMMAR_CONTROL_DEV_NOT_FINAL_TEST_OR_DRIVING',status='LOADING',
        source_provenance=provenance,dataset_version=version,release_manifest_sha256=previous['release_manifest_sha256'],
        model_fingerprints={k:v['artifact_sha256'] for k,v in fingerprints.items()},gpu_uuid=gpu,
        system_prompt_sha256=previous['system_prompt_sha256'],schema_sha256=canonical_hash(control_schema()),
        production_before=production_health(),started_at_unix=time.time(),arms={},image_inputs=0,test_labels_read=0,
        optimizer_steps=0,formal_performance_gate_passed=False,
        protocol=dict(grammar='xgrammar TASK_SCHEMA any_order=False canonical property order',max_new_tokens=1536,do_sample=False,
                      num_beams=1,repetition_penalty=1.0,attention='eager',dtype='bfloat16',retries=0))
    baseline=None
    if args.condition_prompt:
        import hashlib
        reference=artifacts/'grammar_control_20261104_02'
        reference_report=json.loads((reference/'report.json').read_text())
        if (reference_report['status']!='COMPLETED' or any(reference_report[k]!=report[k] for k in
                ('release_manifest_sha256','schema_sha256','system_prompt_sha256','protocol'))
                or reference_report['model_fingerprints']['2B']!=report['model_fingerprints']['2B']):
            raise ValueError('condition prompt comparison requires the matched completed V5 baseline')
        baseline=verify_reference(load_jsonl(reference/'2B_V5_LORA.jsonl'),records['val'])
        report['prompt_only_experiment']=True
        report['baseline_sha256']=sha(reference/'2B_V5_LORA.jsonl')
        report['baseline_summary']=summarize(baseline)
        report['adapter_sha256']=previous['adapter_sha256']
        report['candidate_system_prompt_sha256']=hashlib.sha256(
            with_condition_guidance(records['val'][0])['messages'][0]['content'].encode()).hexdigest()
    def save():
        p=output/'report.tmp';p.write_text(json.dumps(report,indent=2));p.replace(output/'report.json')
    save()
    try:
        import importlib.metadata as md
        import torch
        import xgrammar as xgr
        from xgrammar.contrib.hf import LogitsProcessor
        from transformers import AutoTokenizer,AutoModelForImageTextToText
        from peft import PeftModel
        report['packages']={p:md.version(p) for p in ['torch','transformers','xgrammar','peft']}
        families={r['sample_id']:r['semantic_family'] for r in load_jsonl(release/'reviewed_rows.jsonl')}
        groups=[('2B',['2B_V5_CONDITION_PROMPT'])] if args.condition_prompt else [('7B',['7B_BASE']),('2B',['2B_BASE','2B_V5_LORA'])]
        for key,arms in groups:
            torch.manual_seed(previous['training_config']['seed'])
            path=paths[key]
            t=AutoTokenizer.from_pretrained(str(path),local_files_only=True)
            if not t.chat_template:
                t.chat_template=json.loads((path/'chat_template.json').read_text())['chat_template'] if (path/'chat_template.json').exists() else (path/'chat_template.jinja').read_text()
            model=AutoModelForImageTextToText.from_pretrained(str(path),local_files_only=True,
                dtype=torch.bfloat16,device_map={'':'cuda:0'},attn_implementation='eager')
            if key=='2B': model=PeftModel.from_pretrained(model,str(adapter),is_trainable=False)
            model.eval();model.requires_grad_(False)
            eos=model.generation_config.eos_token_id;eos_ids=[eos] if isinstance(eos,int) else eos
            info=xgr.TokenizerInfo.from_huggingface(t,vocab_size=model.get_output_embeddings().weight.shape[0],stop_token_ids=eos_ids)
            grammar=xgr.GrammarCompiler(info).compile_json_schema(control_schema(),any_order=False)
            for arm in arms:
                from contextlib import nullcontext
                scored=[]
                report.update(status='GENERATING',current_arm=arm,done=0);save()
                with (output/(arm+'.jsonl')).open('x',encoding='utf-8') as stream:
                    for record in records['val']:
                        prefix=encode_prompt(t,with_condition_guidance(record) if args.condition_prompt else record)
                        if len(prefix)+1536>4096: raise ValueError('matched context budget exceeded')
                        inputs=dict(input_ids=torch.tensor([prefix],device='cuda:0'))
                        inputs['attention_mask']=torch.ones_like(inputs['input_ids'])
                        with torch.inference_mode(), (model.disable_adapter() if arm=='2B_BASE' else nullcontext()):
                            result=model.generate(**inputs,do_sample=False,num_beams=1,max_new_tokens=1536,
                                repetition_penalty=1.0,use_cache=True,eos_token_id=eos_ids,
                                pad_token_id=t.pad_token_id if t.pad_token_id is not None else eos_ids[0],
                                logits_processor=[LogitsProcessor(grammar)])
                        new=result[0,len(prefix):].tolist();raw=t.decode(new,skip_special_tokens=True)
                        gold=json.loads(record['messages'][-1]['content'])
                        item=dict(sample_id=record['sample_id'],semantic_family=families[record['sample_id']],raw=raw,
                            prompt_ids_sha256=canonical_hash(prefix),expected_label_sha256=canonical_hash(gold),
                            **diagnose_case(record['messages'][1]['content'],raw,gold,complete=bool(new) and new[-1] in eos_ids))
                        scored.append(item);stream.write(json.dumps(item,ensure_ascii=False)+'\n');stream.flush()
                        if item['score']['checks']['complete'] and not item['score']['checks']['schema_valid']:
                            raise RuntimeError('completed generation violated grammar schema; abort control, not a model accuracy result')
                        report.update(done=len(scored));report['arms'][arm]=summarize(scored);save()
                        print(json.dumps(dict(arm=arm,done=len(scored),total=75)),flush=True)
            if baseline is not None:
                report['regressions_vs_v5']=baseline_regressions(scored,baseline)
                before={r['sample_id']:r['score']['checks']['condition_exact'] for r in baseline}
                report['condition_pairs']={
                    'recovered':[r['sample_id'] for r in scored if not before[r['sample_id']] and r['score']['checks']['condition_exact']],
                    'lost':[r['sample_id'] for r in scored if before[r['sample_id']] and not r['score']['checks']['condition_exact']],
                }
            del model,result;gc.collect();torch.cuda.empty_cache()
        report['production_after']=production_health()
        if report['production_after']!=report['production_before']: raise ValueError('production identity changed')
        report['status']='COMPLETED'
    except Exception as exc:
        report.update(status='FAILED',error=type(exc).__name__+': '+str(exc));raise
    finally:
        report['last_report_at_unix']=time.time();save()


if __name__=='__main__': main()
