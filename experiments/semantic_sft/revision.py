"""Propose condition-only corrections; freeze only after actual owner authorization."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path

from qwen_service.task_understanding import SYSTEM_PROMPT, validate_extraction
from .data import PLAN, audit_rows, baseline_guard, canonical_hash, chat_record, load_jsonl, output_directory
from .prepare import external_registry, registry_groups
from .release import write_rows
from .train import sha, verify_release


# Protocol/rubric only: no Dev examples, expected answers, regex action classifier, or grammar repair.
SYSTEM_V3 = SYSTEM_PROMPT + """
JSON顶层恰好为steps、prohibited_actions、requires_confirmation。
steps为1至8步数组，每步恰好包含action、target_text、direction、speed_kph、gap_m、condition、evidence。
action必须使用上述大写英文动作码；direction只能是LEFT、RIGHT、STRAIGHT或null，不可使用中文或动作码。
speed_kph、gap_m为数字或null，不可带单位字符串。requires_confirmation是布尔值。
prohibited_actions是对象：没有禁止事项时{}；否则只以被禁止动作码为键、true为值，不是数组或字符串。
condition也包括明确指定的将来到达地点，例如要求在某路口执行而非立即执行。
同一动作有状态和地点两个前提时，引用包含两者的连续原文片段。仅表达动作本身的“靠边”等不是额外地点条件。
并列任务共用明确前提；新的“然后/最后”任务不自动继承已结束从句的条件。背景中的其他车辆行为不是本车指令。
只返回JSON，不要Markdown代码围栏、解释或额外字段。
"""


def condition_proposals(rows):
    """Source/label-only audit; deliberately independent of all model predictions."""
    proposals = []
    for row in rows:
        label = copy.deepcopy(row['label'])
        for step in label['steps']:
            if step['action'] in {'TURN_LEFT', 'TURN_RIGHT'} and step['condition'] is None and step['evidence'].startswith('在前方路口'):
                step['condition'] = '在前方路口'
            for old, new in (
                ('清洁员通过人行道以后', '清洁员通过人行道以后，在前方路口'),
                ('等白色客车驶入停车区后', '等白色客车驶入停车区后，在路口'),
            ):
                if step['condition'] == old and new in row['source_text']:
                    step['condition'] = new
        if label != row['label']:
            validate_extraction(row['source_text'], label)
            proposals.append(dict(sample_id=row['sample_id'], source_sha256=row['source_sha256'],
                source_text=row['source_text'], split=row['split'], group_id=row['group_id'],
                previous_label_sha256=canonical_hash(row['label']), label=label))
    return proposals


def apply_condition_revision(rows, proposals, approval):
    """Caller must retain real authorization. This function cannot verify a human signature."""
    if (approval.get('reviewer_id') != PLAN['review_owner_id']
            or any(not isinstance(approval.get(k), str) or not approval[k].strip()
                   for k in ('approval_reference', 'approval_quote', 'reviewed_at'))):
        raise ValueError('explicit owner authorization is required for changed labels')
    timestamp = datetime.fromisoformat(approval['reviewed_at'].replace('Z', '+00:00'))
    if timestamp.utcoffset() is None:
        raise ValueError('actual review recording time needs a timezone')
    if (not proposals or approval.get('proposal_sha256') != canonical_hash(proposals)
            or len({p['sample_id'] for p in proposals}) != len(proposals)):
        raise ValueError('approval must bind exactly these unique proposed labels')
    by_id = {p['sample_id']: p for p in proposals}
    if len({r['sample_id'] for r in rows}) != len(rows) or set(by_id) - {r['sample_id'] for r in rows}:
        raise ValueError('missing/duplicate parent row')
    updated = copy.deepcopy(rows)
    accepted = []
    for row in updated:
        if row['sample_id'] not in by_id:
            continue
        proposal = by_id[row['sample_id']]
        if (row['annotation_status'] != 'APPROVED' or proposal['previous_label_sha256'] != canonical_hash(row['label'])
                or any(proposal[k] != row[k] for k in ('source_text', 'source_sha256', 'split', 'group_id'))):
            raise ValueError('stale correction or changed source/split/group')
        candidate = proposal['label']
        stripped = copy.deepcopy(candidate)
        if len(candidate['steps']) != len(row['label']['steps']):
            raise ValueError('only condition changes are authorized')
        for old, new in zip(row['label']['steps'], stripped['steps']):
            new['condition'] = old['condition']
        if stripped != row['label'] or candidate == row['label']:
            raise ValueError('only nonempty condition changes are authorized')
        validate_extraction(row['source_text'], candidate)
        row['label'] = copy.deepcopy(candidate)
        row['reviews'].append(dict(reviewer_id=approval['reviewer_id'], approved=True,
            source_sha256=row['source_sha256'], label_sha256=canonical_hash(candidate), reviewed_at=approval['reviewed_at']))
        accepted.append(dict(sample_id=row['sample_id'], source_sha256=row['source_sha256'],
                             label_sha256=canonical_hash(candidate)))
    return updated, dict(scope='HUMAN_REVIEW_RECORD_NOT_TRAINING_GATE', **approval, accepted_rows=accepted,
        identity_note='Caller-provided identity is not a verified signature; retain actual owner approval.',
        prior_reviews_preserved=True, new_training_texts=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('draft', 'freeze'))
    parser.add_argument('--parent-dir', type=Path, required=True)
    parser.add_argument('--parent-manifest-sha256', required=True)
    parser.add_argument('--parent-token-audit', type=Path, required=True)
    parser.add_argument('--proposal-file', type=Path)
    parser.add_argument('--approval-file', type=Path)
    parser.add_argument('--dataset-version')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if not baseline_guard()['passed']:
        raise ValueError('isolated experiment guard failed')
    parent = args.parent_dir.resolve(strict=True)
    verify_release(parent, args.parent_manifest_sha256, args.parent_token_audit)
    rows = load_jsonl(parent / 'reviewed_rows.jsonl')
    output = output_directory(args.output_dir)
    if args.mode == 'draft':
        proposals = condition_proposals(rows)
        output.mkdir(parents=True, exist_ok=False)
        (output / 'proposals.json').write_text(json.dumps(proposals, ensure_ascii=False, indent=2), encoding='utf-8')
        before = {r['sample_id']: r['label'] for r in rows}
        lines = ['# V3条件口径修订候选（未批准）', '', '仅修condition，旧版及所有split/group保留；动作、顺序和参数不改。', '']
        for p in proposals:
            lines.extend([f"## {p['sample_id']} ({p['split']})", '', p['source_text'], ''])
            for i, (old, new) in enumerate(zip(before[p['sample_id']]['steps'], p['label']['steps'])):
                if old['condition'] != new['condition']:
                    lines.append(f"- 步骤{i+1} {new['action']}：{old['condition']!r} → {new['condition']!r}")
            lines.append('')
        (output / 'REVIEW.md').write_text('\n'.join(lines), encoding='utf-8')
        print(json.dumps(dict(proposals=len(proposals), proposal_sha256=canonical_hash(proposals), approved=False)))
        return
    if not args.proposal_file or not args.approval_file or not args.dataset_version or not args.dataset_version.strip():
        parser.error('freeze requires proposal, actual owner approval, and a new dataset version')
    proposals = json.loads(args.proposal_file.read_text(encoding='utf-8'))
    approval = json.loads(args.approval_file.read_text(encoding='utf-8'))
    updated, receipt = apply_condition_revision(rows, proposals, approval)
    report = audit_rows(updated, external_protected=external_registry(parent / 'test_exclusion_registry.json'),
        supplemental_protected=external_registry(parent / 'supplemental_exclusion_registry.json', role='INDEPENDENT_VALIDATION'),
        protected_groups=registry_groups(parent / 'test_exclusion_registry.json') | registry_groups(parent / 'supplemental_exclusion_registry.json'))
    if not report['data_ready_for_tokenization']:
        raise ValueError('revision failed full data audit')
    output.mkdir(parents=True, exist_ok=False)
    write_rows(output / 'reviewed_rows.jsonl', updated)
    for split in ('train', 'val'):
        write_rows(output / (split + '.jsonl'), [chat_record(r, system_prompt=SYSTEM_V3) for r in updated if r['split'] == split])
    for name in ('quarantine.jsonl', 'test_exclusion_registry.json', 'supplemental_exclusion_registry.json'):
        (output / name).write_bytes((parent / name).read_bytes())
    (output / 'parent_approval_receipt.json').write_bytes((parent / 'approval_receipt.json').read_bytes())
    (output / 'approval_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'condition_proposals.json').write_bytes(args.proposal_file.read_bytes())
    (output / 'system_prompt.txt').write_text(SYSTEM_V3, encoding='utf-8')
    report.update(dataset_version=args.dataset_version, changed_labels=len(proposals), split_frozen=True,
                  scope='REVISED_DEVELOPMENT_LABELS_NOT_COMPARABLE_TO_OLD_STRICT_SCORE_OR_FINAL_GATE')
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    manifest = dict(dataset_version=args.dataset_version, split_frozen=True, base_model=PLAN['base_model'],
        base_revision=PLAN['base_revision'], parent_manifest_sha256=args.parent_manifest_sha256,
        parent_reviewed_rows_sha256=sha(parent / 'reviewed_rows.jsonl'), changed_labels=len(proposals),
        system_prompt=SYSTEM_V3, system_prompt_sha256=hashlib.sha256(SYSTEM_V3.encode()).hexdigest(),
        recorded_at=datetime.now().astimezone().isoformat(), formal_performance_gate_passed=False,
        artifact_sha256={p.name: sha(p) for p in sorted(output.iterdir())})
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(dict(dataset_version=args.dataset_version, changed_labels=len(proposals), splits=report['splits'],
                         manifest_sha256=sha(output / 'manifest.json'))))


if __name__ == '__main__':
    main()
