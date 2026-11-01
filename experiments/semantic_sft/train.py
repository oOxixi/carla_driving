"""Owner-authorized frozen-text Qwen LoRA training. Never merge, deploy, or read Test labels."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import time

from integration.evidence_provenance import collect_provenance
from .data import HERE, ROOT, PLAN, audit_rows, baseline_guard, canonical_hash, chat_record, load_jsonl, output_directory
from .environment import assistant_token_mask
from .prepare import external_registry, registry_groups
from .synthetic_smoke import production_health


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def artifact_fingerprint(root):
    # Same canonical file-list recipe as B1 teacher_model_fingerprint.py, not path-dependent.
    files = [{'path': p.relative_to(root).as_posix(), 'size_bytes': p.stat().st_size, 'sha256': sha(p)}
             for p in sorted(root.rglob('*')) if p.is_file() and '.cache' not in p.relative_to(root).parts
             and p.relative_to(root).as_posix() != '.model_revision']
    if not files:
        raise ValueError('empty model artifact')
    return {'files': files, 'artifact_sha256': canonical_hash(files)}


def verify_release(folder, expected_manifest_sha, token_audit_path):
    if sha(folder / 'manifest.json') != expected_manifest_sha:
        raise ValueError('release manifest hash changed')
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    required = {'reviewed_rows.jsonl', 'train.jsonl', 'val.jsonl', 'report.json', 'quarantine.jsonl',
                'approval_receipt.json', 'test_exclusion_registry.json', 'supplemental_exclusion_registry.json'}
    hashes = manifest.get('artifact_sha256', {})
    if (manifest.get('split_frozen') is not True or not required <= set(hashes)
            or manifest.get('base_model') != PLAN['base_model'] or manifest.get('base_revision') != PLAN['base_revision']):
        raise ValueError('frozen release identity or artifact list is invalid')
    for name, digest in hashes.items():
        if Path(name).name != name or sha(folder / name) != digest:
            raise ValueError('release artifact changed: ' + name)
    rows = load_jsonl(folder / 'reviewed_rows.jsonl')
    test, supplement = folder / 'test_exclusion_registry.json', folder / 'supplemental_exclusion_registry.json'
    audit = audit_rows(rows, external_protected=external_registry(test),
        supplemental_protected=external_registry(supplement, role='INDEPENDENT_VALIDATION'),
        protected_groups=registry_groups(test) | registry_groups(supplement))
    if not audit['data_ready_for_tokenization']:
        raise ValueError('fresh release data audit failed')
    exports = {split: load_jsonl(folder / (split + '.jsonl')) for split in ('train', 'val')}
    for split in exports:
        if exports[split] != [chat_record(row) for row in rows if row['split'] == split]:
            raise ValueError('export differs from reviewed labels')
    tokens = json.loads(token_audit_path.read_text(encoding='utf-8'))
    bound = {row['sample_id']: (row['source_sha256'], canonical_hash(row['label'])) for row in rows}
    checks = tokens.get('checks', [])
    if (tokens.get('input_sha256') != hashes['reviewed_rows.jsonl'] or tokens.get('all_checked_passed') is not True
            or tokens.get('checked_rows') != len(rows) or tokens.get('skipped_sample_ids')
            or len(checks) != len(rows) or {c.get('sample_id') for c in checks} != set(bound)
            or any(c.get('status') != 'PASS' or c.get('prompt_loss_masked') is not True
                   or (c.get('source_sha256'), c.get('label_sha256')) != bound[c['sample_id']] for c in checks)):
        raise ValueError('full token audit is missing, failed, or bound to other labels')
    return exports, manifest['dataset_version'], audit


def select_idle_gpu(index):
    if type(index) is not int or index not in range(1, 8):
        raise ValueError('GPU0 is protected; select one non-production device')
    line = subprocess.check_output(['nvidia-smi', '-i', str(index),
        '--query-gpu=uuid,memory.used,memory.total', '--format=csv,noheader,nounits'], text=True).strip()
    uuid, used, total = [v.strip() for v in line.split(',')]
    processes = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid',
                                         '--format=csv,noheader,nounits'], text=True)
    if (not uuid.startswith('GPU-') or int(used) > 1024 or int(total) - int(used) < 20 * 1024
            or any(line.split(',')[0].strip() == uuid for line in processes.splitlines())):
        raise ValueError('selected GPU is occupied; never stop or share another task')
    return uuid


def epoch_batches(count, accumulation, seed, epoch):
    indices = list(range(count))
    random.Random(seed + epoch).shuffle(indices)
    return [indices[start:start + accumulation] for start in range(0, count, accumulation)]


def validate_config(config):
    if set(config) != {'epochs', 'learning_rate', 'weight_decay', 'gradient_accumulation', 'max_grad_norm', 'warmup_steps', 'seed'}:
        raise ValueError('unknown or missing training configuration')
    for key in ('epochs', 'gradient_accumulation', 'seed', 'warmup_steps'):
        if type(config[key]) is not int or config[key] < (0 if key in ('seed', 'warmup_steps') else 1):
            raise ValueError('invalid ' + key)
    for key in ('learning_rate', 'weight_decay', 'max_grad_norm'):
        if type(config[key]) not in (int, float) or not math.isfinite(config[key]) or config[key] < 0:
            raise ValueError('invalid ' + key)
    if config['learning_rate'] == 0 or config['max_grad_norm'] == 0:
        raise ValueError('learning rate and gradient clipping must be positive')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-dir', type=Path, required=True)
    parser.add_argument('--release-manifest-sha256', required=True)
    parser.add_argument('--token-audit', type=Path, required=True)
    parser.add_argument('--model-path', type=Path, required=True)
    parser.add_argument('--gpu-index', type=int, choices=range(1, 8), required=True)
    parser.add_argument('--config', type=Path, default=HERE / 'train_config.json')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if not baseline_guard()['passed'] or PLAN['training_entrypoint'] != 'experiments.semantic_sft.train':
        raise ValueError('isolated training plan or baseline guard failed')
    config = json.loads(args.config.read_text(encoding='utf-8'))
    validate_config(config)
    folder = args.release_dir.resolve(strict=True)
    if not folder.is_relative_to((ROOT / 'artifacts/semantic_sft/releases').resolve()):
        raise ValueError('only a frozen release in this isolated workspace is allowed')
    records, version, audit = verify_release(folder, args.release_manifest_sha256, args.token_audit)
    model_path = args.model_path.resolve(strict=True)
    if model_path != Path('/home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B').resolve():
        raise ValueError('only the existing read-only pinned 2B directory is allowed')
    if (model_path / '.model_revision').read_text().strip() != PLAN['base_revision']:
        raise ValueError('base model revision marker mismatch')
    source = collect_provenance(ROOT)
    if source['source']['dirty'] is not False:
        raise ValueError('commit the exact experimental source before starting a training job')
    output = output_directory(args.output_dir)
    import fcntl
    lock_dir = ROOT / 'artifacts/semantic_sft/locks'
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock = (lock_dir / f'gpu{args.gpu_index}.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fingerprint = artifact_fingerprint(model_path)
    if fingerprint['artifact_sha256'] != PLAN['expected_base_artifact_sha256']:
        raise ValueError('actual model artifact fingerprint mismatch')
    gpu_uuid = select_idle_gpu(args.gpu_index)
    health = production_health()
    if (health['model_revision'] != PLAN['base_revision']
            or health['artifact_sha256'] != PLAN['expected_base_artifact_sha256']):
        raise ValueError('production baseline identity changed')
    os.environ.update(CUDA_VISIBLE_DEVICES=gpu_uuid, TOKENIZERS_PARALLELISM='false', HF_HUB_OFFLINE='1')
    output.mkdir(parents=True, exist_ok=False)
    report = dict(scope='FROZEN_TEXT_LORA_CANDIDATE_NOT_SEMANTIC_ACCURACY_OR_GATE', status='LOADING',
        started_at_unix=time.time(), source_provenance=source, dataset_version=version,
        release_manifest_sha256=args.release_manifest_sha256, token_audit_sha256=sha(args.token_audit),
        training_config=config, base_model=PLAN['base_model'], base_revision=PLAN['base_revision'],
        base_fingerprint_verified=True, base_artifact_sha256=fingerprint['artifact_sha256'],
        physical_gpu=args.gpu_index, gpu_uuid=gpu_uuid, train_rows=len(records['train']), val_rows=len(records['val']),
        test_rows_read=0, adapter_only=True, production_health_before=health, epochs=[], optimizer_steps=0, training_started=False,
        formal_performance_gate_passed=False, semantic_accuracy_evaluated=False)
    def save():
        temporary = output / 'report.tmp'
        temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
        temporary.replace(output / 'report.json')
    save()
    (output / 'base_fingerprint.json').write_text(json.dumps(fingerprint, indent=2), encoding='utf-8')
    try:
        import importlib.metadata as md
        import torch
        from transformers import AutoModelForImageTextToText, AutoTokenizer
        from peft import LoraConfig, PeftModel, get_peft_model
        report['packages'] = {name: md.version(name) for name in ('torch', 'transformers', 'peft', 'accelerate')}
        torch.manual_seed(config['seed'])
        if torch.cuda.device_count() != 1:
            raise ValueError('exactly one isolated training GPU must be visible')
        tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
        if not tokenizer.chat_template:
            tokenizer.chat_template = (model_path / 'chat_template.jinja').read_text()
        tokens = {split: [assistant_token_mask(tokenizer, r['messages'], max_length=PLAN['max_sequence_length_candidate'])
                          for r in records[split]] for split in records}
        report['fresh_token_audit_rows'] = sum(len(rows) for rows in tokens.values())
        def load_base():
            return AutoModelForImageTextToText.from_pretrained(str(model_path), local_files_only=True,
                trust_remote_code=False, dtype=torch.bfloat16, device_map={'': 'cuda:0'}, attn_implementation='eager')
        lora = PLAN['candidate_lora']
        model = get_peft_model(load_base(), LoraConfig(r=lora['r'], lora_alpha=lora['alpha'],
            lora_dropout=lora['dropout'], bias='none', target_modules=lora['target_modules_regex'], task_type='CAUSAL_LM'))
        model.config.use_cache = False
        trainable = {name: p for name, p in model.named_parameters() if p.requires_grad}
        if (sum(p.numel() for p in trainable.values()) != 417792
                or any('.lora_' not in name or '.model.language_model.' not in name for name in trainable)):
            raise ValueError('only the checked language-main q/v LoRA parameters may train')
        report['trainable_parameters'] = sum(p.numel() for p in trainable.values())
        before = {name: p.detach().float().cpu().clone() for name, p in trainable.items()}
        optimizer = torch.optim.AdamW(trainable.values(), lr=config['learning_rate'], weight_decay=config['weight_decay'])
        updates = math.ceil(len(tokens['train']) / config['gradient_accumulation']) * config['epochs']
        def lr_scale(step):
            if step < config['warmup_steps']:
                return (step + 1) / max(1, config['warmup_steps'])
            return max(0.0, (updates - step) / max(1, updates - config['warmup_steps']))
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_scale)
        def batch(record, labels=True):
            result = {key: torch.tensor([record[key]], device='cuda:0')
                      for key in ('input_ids', 'labels') if labels or key != 'labels'}
            result['attention_mask'] = torch.ones_like(result['input_ids'])
            return result
        def validation():
            model.eval()
            loss_sum, count = 0.0, 0
            with torch.no_grad():
                for record in tokens['val']:
                    loss = model(**batch(record), use_cache=False).loss.item()
                    if not math.isfinite(loss):
                        raise ValueError('non-finite validation loss')
                    size = sum(v != -100 for v in record['labels'][1:])
                    loss_sum += loss * size
                    count += size
            return loss_sum / count
        report['initial_val_token_cross_entropy'] = validation()
        report['status'] = 'TRAINING'
        report['planned_optimizer_steps'] = updates
        save()
        best_loss = math.inf
        with (output / 'metrics.jsonl').open('x', encoding='utf-8') as metrics:
            for epoch in range(config['epochs']):
                model.train()
                epoch_losses = []
                for indices in epoch_batches(len(tokens['train']), config['gradient_accumulation'], config['seed'], epoch):
                    optimizer.zero_grad(set_to_none=True)
                    losses = []
                    for index in indices:
                        loss = model(**batch(tokens['train'][index]), use_cache=False).loss
                        if not torch.isfinite(loss):
                            raise ValueError('non-finite training loss')
                        (loss / len(indices)).backward()
                        losses.append(loss.item())
                    norm = torch.nn.utils.clip_grad_norm_(trainable.values(), config['max_grad_norm'], error_if_nonfinite=True)
                    used_lr = optimizer.param_groups[0]['lr']
                    optimizer.step()
                    scheduler.step()
                    report['optimizer_steps'] += 1
                    report['training_started'] = True
                    epoch_losses.extend(losses)
                    entry = dict(epoch=epoch + 1, step=report['optimizer_steps'], loss=sum(losses) / len(losses),
                                 gradient_norm=float(norm), learning_rate=used_lr, samples=len(indices))
                    metrics.write(json.dumps(entry) + '\n'); metrics.flush()
                    report['latest_update'] = entry
                    save()
                    print(json.dumps(entry), flush=True)
                val_loss = validation()
                adapter = output / f'epoch_{epoch + 1}_adapter'
                model.save_pretrained(adapter, safe_serialization=True)
                summary = dict(epoch=epoch + 1, train_mean_example_loss=sum(epoch_losses) / len(epoch_losses),
                               val_token_cross_entropy=val_loss, adapter=adapter.name)
                report['epochs'].append(summary)
                if val_loss < best_loss:
                    best_loss = val_loss
                    report['best_adapter'] = adapter.name
                    report['best_val_token_cross_entropy'] = val_loss
                    with torch.no_grad():
                        reference = model(**batch(tokens['val'][0], labels=False), use_cache=False, logits_to_keep=1).logits.float().cpu()
                save()
        report['changed_adapter_tensors'] = sum(not torch.equal(before[name], p.detach().float().cpu()) for name, p in trainable.items())
        if not report['changed_adapter_tensors']:
            raise ValueError('no adapter parameters changed')
        report['peak_cuda_bytes'] = torch.cuda.max_memory_allocated()
        loss = None
        del model, optimizer, scheduler, trainable, before
        gc.collect(); torch.cuda.empty_cache()
        report['status'] = 'VERIFYING_RELOAD'
        save()
        selected = output / report['best_adapter']
        reloaded = PeftModel.from_pretrained(load_base(), str(selected), is_trainable=False)
        reloaded.eval()
        with torch.no_grad():
            actual = reloaded(**batch(tokens['val'][0], labels=False), use_cache=False, logits_to_keep=1).logits.float().cpu()
        report['reload_max_absolute_logit_error'] = (reference - actual).abs().max().item()
        if not torch.allclose(reference, actual, atol=0.05, rtol=0.01):
            raise ValueError('saved adapter reload output mismatch')
        report['adapter_sha256'] = {p.name: sha(p) for p in selected.iterdir() if p.is_file()}
        report['production_health_after'] = production_health()
        if report['production_health_after'] != health:
            raise ValueError('production identity/health changed')
        report['status'] = 'COMPLETED'
    except Exception as exc:
        report.update(status='FAILED', error=type(exc).__name__ + ': ' + str(exc))
        raise
    finally:
        report['last_report_at_unix'] = time.time()
        save()
    print(json.dumps(dict(status=report['status'], output=str(output), formal_performance_gate_passed=False)), flush=True)


if __name__ == '__main__':
    main()
