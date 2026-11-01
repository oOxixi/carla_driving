"""Freeze approved grouped Train/Val and export chat records; never approve or train."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path

from .data import PLAN, audit_rows, baseline_guard, chat_record, load_jsonl, output_directory
from .prepare import external_registry, registry_groups


def assign_approved_groups(previous, batch, planned_groups, *, external_protected,
                           supplemental_protected, protected_groups):
    options = dict(external_protected=external_protected, supplemental_protected=supplemental_protected,
                   protected_groups=protected_groups)
    old = audit_rows(previous, minimum_train=0, minimum_val=0, **options)
    if not old['data_ready_for_tokenization']:
        raise ValueError('previous split must already be approved, protected and fully assigned')
    if not batch or not isinstance(planned_groups, dict) or set(planned_groups) != {r['group_id'] for r in batch}:
        raise ValueError('every new group must have exactly one declared split; no unused groups')
    if any(value not in {'train', 'val'} for value in planned_groups.values()):
        raise ValueError('planned splits must be train or val')
    if any(row['split'] != 'UNASSIGNED' for row in batch):
        raise ValueError('never overwrite an existing batch split')
    old_groups = {row['group_id']: (row['split'], row['semantic_family']) for row in previous}
    combined = copy.deepcopy(previous + batch)
    for row in combined[len(previous):]:
        row['split'] = planned_groups[row['group_id']]
        if row['group_id'] in old_groups and old_groups[row['group_id']] != (row['split'], row['semantic_family']):
            raise ValueError('existing paraphrase group cannot change split or family')
    report = audit_rows(combined, **options)
    if not report['data_ready_for_tokenization']:
        raise ValueError('release rejected: ' + json.dumps(dict(issues=report['issues'], global_errors=report['global_errors'])))
    return combined, report


def write_rows(path, rows):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('previous', 'approved-batch', 'planned-groups', 'quarantine', 'approval-receipt',
                 'test-registry', 'supplemental-registry', 'output-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--dataset-version', required=True)
    args = parser.parse_args()
    if not args.dataset_version.strip():
        raise ValueError('dataset version is required')
    guard = baseline_guard()
    if not guard['passed']:
        raise ValueError('baseline guard failed')
    output = output_directory(args.output_dir)
    previous, batch = load_jsonl(args.previous), load_jsonl(args.approved_batch)
    planned = json.loads(args.planned_groups.read_text(encoding='utf-8'))
    combined, report = assign_approved_groups(previous, batch, planned,
        external_protected=external_registry(args.test_registry),
        supplemental_protected=external_registry(args.supplemental_registry, role='INDEPENDENT_VALIDATION'),
        protected_groups=registry_groups(args.test_registry) | registry_groups(args.supplemental_registry))
    quarantine = load_jsonl(args.quarantine)
    if any(not r.get('proposal', {}).get('contract_gap') or r.get('label') is not None or r.get('reviews') for r in quarantine):
        raise ValueError('quarantine must retain unresolved, unapproved contract gaps')
    if {r['sample_id'] for r in quarantine} & {r['sample_id'] for r in combined}:
        raise ValueError('quarantine cannot enter Train/Val')
    receipt = json.loads(args.approval_receipt.read_text(encoding='utf-8'))
    expected = [{'sample_id': r['sample_id'], 'source_sha256': r['source_sha256'],
                 'label_sha256': r['reviews'][-1]['label_sha256']} for r in batch]
    if (receipt.get('scope') != 'HUMAN_REVIEW_RECORD_NOT_TRAINING_GATE'
            or receipt.get('accepted_rows') != expected or not receipt.get('approval_quote')):
        raise ValueError('approval receipt must bind this exact batch, not an unrelated review')
    output.mkdir(parents=True, exist_ok=False)
    write_rows(output / 'reviewed_rows.jsonl', combined)
    for split in ('train', 'val'):
        write_rows(output / (split + '.jsonl'), [chat_record(r) for r in combined if r['split'] == split])
    for name, source in [('quarantine.jsonl', args.quarantine), ('approval_receipt.json', args.approval_receipt),
                         ('test_exclusion_registry.json', args.test_registry),
                         ('supplemental_exclusion_registry.json', args.supplemental_registry)]:
        with (output / name).open('xb') as stream:
            stream.write(source.read_bytes())
    report.update(scope='FROZEN_INTERNAL_SEMANTIC_TRAIN_VAL_NOT_PERFORMANCE_GATE', split_frozen=True,
                  dataset_version=args.dataset_version, reviewed_rows=len(combined), quarantined_rows=len(quarantine),
                  semantic_independence_source='OWNER_CONFIRMED_NOT_PROVEN_BY_TOOL', training_started=False)
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8', newline='\n')
    inputs = [args.previous, args.approved_batch, args.planned_groups, args.quarantine, args.approval_receipt,
              args.test_registry, args.supplemental_registry]
    manifest = dict(scope=report['scope'], dataset_version=args.dataset_version,
        recorded_at=datetime.now().astimezone().isoformat(), split_frozen=True, baseline_guard=guard,
        base_model=PLAN['base_model'], base_revision=PLAN['base_revision'],
        source_lf_utf8_sha256=hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
        input_sha256={p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        artifact_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
        training_started=False, ready_for_training=False, formal_performance_gate_passed=False)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps(dict(dataset_version=args.dataset_version, splits=report['splits'],
                         split_frozen=True, data_ready_for_tokenization=True, ready_for_training=False)))


if __name__ == '__main__':
    main()
