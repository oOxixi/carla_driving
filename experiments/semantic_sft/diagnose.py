"""Autoregressive TRAIN diagnostics, not retraining, deployment, or a promotion gate."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import time

from .data import HERE, ROOT, PLAN, baseline_guard, canonical_hash, load_jsonl, output_directory
from .environment import assistant_token_mask
from .semantic_metrics import score_text, summarize
from .synthetic_smoke import production_health
from .train import artifact_fingerprint, select_idle_gpu, sha, verify_release
from integration.evidence_provenance import collect_provenance


def prompt_only(tokens):
    n = tokens['prompt_tokens']
    if (type(n) is not int or not 0 < n < len(tokens['input_ids'])
            or len(tokens['labels']) != len(tokens['input_ids'])
            or any(v != -100 for v in tokens['labels'][:n])
            or any(v == -100 for v in tokens['labels'][n:])):
        raise ValueError('cannot prove gold-free generation prefix')
    return tokens['input_ids'][:n]


def diagnose_case(source, raw, expected, *, complete):
    score = score_text(source, raw, expected, complete=complete)
    checks, observed = score['checks'], score['observed']
    tags, differences = [], []
    if not complete:
        tags.append('INCOMPLETE_GENERATION')
    if not checks['json_valid']:
        tags.append('JSON_INVALID')
    elif not checks['schema_valid']:
        tags.append('SCHEMA_INVALID')
    if isinstance(observed, dict) and isinstance(observed.get('steps'), list):
        actions = [s.get('action') if isinstance(s, dict) else None for s in observed['steps']]
        if actions != [s['action'] for s in expected['steps']]:
            tags.append('ACTION_SEQUENCE_MISMATCH')
    aligned = checks['raw_action_order_exact'] and checks['schema_valid']
    if aligned:
        for i, (gold, actual) in enumerate(zip(expected['steps'], observed['steps'])):
            for field in ('condition', 'direction', 'target_text', 'speed_kph', 'gap_m'):
                if gold[field] == actual[field] or (type(gold[field]) in (int, float)
                        and type(actual[field]) in (int, float) and abs(gold[field] - actual[field]) <= 1e-6):
                    continue
                if field == 'condition':
                    tag = 'CONDITION_EXTRA' if gold[field] is None else 'CONDITION_MISSING' if actual[field] is None else 'CONDITION_SPAN_MISMATCH'
                else:
                    tag = field.upper() + '_MISMATCH'
                tags.append(tag)
                differences.append(dict(step=i+1, field=field, expected=gold[field], observed=actual[field]))
    if checks['schema_valid']:
        for key in ('prohibited_actions', 'requires_confirmation'):
            if expected[key] != observed[key]:
                tags.append(key.upper() + '_MISMATCH')
        if not checks['extraction_valid']:
            tags.append('LITERAL_OR_CONTRACT_REJECTION')
    return dict(score=score, diagnostic=dict(tags=sorted(set(tags)),
        slots_compared_only_when_actions_aligned_and_schema_valid=aligned, slot_differences=differences,
        note='Span differences are literal mismatches, not independently judged semantic equivalence.'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--release-dir', type=Path, required=True)
    parser.add_argument('--token-audit', type=Path, required=True)
    parser.add_argument('--gpu-index', type=int, choices=range(1, 8), required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if not baseline_guard()['passed']:
        raise ValueError('isolated branch guard failed')
    run_dir, release = args.run_dir.resolve(strict=True), args.release_dir.resolve(strict=True)
    for path in (run_dir, release):
        if not path.is_relative_to((ROOT / 'artifacts/semantic_sft').resolve()):
            raise ValueError('diagnostics must use artifacts of this isolated workspace')
    previous = json.loads((run_dir / 'report.json').read_text())
    if (previous['status'] != 'COMPLETED' or previous['base_model'] != PLAN['base_model']
            or previous['base_revision'] != PLAN['base_revision']):
        raise ValueError('only completed pinned 2B runs may be diagnosed')
    records, version, _ = verify_release(release, previous['release_manifest_sha256'], args.token_audit)
    if version != previous['dataset_version'] or len(records['train']) != previous['train_rows']:
        raise ValueError('diagnostic cohort differs from original training run')
    prompt_sha = hashlib.sha256(records['train'][0]['messages'][0]['content'].encode()).hexdigest()
    if previous.get('system_prompt_sha256', prompt_sha) != prompt_sha:
        raise ValueError('diagnostic prompt differs from original run')
    adapter_name = previous['reload_verified_adapter']
    if Path(adapter_name).name != adapter_name:
        raise ValueError('invalid adapter directory')
    adapter = run_dir / adapter_name
    if any(sha(adapter / name) != digest for name, digest in previous['adapter_sha256'].items()):
        raise ValueError('checkpoint files differ from verified training result')
    provenance = collect_provenance(ROOT)
    if provenance['source']['dirty']:
        raise ValueError('freeze diagnostic source before running')
    output = output_directory(args.output_dir)
    import fcntl
    locks = ROOT / 'artifacts/semantic_sft/locks'
    locks.mkdir(parents=True, exist_ok=True)
    lock = (locks / f'gpu{args.gpu_index}.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    uuid = select_idle_gpu(args.gpu_index)
    model_path = Path('/home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B')
    fingerprint = artifact_fingerprint(model_path)['artifact_sha256']
    if fingerprint != PLAN['expected_base_artifact_sha256']:
        raise ValueError('actual base fingerprint mismatch')
    health = production_health()
    if health['model_revision'] != PLAN['base_revision'] or health['artifact_sha256'] != fingerprint:
        raise ValueError('production identity changed')
    os.environ.update(CUDA_VISIBLE_DEVICES=uuid, HF_HUB_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    output.mkdir(parents=True, exist_ok=False)
    report = dict(scope='TRAIN_MEMORIZATION_DIAGNOSTIC_NOT_GENERALIZATION_OR_PROMOTION', status='LOADING',
        source_provenance=provenance, training_report_sha256=sha(run_dir / 'report.json'),
        checkpoint=adapter_name, checkpoint_role=previous['adapter_artifact_role'], dataset_version=version,
        release_manifest_sha256=previous['release_manifest_sha256'], scorer_sha256=sha(HERE/'semantic_metrics.py'),
        physical_gpu=args.gpu_index, gpu_uuid=uuid, base_fingerprint=fingerprint,
        cases=len(records['train']), done=0, optimizer_steps=0, training_started=False, test_labels_read=0,
        system_prompt_sha256=prompt_sha,
        generation_policy=dict(do_sample=False, num_beams=1, max_new_tokens=1536, schema_constraint=False, retries=0),
        production_health_before=health, started_at_unix=time.time(), formal_performance_gate_passed=False)
    def save():
        temp = output / 'report.tmp'
        temp.write_text(json.dumps(report, indent=2), encoding='utf-8')
        temp.replace(output / 'report.json')
    save()
    try:
        import torch
        from transformers import AutoModelForImageTextToText, AutoTokenizer
        from peft import PeftModel
        torch.manual_seed(previous['training_config']['seed'])
        if torch.cuda.device_count() != 1:
            raise ValueError('exactly one isolated GPU is required')
        tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
        if not tokenizer.chat_template:
            tokenizer.chat_template = (model_path / 'chat_template.jinja').read_text()
        base = AutoModelForImageTextToText.from_pretrained(str(model_path), local_files_only=True,
            trust_remote_code=False, dtype=torch.bfloat16, device_map={'': 'cuda:0'}, attn_implementation='eager')
        model = PeftModel.from_pretrained(base, str(adapter), is_trainable=False)
        model.eval()
        if any(p.requires_grad for p in model.parameters()):
            raise ValueError('inference diagnostics may not create trainable parameters')
        eos = model.generation_config.eos_token_id
        eos_ids = [eos] if isinstance(eos, int) else eos
        if not eos_ids:
            raise ValueError('missing EOS contract')
        families = {r['sample_id']: r['semantic_family'] for r in load_jsonl(release / 'reviewed_rows.jsonl')}
        report['status'] = 'GENERATING_TRAIN'
        scored = []
        with (output / 'train_generations.jsonl').open('x', encoding='utf-8') as stream:
            for record in records['train']:
                tokenized = assistant_token_mask(tokenizer, record['messages'], max_length=PLAN['max_sequence_length_candidate'])
                prefix = prompt_only(tokenized)
                if len(prefix) + 1536 > PLAN['max_sequence_length_candidate']:
                    raise ValueError('prompt exceeds matched generation budget')
                inputs = dict(input_ids=torch.tensor([prefix], device='cuda:0'))
                inputs['attention_mask'] = torch.ones_like(inputs['input_ids'])
                with torch.inference_mode():
                    result = model.generate(**inputs, do_sample=False, num_beams=1, max_new_tokens=1536,
                        use_cache=True, eos_token_id=eos_ids,
                        pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else eos_ids[0])
                new = result[0, len(prefix):].tolist()
                raw = tokenizer.decode(new, skip_special_tokens=True)
                expected = json.loads(record['messages'][-1]['content'])
                item = dict(sample_id=record['sample_id'], semantic_family=families[record['sample_id']], raw=raw,
                    generated_tokens=len(new), prompt_ids_sha256=canonical_hash(prefix), expected_label_sha256=canonical_hash(expected),
                    **diagnose_case(record['messages'][1]['content'], raw, expected, complete=bool(new) and new[-1] in eos_ids))
                scored.append(item)
                stream.write(json.dumps(item, ensure_ascii=False) + '\n'); stream.flush()
                report.update(done=len(scored), train_summary=summarize(scored),
                              error_case_counts=dict(Counter(t for r in scored for t in r['diagnostic']['tags'])))
                save()
                print(json.dumps(dict(done=len(scored), total=len(records['train']))), flush=True)
        report['production_health_after'] = production_health()
        if report['production_health_after'] != health or sha(run_dir/'report.json') != report['training_report_sha256']:
            raise ValueError('production or original training evidence changed')
        if any(sha(adapter/name) != digest for name, digest in previous['adapter_sha256'].items()):
            raise ValueError('original checkpoint changed')
        report['status'] = 'COMPLETED'
    except Exception as exc:
        report.update(status='FAILED', error=type(exc).__name__ + ': ' + str(exc))
        raise
    finally:
        report['last_report_at_unix'] = time.time()
        save()


if __name__ == '__main__':
    main()
