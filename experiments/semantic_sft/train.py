"""Owner-authorized frozen-text Qwen LoRA training. Never merge, deploy, or read Test labels."""
from __future__ import annotations

import argparse
from contextlib import nullcontext
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
from .data import HERE, ROOT, PLAN, SFT_SYSTEM, audit_rows, baseline_guard, canonical_hash, chat_record, load_jsonl, output_directory
from .environment import assistant_token_mask
from .prepare import external_registry, registry_groups
from .synthetic_smoke import production_health
from .semantic_metrics import score_text, summarize, baseline_regressions, selection_rank


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
    prompt = manifest.get('system_prompt', SFT_SYSTEM)
    if (not isinstance(prompt, str) or not prompt.strip()
            or ('system_prompt' in manifest and manifest.get('system_prompt_sha256') != hashlib.sha256(prompt.encode()).hexdigest())):
        raise ValueError('release prompt identity is invalid')
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
        if exports[split] != [chat_record(row, system_prompt=prompt) for row in rows if row['split'] == split]:
            raise ValueError('export differs from reviewed labels')
    tokens = json.loads(token_audit_path.read_text(encoding='utf-8'))
    if tokens.get('system_prompt_sha256', hashlib.sha256(SFT_SYSTEM.encode()).hexdigest()) != hashlib.sha256(prompt.encode()).hexdigest():
        raise ValueError('token audit used a different system prompt')
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


def semantic_evaluation_epochs(requested, total, *, semantic, train_recall):
    if (requested is not None or train_recall) and not semantic:
        raise ValueError('staged semantic and Train recall evaluation require --semantic-validation')
    if requested is None:
        return set(range(1, total + 1))
    if (not requested or any(type(n) is not int or not 1 <= n <= total for n in requested)
            or len(set(requested)) != len(requested) or total not in requested):
        raise ValueError('evaluation epochs must be unique, in range, and include the final epoch')
    return set(requested)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-dir', type=Path, required=True)
    parser.add_argument('--release-manifest-sha256', required=True)
    parser.add_argument('--token-audit', type=Path, required=True)
    parser.add_argument('--model-path', type=Path, required=True)
    parser.add_argument('--gpu-index', type=int, choices=range(1, 8), required=True)
    parser.add_argument('--config', type=Path, default=HERE / 'train_config.json')
    parser.add_argument('--semantic-validation', action='store_true', help='generate on all Dev rows; reject lost baseline-correct cases; keep legacy loss selection only when omitted')
    parser.add_argument('--group-action-weighting', action='store_true', help='Train-only group-balanced rare-action loss weights; each row is still visited once')
    parser.add_argument('--sequence-group-weighting', action='store_true', help='Add a bounded Train-only boost for rare ordered action transitions')
    parser.add_argument('--train-hard-case-audit', type=Path, help='Opt-in frozen Train replay errors; bounded sample weighting only, never Dev/Test')
    parser.add_argument('--gradient-checkpointing', action='store_true', help='Non-reentrant training activation recomputation; legacy default unchanged')
    parser.add_argument('--semantic-evaluation-epochs', type=int, nargs='+', help='Generate Dev semantics only at these epochs; final epoch is required')
    parser.add_argument('--train-recall-evaluation', action='store_true', help='Also generate all seen Train rows at semantic checkpoints, without using them to select the adapter')
    field_mode = parser.add_mutually_exclusive_group()
    field_mode.add_argument('--semantic-field-loss', action='store_true', help='V4 joint value weighting; preserved for reproduction')
    field_mode.add_argument('--action-field-loss', action='store_true', help='Only action values receive weight 4; every other supervised token remains weight 1')
    field_mode.add_argument('--step-boundary-loss', action='store_true', help='V10 loss plus weight 3 on supervised step-list and step-object boundaries')
    field_mode.add_argument('--condition-field-loss', action='store_true', help='V10 loss plus weight 3 on condition values, including null')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.sequence_group_weighting and not args.group_action_weighting:
        parser.error('--sequence-group-weighting requires --group-action-weighting')
    if args.train_hard_case_audit and not args.group_action_weighting:
        parser.error('--train-hard-case-audit requires --group-action-weighting')
    if not baseline_guard()['passed'] or PLAN['training_entrypoint'] != 'experiments.semantic_sft.train':
        raise ValueError('isolated training plan or baseline guard failed')
    config = json.loads(args.config.read_text(encoding='utf-8'))
    validate_config(config)
    evaluation_epochs = semantic_evaluation_epochs(args.semantic_evaluation_epochs, config['epochs'],
        semantic=args.semantic_validation, train_recall=args.train_recall_evaluation)
    folder = args.release_dir.resolve(strict=True)
    if not folder.is_relative_to((ROOT / 'artifacts/semantic_sft/releases').resolve()):
        raise ValueError('only a frozen release in this isolated workspace is allowed')
    records, version, audit = verify_release(folder, args.release_manifest_sha256, args.token_audit)
    reviewed_rows = load_jsonl(folder / 'reviewed_rows.jsonl')
    train_rows = [r for r in reviewed_rows if r['split'] == 'train']
    from .weighting import group_action_weights
    weight_report = group_action_weights(train_rows, sequence_balance=args.sequence_group_weighting) if args.group_action_weighting else None
    if args.train_hard_case_audit:
        from .weighting import load_train_replay_audit, train_replay_weights
        cases, provenance = load_train_replay_audit(args.train_hard_case_audit,
            expected_dataset_manifest_sha256=args.release_manifest_sha256)
        weight_report = train_replay_weights(train_rows, weight_report, cases)
        weight_report['train_replay_audit_provenance'] = provenance
    weights = [item['weight'] for item in weight_report['samples']] if weight_report else [1.0] * len(train_rows)
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
    report = dict(scope='FROZEN_TEXT_LORA_DEVELOPMENT_SEMANTICS_NOT_FINAL_GATE' if args.semantic_validation else 'FROZEN_TEXT_LORA_CANDIDATE_NOT_SEMANTIC_ACCURACY_OR_GATE', status='LOADING',
        started_at_unix=time.time(), source_provenance=source, dataset_version=version,
        release_manifest_sha256=args.release_manifest_sha256, token_audit_sha256=sha(args.token_audit),
        training_config=config, base_model=PLAN['base_model'], base_revision=PLAN['base_revision'],
        base_fingerprint_verified=True, base_artifact_sha256=fingerprint['artifact_sha256'],
        physical_gpu=args.gpu_index, gpu_uuid=gpu_uuid, train_rows=len(records['train']), val_rows=len(records['val']),
        test_rows_read=0, adapter_only=True, production_health_before=health, epochs=[], optimizer_steps=0, training_started=False,
        formal_performance_gate_passed=False, semantic_accuracy_evaluated=False)
    report['group_action_weighting_enabled'] = args.group_action_weighting
    if args.train_hard_case_audit:
        report['train_replay_weighting_enabled'] = True
    if args.sequence_group_weighting:
        report['sequence_group_weighting_enabled'] = True
    report['gradient_checkpointing_enabled'] = args.gradient_checkpointing
    if args.semantic_evaluation_epochs is not None or args.train_recall_evaluation:
        report['evaluation_schedule'] = dict(epochs=sorted(evaluation_epochs), train_recall=args.train_recall_evaluation,
                                             train_recall_used_for_selection=False)
    use_field_loss = args.semantic_field_loss or args.action_field_loss or args.step_boundary_loss or args.condition_field_loss
    report['semantic_field_loss_enabled'] = use_field_loss
    report['system_prompt_sha256'] = hashlib.sha256(records['train'][0]['messages'][0]['content'].encode()).hexdigest()
    report['selection_policy'] = dict(mode='GENERATED_DEV_SEMANTICS' if args.semantic_validation else 'LEGACY_VAL_LOSS',
        evaluation_role='DEVELOPMENT_NOT_FINAL_TEST', generation_enabled=args.semantic_validation, max_new_tokens=1536, do_sample=False,
        order=['semantic_exact','raw_action_order_exact','extraction_valid','negative_val_loss'] if args.semantic_validation else ['negative_val_loss'],
        baseline_guard='No previously correct raw-action or complete-semantic Dev case may regress' if args.semantic_validation else 'NOT_APPLIED_LEGACY_REPRODUCTION',
        scorer_sha256=sha(HERE / 'semantic_metrics.py'))
    def save():
        temporary = output / 'report.tmp'
        temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
        temporary.replace(output / 'report.json')
    save()
    if weight_report:
        (output / 'train_weights.json').write_text(json.dumps(weight_report, indent=2), encoding='utf-8')
        report['train_weights_sha256'] = sha(output / 'train_weights.json')
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
        from .field_loss import POLICY, ACTION_ONLY_POLICY, STEP_BOUNDARY_POLICY, CONDITION_POLICY, assistant_weighted_ce, semantic_token_weights
        field_policy = (STEP_BOUNDARY_POLICY if args.step_boundary_loss else CONDITION_POLICY if args.condition_field_loss
                        else ACTION_ONLY_POLICY if args.action_field_loss else POLICY)
        field_weights = None
        if use_field_loss:
            field_weights = [semantic_token_weights(tokenizer, r['messages'], t, policy=field_policy)
                             for r, t in zip(records['train'], tokens['train'])]
            field_audit = dict(policy=field_policy, statistics_split='train', samples=[dict(sample_id=r['sample_id'],
                supervised_tokens=t['assistant_tokens'], weighted_tokens=sum(w > 1 for w in weights),
                token_weights_sha256=canonical_hash(weights),
                prompt_tokens_zero_weight=all(w == 0 for w in weights[:t['prompt_tokens']]))
                for r, t, weights in zip(records['train'], tokens['train'], field_weights)])
            if not all(s['weighted_tokens'] > 0 and s['prompt_tokens_zero_weight'] for s in field_audit['samples']):
                raise ValueError('semantic field masks failed')
            (output / 'field_loss_audit.json').write_text(json.dumps(field_audit, indent=2), encoding='utf-8')
            report['semantic_field_loss_policy'] = field_policy
            report['field_loss_audit_sha256'] = sha(output / 'field_loss_audit.json')
        def load_base():
            return AutoModelForImageTextToText.from_pretrained(str(model_path), local_files_only=True,
                trust_remote_code=False, dtype=torch.bfloat16, device_map={'': 'cuda:0'}, attn_implementation='eager')
        lora = PLAN['candidate_lora']
        model = get_peft_model(load_base(), LoraConfig(r=lora['r'], lora_alpha=lora['alpha'],
            lora_dropout=lora['dropout'], bias='none', target_modules=lora['target_modules_regex'], task_type='CAUSAL_LM'))
        model.config.use_cache = False
        if args.gradient_checkpointing:
            model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
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
        def generated_validation(tag, *, base=False, split='val'):
            model.eval()
            families = {r['sample_id']: r['semantic_family'] for r in load_jsonl(folder / 'reviewed_rows.jsonl')}
            eos = model.generation_config.eos_token_id
            eos_ids = [eos] if isinstance(eos, int) else eos
            scored = []
            cohort_name = 'dev' if split == 'val' else 'train'
            with (output / f'{cohort_name}_{tag}_generations.jsonl').open('x', encoding='utf-8') as stream:
                for record, token_record in zip(records[split], tokens[split]):
                    # The audited prompt prefix excludes every assistant/gold token.
                    prefix = token_record['input_ids'][:token_record['prompt_tokens']]
                    if len(prefix) + 1536 > PLAN['max_sequence_length_candidate']:
                        raise ValueError('generation prompt exceeds fixed context budget')
                    inputs = {'input_ids': torch.tensor([prefix], device='cuda:0')}
                    inputs['attention_mask'] = torch.ones_like(inputs['input_ids'])
                    with torch.inference_mode(), (model.disable_adapter() if base else nullcontext()):
                        generated = model.generate(**inputs, do_sample=False, num_beams=1, max_new_tokens=1536,
                            use_cache=True, eos_token_id=eos_ids,
                            pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else eos_ids[0])
                    new = generated[0, len(prefix):].tolist()
                    raw = tokenizer.decode(new, skip_special_tokens=True)
                    source = record['messages'][1]['content']
                    expected = json.loads(record['messages'][-1]['content'])
                    item = dict(sample_id=record['sample_id'], semantic_family=families[record['sample_id']],
                        raw=raw, generated_tokens=len(new), prompt_ids_sha256=canonical_hash(prefix),
                        score=score_text(source, raw, expected, complete=bool(new) and new[-1] in eos_ids))
                    scored.append(item)
                    stream.write(json.dumps(item, ensure_ascii=False) + '\n'); stream.flush()
                    report['development_generation_progress'] = dict(tag=tag, done=len(scored), total=len(records[split]))
                    if args.train_recall_evaluation:
                        report['development_generation_progress']['cohort'] = cohort_name
                    save()
                    print(json.dumps(dict(stage='DEV_GENERATION', **report['development_generation_progress'])), flush=True)
            return scored, summarize(scored)
        report['initial_val_token_cross_entropy'] = validation()
        baseline_generations = None
        if args.semantic_validation:
            report['status'] = 'VALIDATING_BASE_SEMANTICS'
            save()
            baseline_generations, baseline_summary = generated_validation('base', base=True)
            report['base_development_semantics'] = baseline_summary
        report['status'] = 'TRAINING'
        report['planned_optimizer_steps'] = updates
        save()
        best_key, diagnostic_key = None, None
        selected_reference, diagnostic_reference = None, None
        with (output / 'metrics.jsonl').open('x', encoding='utf-8') as metrics:
            for epoch in range(config['epochs']):
                model.train()
                epoch_losses = []
                for indices in epoch_batches(len(tokens['train']), config['gradient_accumulation'], config['seed'], epoch):
                    optimizer.zero_grad(set_to_none=True)
                    losses, weighted_losses = [], []
                    for index in indices:
                        record = tokens['train'][index]
                        if field_weights is None:
                            loss = model(**batch(record), use_cache=False).loss
                        else:
                            size = record['assistant_tokens']
                            # Only assistant-predicting logits are materialized, not the much longer prompt vocabulary tensor.
                            logits = model(**batch(record, labels=False), use_cache=False, logits_to_keep=size + 1).logits
                            loss = assistant_weighted_ce(logits, record['labels'][-size:], field_weights[index][-size:])
                        if not torch.isfinite(loss):
                            raise ValueError('non-finite training loss')
                        (loss * weights[index] / len(indices)).backward()
                        losses.append(loss.item())
                        weighted_losses.append(loss.item() * weights[index])
                    norm = torch.nn.utils.clip_grad_norm_(trainable.values(), config['max_grad_norm'], error_if_nonfinite=True)
                    used_lr = optimizer.param_groups[0]['lr']
                    optimizer.step()
                    scheduler.step()
                    report['optimizer_steps'] += 1
                    report['training_started'] = True
                    epoch_losses.extend(losses)
                    entry = dict(epoch=epoch + 1, step=report['optimizer_steps'], loss=sum(losses) / len(losses),
                                 weighted_loss=sum(weighted_losses) / len(weighted_losses),
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
                if args.semantic_validation and epoch + 1 in evaluation_epochs:
                    report['status'] = 'VALIDATING_EPOCH_SEMANTICS'
                    save()
                    scored, semantic_summary = generated_validation(f'epoch_{epoch + 1}')
                    regressions = baseline_regressions(scored, baseline_generations)
                    key = selection_rank(semantic_summary, val_loss)
                    eligible = not any(regressions.values())
                    summary.update(development_semantics=semantic_summary, baseline_regressions=regressions,
                                   eligible_after_baseline_guard=eligible, selection_rank=list(key))
                    report['semantic_accuracy_evaluated'] = True
                    if args.train_recall_evaluation:
                        report['status'] = 'VALIDATING_SEEN_TRAIN_SEMANTICS'
                        save()
                        _, train_summary = generated_validation(f'epoch_{epoch + 1}', split='train')
                        summary['seen_train_semantics'] = train_summary
                elif args.semantic_validation:
                    key, eligible = None, False
                    summary['semantic_evaluation_skipped'] = True
                else:
                    key, eligible = (-val_loss,), True
                report['epochs'].append(summary)
                diagnostic_improved = key is not None and (diagnostic_key is None or key > diagnostic_key)
                selected_improved = eligible and (best_key is None or key > best_key)
                if diagnostic_improved or selected_improved:
                    with torch.no_grad():
                        reference = model(**batch(tokens['val'][0], labels=False), use_cache=False, logits_to_keep=1).logits.float().cpu()
                if diagnostic_improved:
                    diagnostic_key = key
                    diagnostic_reference = reference
                    report['diagnostic_adapter'] = adapter.name
                if selected_improved:
                    best_key = key
                    selected_reference = reference
                    report['best_adapter'] = adapter.name
                    report['best_val_token_cross_entropy'] = val_loss
                report['status'] = 'TRAINING'
                save()
        report['changed_adapter_tensors'] = sum(not torch.equal(before[name], p.detach().float().cpu()) for name, p in trainable.items())
        if not report['changed_adapter_tensors']:
            raise ValueError('no adapter parameters changed')
        report['peak_cuda_bytes'] = torch.cuda.max_memory_allocated()
        loss = None
        if use_field_loss:
            del logits
        del model, optimizer, scheduler, trainable, before
        gc.collect(); torch.cuda.empty_cache()
        report['status'] = 'VERIFYING_RELOAD'
        save()
        report['candidate_selection_status'] = 'SELECTED_ON_DEV_NOT_FINAL_GATE' if 'best_adapter' in report else 'NO_ADMISSIBLE_CANDIDATE_KEEP_BASELINE'
        verified_name = report.get('best_adapter', report['diagnostic_adapter'])
        report['reload_verified_adapter'] = verified_name
        report['adapter_artifact_role'] = 'SELECTED_DEVELOPMENT_CANDIDATE' if 'best_adapter' in report else 'REJECTED_DIAGNOSTIC_ONLY_NOT_PROMOTABLE'
        reference = selected_reference if selected_reference is not None else diagnostic_reference
        selected = output / verified_name
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
