"""Matched text-only 7B Dev comparison. Never deploy, train, repair, or evaluate Final Test."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from .data import HERE, ROOT, PLAN, baseline_guard, canonical_hash, load_jsonl, output_directory
from .diagnose import diagnose_case, prompt_only
from .environment import assistant_token_mask
from .semantic_metrics import score_text, summarize, baseline_regressions
from .synthetic_smoke import production_health
from .train import sha, select_idle_gpu, verify_release, artifact_fingerprint
from integration.evidence_provenance import collect_provenance


def verify_reference(rows, records):
    expected = {r['sample_id']: r for r in records}
    if len(rows) != len(expected) or len({r['sample_id'] for r in rows}) != len(rows) or {r['sample_id'] for r in rows} != set(expected):
        raise ValueError('comparison arms must cover exactly the same unique Dev IDs')
    for row in rows:
        record = expected[row['sample_id']]
        checked = score_text(record['messages'][1]['content'], row['raw'],
            json.loads(record['messages'][-1]['content']), complete=row['score']['checks']['complete'])
        if checked['checks'] != row['score']['checks']:
            raise ValueError('cached reference scores do not match raw generations and current labels')
    return rows


def inference_messages(record):
    messages = record['messages']
    if [m['role'] for m in messages] != ['system', 'user', 'assistant']:
        raise ValueError('only frozen single-turn records are allowed')
    return messages[:-1]


def encode_prompt(tokenizer, record):
    text = tokenizer.apply_chat_template(inference_messages(record), tokenize=False,
        add_generation_prompt=True, enable_thinking=False)
    ids = tokenizer(text, add_special_tokens=False)['input_ids']
    if not isinstance(ids, list) or not ids or any(type(i) is not int for i in ids):
        raise ValueError('tokenizer did not return a flat prompt token list')
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-manifest', type=Path, required=True)
    parser.add_argument('--reference-run-dir', type=Path, required=True)
    parser.add_argument('--release-dir', type=Path, required=True)
    parser.add_argument('--token-audit', type=Path, required=True)
    parser.add_argument('--gpu-index', type=int, choices=range(1, 8), required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if not baseline_guard()['passed']:
        raise ValueError('isolated experiment guard failed')
    source = collect_provenance(ROOT)
    if source['source']['dirty']:
        raise ValueError('freeze comparison source before running')
    identity = json.loads(args.model_manifest.read_text())
    if identity['status'] != 'COMPLETED' or identity['model_id'] != 'Qwen/Qwen2.5-VL-7B-Instruct' or len(identity['revision']) != 40:
        raise ValueError('a completed exact-revision 7B download is required')
    model_path = Path(identity['destination']).resolve(strict=True)
    if not model_path.is_relative_to((ROOT/'artifacts/semantic_sft/models').resolve()):
        raise ValueError('use an isolated experimental model directory')
    if json.loads((model_path/'config.json').read_text())['model_type'] != 'qwen2_5_vl':
        raise ValueError('wrong 7B architecture')
    run = args.reference_run_dir.resolve(strict=True)
    previous = json.loads((run/'report.json').read_text())
    if previous['status'] != 'COMPLETED' or previous['base_model'] != PLAN['base_model'] or previous['base_revision'] != PLAN['base_revision']:
        raise ValueError('wrong 2B reference run')
    records, version, _ = verify_release(args.release_dir, previous['release_manifest_sha256'], args.token_audit)
    if len(records['val']) != 75:
        raise ValueError('expected the frozen Dev75 cohort')
    refs = {name: verify_reference(load_jsonl(run/file), records['val']) for name, file in
            [('2B_BASE','dev_base_generations.jsonl'), ('2B_V5_LORA','dev_epoch_3_generations.jsonl')]}
    ref_hashes = {file: sha(run/file) for file in ('report.json','dev_base_generations.jsonl','dev_epoch_3_generations.jsonl')}
    output = output_directory(args.output_dir)
    import fcntl
    locks = ROOT/'artifacts/semantic_sft/locks'
    locks.mkdir(parents=True, exist_ok=True)
    lock = (locks/f'gpu{args.gpu_index}.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fingerprint = artifact_fingerprint(model_path)
    uuid = select_idle_gpu(args.gpu_index)
    health = production_health()
    if health['model_revision'] != PLAN['base_revision'] or health['artifact_sha256'] != PLAN['expected_base_artifact_sha256']:
        raise ValueError('production model identity changed')
    os.environ.update(CUDA_VISIBLE_DEVICES=uuid, HF_HUB_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    output.mkdir(parents=True, exist_ok=False)
    report = dict(scope='MATCHED_TEXT_DEV_COMPARISON_NOT_FINAL_TEST_OR_DRIVING_GATE', status='LOADING',
        model_id=identity['model_id'], revision=identity['revision'], model_fingerprint=fingerprint['artifact_sha256'],
        source_provenance=source, dataset_version=version, release_manifest_sha256=previous['release_manifest_sha256'],
        reference_file_sha256=ref_hashes, reference_run=str(run), references_reused_not_rerun=True,
        reference_training_source=previous['source_provenance'], image_inputs=0, test_labels_read=0,
        optimizer_steps=0, production_health_before=health, physical_gpu=args.gpu_index, gpu_uuid=uuid,
        done=0, total=75, started_at_unix=time.time(), formal_performance_gate_passed=False,
        generation_policy=dict(do_sample=False,num_beams=1,max_new_tokens=1536,repetition_penalty=1.0,grammar=False,retries=0,dtype='bfloat16'),
        system_prompt_sha256=hashlib.sha256(records['val'][0]['messages'][0]['content'].encode()).hexdigest(),
        summaries={name:summarize(rows) for name, rows in refs.items()})
    def save():
        path = output/'report.tmp'
        path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        path.replace(output/'report.json')
    save()
    (output/'model_fingerprint.json').write_text(json.dumps(fingerprint,indent=2))
    try:
        import importlib.metadata as md
        import torch
        from transformers import AutoTokenizer, AutoModelForImageTextToText
        config2b = Path('/home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B')
        for path in (config2b/'generation_config.json', config2b/'config.json'):
            if path.exists() and json.loads(path.read_text()).get('repetition_penalty',1.0) != 1.0:
                raise ValueError('cached 2B repetition penalty differs from the matched 1.0 protocol')
        report['packages'] = {p:md.version(p) for p in ('torch','transformers','tokenizers')}
        torch.manual_seed(previous['training_config']['seed'])
        tokenizer2b = AutoTokenizer.from_pretrained('/home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B',local_files_only=True)
        if not tokenizer2b.chat_template:
            tokenizer2b.chat_template = Path('/home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B/chat_template.jinja').read_text()
        prefixes = {r['sample_id']:canonical_hash(prompt_only(assistant_token_mask(tokenizer2b,r['messages']))) for r in records['val']}
        if any(r['prompt_ids_sha256'] != prefixes[r['sample_id']] for rows in refs.values() for r in rows):
            raise ValueError('reference prompts differ from the matched frozen protocol')
        tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
        if not tokenizer.chat_template:
            tokenizer.chat_template = (json.loads((model_path/'chat_template.json').read_text())['chat_template']
                if (model_path/'chat_template.json').exists() else (model_path/'chat_template.jinja').read_text())
        model = AutoModelForImageTextToText.from_pretrained(str(model_path),local_files_only=True,
            trust_remote_code=False,dtype=torch.bfloat16,device_map={'':'cuda:0'},attn_implementation='eager')
        model.eval(); model.requires_grad_(False)
        eos = model.generation_config.eos_token_id
        eos_ids = [eos] if isinstance(eos,int) else eos
        if not eos_ids:
            raise ValueError('missing generation EOS contract')
        families = {r['sample_id']:r['semantic_family'] for r in load_jsonl(args.release_dir/'reviewed_rows.jsonl')}
        scored = []
        report['status'] = 'GENERATING_7B_DEV'
        with (output/'dev_7b_generations.jsonl').open('x',encoding='utf-8') as stream:
            for record in records['val']:
                prefix = encode_prompt(tokenizer,record)
                inputs = dict(input_ids=torch.tensor([prefix],device='cuda:0'))
                inputs['attention_mask'] = torch.ones_like(inputs['input_ids'])
                with torch.inference_mode():
                    result = model.generate(**inputs,do_sample=False,num_beams=1,max_new_tokens=1536,repetition_penalty=1.0,use_cache=True,
                        eos_token_id=eos_ids,pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else eos_ids[0])
                new = result[0,len(prefix):].tolist()
                raw = tokenizer.decode(new,skip_special_tokens=True)
                expected = json.loads(record['messages'][-1]['content'])
                item = dict(sample_id=record['sample_id'],semantic_family=families[record['sample_id']],raw=raw,
                    prompt_ids_sha256=canonical_hash(prefix),expected_label_sha256=canonical_hash(expected),generated_tokens=len(new),
                    **diagnose_case(record['messages'][1]['content'],raw,expected,complete=bool(new) and new[-1] in eos_ids))
                scored.append(item)
                stream.write(json.dumps(item,ensure_ascii=False)+'\n'); stream.flush()
                report.update(done=len(scored),seven_b_progress_summary=summarize(scored)); save()
                print(json.dumps(dict(done=len(scored),total=75)),flush=True)
        report['summaries']['7B_BASE'] = summarize(scored)
        report['regressions_vs'] = {name:baseline_regressions(scored,rows) for name,rows in refs.items()}
        report['production_health_after'] = production_health()
        if report['production_health_after'] != health or any(sha(run/file)!=digest for file,digest in ref_hashes.items()):
            raise ValueError('production or reference evidence changed')
        report['status'] = 'COMPLETED'
    except Exception as exc:
        report.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        report['last_report_at_unix']=time.time(); save()


if __name__ == '__main__':
    main()
