"""Inventory existing data and recover Train-only text candidates without inventing semantic labels."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import subprocess

from .data import ROOT, HERE, load_jsonl, output_directory, protected_hashes, review_packet, text_hash, source_hash
from .prepare import external_registry
from .release import write_rows
from .train import sha


RETIRED = {'d2_v1'}
TRAIN_FILES = {'train.jsonl', 'train_addition.jsonl'}
EVAL_FILES = {'val.jsonl', 'val_addition.jsonl', 'reserved_test_candidates.jsonl', 'calibration.jsonl'}


def source_text(row):
    for value in (row.get('model_request', {}).get('source_text'), row.get('source_text'),
                  row.get('transcript'), row.get('voice_command'), row.get('text'), row.get('template')):
        if isinstance(value, str) and value.strip():
            return value
    return None


def source_group(row):
    return row.get('metadata', {}).get('group_key') or row.get('group_id') or row.get('evaluation_group_id')


def eligible_teacher(row):
    q = row.get('quality', {})
    return q.get('valid_for_training') is True and not q.get('training_exclusion_reasons') and (
        q.get('training_role') == 'POSITIVE')


def partition_train(entries, protected, protected_groups, existing):
    kept, excluded = defaultdict(list), []
    for row, reference in entries:
        text = source_text(row)
        reasons = []
        if text is None or len(text) > 1000:
            reasons.append('NO_SUPPORTED_SOURCE_TEXT')
        digest = text_hash(text) if text is not None else None
        if digest in protected:
            reasons.append('EVALUATION_OR_PROMPT_TEXT')
        if source_group(row) in protected_groups:
            reasons.append('EVALUATION_SOURCE_GROUP')
        if digest in existing:
            reasons.append('ALREADY_IN_APPROVED_SEMANTIC_TRAIN')
        if not eligible_teacher(row):
            reasons.append('TEACHER_QUALITY_OR_ROLE_NOT_TRAINABLE')
        if reasons:
            excluded.append(dict(reference=reference, normalized_text_sha256=digest, reasons=reasons))
        else:
            kept[digest].append((row, reference))
    return dict(kept), excluded


def packet_for(text, digest):
    packet = review_packet(dict(sample_id='RECOVERED_TRAIN_' + digest[:20], source_text=text,
        semantic_family='UNCLASSIFIED_NEEDS_REVIEW', group_id='recovered_exact_' + digest[:20]))
    packet['origin']['kind'] = 'EXTRACTED_EXISTING_TRAIN_REQUIRES_REVIEW'
    return packet


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--challenge-root', type=Path, required=True)
    parser.add_argument('--release-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = output_directory(args.output_dir)
    protected = set(protected_hashes())
    protected_by = defaultdict(set)
    for digest in protected:
        protected_by[digest].add('BUILTIN_EVALUATION_OR_PROMPT')
    protected_groups = set()
    inventory, entries, unavailable, held = [], [], [], Counter()
    all_reviewed = load_jsonl(args.release_dir / 'reviewed_rows.jsonl')
    old_train = [r for r in all_reviewed if r['split'] == 'train']
    existing = {text_hash(r['source_text']) for r in old_train}
    for r in all_reviewed:
        if r['split'] == 'val':
            protected.add(text_hash(r['source_text']))
            protected_by[text_hash(r['source_text'])].add(str(args.release_dir / 'reviewed_rows.jsonl') + '#val')
            protected_groups.add(r['group_id'])
    for r in load_jsonl(args.release_dir / 'quarantine.jsonl'):
        protected.add(text_hash(r['source_text']))
        protected_by[text_hash(r['source_text'])].add(str(args.release_dir / 'quarantine.jsonl'))
        protected_groups.add(r['group_id'])
    for name, role in [('test_exclusion_registry.json', 'FROZEN_TEST'),
                       ('supplemental_exclusion_registry.json', 'INDEPENDENT_VALIDATION')]:
        hashes = external_registry(args.release_dir / name, role=role)
        protected |= hashes
        for digest in hashes:
            protected_by[digest].add(str(args.release_dir / name))

    def read(path, role):
        if not path.is_file():
            unavailable.append(str(path))
            return []
        if path.suffix == '.jsonl':
            rows = load_jsonl(path) if path.stat().st_size else []
        else:
            obj = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(obj, list):
                raise ValueError('unsupported record container: ' + str(path))
            rows = obj
        file_hash = sha(path)
        refs = [dict(path=str(path.resolve()), file_sha256=file_hash, row_number=i+1,
                     sample_id=r.get('sample_id', r.get('case_id', r.get('id'))),
                     original_text_sha256=source_hash(source_text(r)) if source_text(r) else None)
                for i, r in enumerate(rows)]
        texts = {text_hash(t) for r in rows if (t := source_text(r))}
        inventory.append(dict(path=str(path.resolve()), sha256=file_hash, role=role,
                              records=len(rows), unique_texts=len(texts),
                              rows_without_supported_text=sum(source_text(r) is None for r in rows)))
        if role in {'EVALUATION_ONLY', 'QUARANTINE_ONLY'}:
            protected.update(texts)
            for digest in texts:
                protected_by[digest].add(str(path.resolve()))
            protected_groups.update(source_group(r) for r in rows if source_group(r))
            held[role] += len(rows)
        return list(zip(rows, refs))

    # These repository resources are explicitly regression/evaluation material, not new Train.
    for rel in ('voice_group/test_samples/manifest.json',
                'CARLA-Language-Benchmark/datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json',
                'datasets/language_v1/commands.jsonl', 'datasets/qwen_proxy_v1/cases.jsonl',
                'config/qwen_task_understanding_dev.jsonl', 'config/qwen_task_understanding_probe.jsonl'):
        read(ROOT / rel, 'EVALUATION_ONLY')
    releases = args.challenge_root / 'challenge/dataset/releases'
    if not releases.is_dir():
        raise ValueError('challenge release directory missing')
    for directory in sorted(p for p in releases.iterdir() if p.is_dir()):
        for path in sorted(directory.glob('*.jsonl')):
            if path.name in EVAL_FILES:
                read(path, 'EVALUATION_ONLY')
            elif path.name == 'hard_negative_addition.jsonl':
                read(path, 'QUARANTINE_ONLY')
            elif path.name in TRAIN_FILES:
                pairs = read(path, 'RETIRED_NOT_IMPORTED' if directory.name in RETIRED else 'DECLARED_TEACHER_TRAIN_PENDING_GOVERNANCE')
                if directory.name not in RETIRED:
                    entries.extend(pairs)
            else:
                inventory.append(dict(path=str(path.resolve()), sha256=sha(path), role='METADATA_NOT_IMPORTED'))
        for path in sorted(directory.glob('quarantine/*.jsonl')):
            read(path, 'QUARANTINE_ONLY')
    smoke = args.challenge_root / 'challenge/dataset/smoke_v0'
    for path, role in ((smoke / 'data/val.jsonl', 'EVALUATION_ONLY'),
                       (smoke / 'data/train.jsonl', 'DECLARED_SMOKE_TRAIN_PENDING_GOVERNANCE'),
                       (smoke / 'training_view/val_a3.jsonl', 'EVALUATION_ONLY')):
        pairs = read(path, role)
        if role == 'DECLARED_SMOKE_TRAIN_PENDING_GOVERNANCE':
            entries.extend(pairs)
    for path in sorted((args.challenge_root / 'challenge/distillation/releases').glob('*/training.jsonl')):
        inventory.append(dict(path=str(path.resolve()), sha256=sha(path),
                              role='OPTIMIZER_LOG_NOT_TRAINING_EXAMPLES'))
    # Availability, not inferred content: archived/private corpora are not silently counted.
    for rel in ('data_short.zip', 'data/group1_voice/data_short/train.json', 'data/group1_voice/data_short/test.json'):
        p = ROOT / rel
        if not p.exists():
            unavailable.append(str(p))
        else:
            inventory.append(dict(path=str(p.resolve()), role='UNVERIFIED_ARCHIVE_OR_OFFICIAL_VOICE_NOT_IMPORTED', sha256=sha(p)))
    kept, excluded = partition_train(entries, protected, protected_groups, existing)
    for item in excluded:
        item['evaluation_or_quarantine_matches'] = sorted(protected_by[item['normalized_text_sha256']])
    excluded_by_reference = {(r['reference']['path'], r['reference']['row_number']): r for r in excluded}
    blocked = defaultdict(list)
    for row, ref in entries:
        reason = excluded_by_reference.get((ref['path'], ref['row_number']))
        if reason and source_text(row):
            blocked[text_hash(source_text(row))].append((row, ref, reason))
    blocked_audit = [dict(normalized_text_sha256=digest, source_text=source_text(members[0][0]),
        status='BLOCKED_NOT_TRAINING_CANDIDATE', source_row_count=len(members),
        reasons=sorted({reason for _, _, issue in members for reason in issue['reasons']}),
        evaluation_or_quarantine_matches=sorted({p for _, _, issue in members for p in issue['evaluation_or_quarantine_matches']}),
        references=[ref for _, ref, _ in members]) for digest, members in sorted(blocked.items())]
    existing_conflicts = [dict(sample_id=r['sample_id'], source_text=r['source_text'],
        status='EXISTING_LABEL_PRESERVED_NEW_EXCLUSION_REVIEW_REQUIRED',
        evaluation_or_quarantine_matches=sorted(protected_by[text_hash(r['source_text'])]))
        for r in old_train if text_hash(r['source_text']) in protected or r['group_id'] in protected_groups]
    packets, labels_missing, provenance = [], [], []
    for digest, members in sorted(kept.items()):
        text = source_text(members[0][0])
        packet = packet_for(text, digest)
        packets.append(packet)
        behaviors = sorted({tuple(s.get('behavior') for s in row.get('teacher_plan', {}).get('steps', []))
                            for row, _ in members})
        provenance.append(dict(sample_id=packet['sample_id'], references=[ref for _, ref in members],
            normalized_text_sha256=digest, original_teacher_execution_sequences=behaviors,
            execution_sequences_are_not_semantic_labels=True, source_license_review_pending=True,
            scenario_groups=sorted({str(source_group(row)) for row, _ in members if source_group(row)})))
        labels_missing.append(dict(sample_id=packet['sample_id'], source_text=text,
            missing=['semantic_family', 'cross_batch_semantic_group_review', 'ordered_steps.action', 'ordered_steps.evidence',
                'ordered_steps.target_text', 'ordered_steps.direction', 'ordered_steps.speed_kph', 'ordered_steps.gap_m',
                'ordered_steps.condition', 'prohibited_actions', 'requires_confirmation', 'owner_label_review',
                'source_governance_and_training_permission_review'],
            not_safe_to_copy=['teacher_plan.target_id', 'teacher_plan.preconditions', 'safety_override_action',
                              'teacher_plan.target_speed_mps_without_unit_and_source_semantics_review']))
    # Candidate leakage checks are rerun after ALL evaluation sources have been indexed.
    assert not {text_hash(r['source_text']) for r in packets} & (protected | existing)
    out.mkdir(parents=True, exist_ok=False)
    for filename, rows in [('recovered_candidates.jsonl', packets), ('missing_labels.jsonl', labels_missing),
                           ('candidate_provenance.jsonl', provenance), ('excluded_source_rows.jsonl', excluded),
                           ('blocked_text_audit.jsonl', blocked_audit),
                           ('existing_approved_train.jsonl', old_train)]:
        write_rows(out / filename, rows)
    write_rows(out / 'existing_train_new_exclusion_conflicts.jsonl', existing_conflicts)
    reasons = Counter(reason for r in excluded for reason in r['reasons'])
    report = dict(scope='INVENTORY_AND_UNAPPROVED_RECOVERY_NOT_NEW_TRAIN_RELEASE', inventory=inventory,
        source_challenge_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.challenge_root, text=True).strip(),
        extraction_source_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        current_reviewed_rows_sha256=sha(args.release_dir / 'reviewed_rows.jsonl'),
        existing_approved_train=len(old_train), declared_teacher_train_rows=len(entries),
        existing_train_conflicts_with_expanded_exclusions=len(existing_conflicts),
        declared_teacher_train_unique_texts=len({text_hash(t) for r, _ in entries if (t := source_text(r))}),
        evaluation_text_hashes=len(protected), evaluation_groups=len(protected_groups),
        excluded_rows=len(excluded), exclusion_reason_counts=dict(reasons), recovered_unique_candidates=len(packets),
        blocked_unique_texts=len(blocked_audit),
        evaluation_overlap_by_source_file=dict(Counter(p for item in excluded for p in item['evaluation_or_quarantine_matches'])),
        ready_for_training=False, training_started=False, unavailable_or_not_in_scope=unavailable,
        limitations=['Exact text and source-group exclusion does not prove semantic independence.',
                     'No previously private archive, external dataset, or other branch was assumed downloaded.',
                     'Teacher decision outputs and command hints were not converted into semantic ground truth.'])
    (out / 'inventory_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 已有数据盘点与语义候选提取', '',
        f'保留已有已审Train快照：{len(old_train)}（不是重新签发训练发布）；新增排除冲突：{len(existing_conflicts)}。',
        f'Teacher Train原始行：{len(entries)}；严格排除后新候选：{len(packets)}。',
        '新增候选label=null，DRAFT/UNASSIGNED、无审批；不是可直接训练的发布。', '',
        '## 来源清单', '', '|来源|用途|行数|文本去重|', '|---|---|---:|---:|']
    for r in inventory:
        lines.append(f"|{Path(r['path']).parent.name}/{Path(r['path']).name}|{r['role']}|{r.get('records','—')}|{r.get('unique_texts','—')}|")
    lines += ['', '## 排除原因（可重叠）', ''] + [f'- {k}: {v}' for k, v in sorted(reasons.items())]
    lines += ['', '## 候选标签缺口', '',
        '每条都需要重新确定：完整有序动作、逐字证据、目标、方向、数值及单位、前提及其作用步骤、禁止项和澄清标志。',
        '执行中的安全停车不能当用户停车意图；Actor ID不能当原文目标；m/s不能直接当km/h。',
        '按原始来源追溯，复核Train/Val相同原句与近义模板，确认来源许可及比赛使用范围。',
        '缺失或未经核验的音频压缩包不会当成可用训练集；原回归集、Val和reserved_test继续排除。']
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    manifest = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
    (out / 'artifact_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('existing_approved_train','declared_teacher_train_rows',
        'declared_teacher_train_unique_texts','excluded_rows','exclusion_reason_counts','recovered_unique_candidates')}))


if __name__ == '__main__':
    main()
