"""Train-only error taxonomy, contrast coverage and group-fold plan; never relabel or train."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from .data import audit_rows, canonical_hash, load_jsonl, output_directory, protected_hashes
from .generalization_audit import train_group_folds
from .mine_train_hard_cases import mine
from .prepare import external_registry, registry_groups
from .release import write_rows
from .train import sha


ERROR_TYPES = {
    'format': {'INCOMPLETE_GENERATION', 'JSON_INVALID', 'SCHEMA_INVALID'},
    'action_sequence': {'ACTION_SEQUENCE_MISMATCH'},
    'condition_missing': {'CONDITION_MISSING'},
    'condition_extra': {'CONDITION_EXTRA'},
    'condition_span_or_scope_review': {'CONDITION_SPAN_MISMATCH'},
    'target_direction_binding': {'TARGET_TEXT_MISMATCH', 'DIRECTION_MISMATCH'},
    'numeric_argument': {'SPEED_KPH_MISMATCH', 'GAP_M_MISMATCH'},
    'confirmation': {'REQUIRES_CONFIRMATION_MISMATCH'},
    'prohibition': {'PROHIBITED_ACTIONS_MISMATCH'},
    'literal_or_contract': {'LITERAL_OR_CONTRACT_REJECTION'},
}


def coverage(rows):
    """Describe approved labels, not keyword-derived semantic truth or new sampling weights."""
    actions, layouts = defaultdict(list), defaultdict(lambda: defaultdict(list))
    for row in rows:
        steps = row['label']['steps']
        sequence = tuple(s['action'] for s in steps)
        layout = tuple(s['condition'] is not None for s in steps)
        layouts[(row['group_id'], sequence)][layout].append(row['sample_id'])
        for index, step in enumerate(steps):
            actions[step['action']].append((row, index, step['condition']))
    census = {}
    for action, items in sorted(actions.items()):
        present = [x for x in items if x[2] is not None]
        absent = [x for x in items if x[2] is None]
        present_groups = {r['group_id'] for r, _, _ in present}
        absent_groups = {r['group_id'] for r, _, _ in absent}
        census[action] = dict(steps=len(items), condition_present_steps=len(present),
            condition_null_steps=len(absent), condition_present_groups=len(present_groups),
            condition_null_groups=len(absent_groups), unique_literal_conditions=len({c for _, _, c in present}),
            groups_with_both=len(present_groups & absent_groups))
    contrasts = [dict(group_id=group, actions=list(sequence),
        condition_layouts=[dict(present=list(layout), sample_ids=ids) for layout, ids in sorted(variants.items())])
        for (group, sequence), variants in sorted(layouts.items()) if len(variants) > 1]
    return dict(rows=len(rows), groups=len({r['group_id'] for r in rows}),
        steps=sum(len(r['label']['steps']) for r in rows),
        step_count_histogram=dict(sorted(Counter(len(r['label']['steps']) for r in rows).items())),
        confirmation_rows=dict(Counter(str(r['label']['requires_confirmation']).lower() for r in rows)),
        rows_with_prohibitions=sum(bool(r['label']['prohibited_actions']) for r in rows),
        per_action=census, within_group_same_sequence_condition_contrasts=contrasts,
        caution='Counts do not prove semantic diversity, label correctness or causal minimal pairs.')


def audit_train(records, predictions, *, protected, held_ids, folds=4):
    cases, mined = mine(records, predictions, protected=protected, held_ids=held_ids)
    siblings = defaultdict(list)
    for row in records:
        siblings[row['group_id']].append(row)
    for case in cases:
        tags = set(case['diagnostic']['tags'])
        case['error_types'] = [key for key, values in ERROR_TYPES.items() if tags & values]
        if not case['error_types']:
            case['error_types'] = ['unclassified_review']
        case['non_null_condition_differences'] = [dict(d,
            literal_containment=d['expected'] in d['observed'] or d['observed'] in d['expected'],
            semantic_equivalence_judged=False)
            for d in case['diagnostic']['slot_differences'] if d['field'] == 'condition'
            and d['expected'] is not None and d['observed'] is not None]
        case['same_group_review_context'] = [dict(sample_id=r['sample_id'], source_text=r['source_text'],
            approved_label=r['label']) for r in siblings[case['group_id']] if r['sample_id'] != case['sample_id']]
        case['annotation_decision'] = 'UNCHANGED_APPROVED_LABEL_REVIEW_ONLY'
    plan = train_group_folds(records, folds=folds)
    by_id = {r['sample_id']: r for r in records}
    fold_coverage = [dict(fold=f['fold'], fit=coverage([by_id[i] for i in f['fit_ids']]),
        development=coverage([by_id[i] for i in f['development_ids']])) for f in plan['folds']]
    full_coverage = coverage(records)
    missing_fit_support = [dict(fold=f['fold'], action=action, condition=side,
        all_train_groups=stats[f'condition_{side}_groups'])
        for f in fold_coverage for action, stats in full_coverage['per_action'].items()
        for side in ('present', 'null') if stats[f'condition_{side}_groups'] > 0
        and f['fit']['per_action'].get(action, {}).get(f'condition_{side}_groups', 0) == 0]
    plan['missing_fit_action_condition_support'] = missing_fit_support
    report = dict(scope='TRAIN_ONLY_TAXONOMY_AND_COVERAGE_NOT_PERFORMANCE_GATE',
        train_rows=len(records), hard_cases=len(cases),
        error_types_row_counts_overlap=dict(Counter(t for c in cases for t in c['error_types'])),
        exclusive_failure_stages=mined['error_accounting']['exclusive_failure_stages'],
        condition_step_errors_on_aligned_rows=mined['error_accounting']['condition_step_errors_on_aligned_rows'],
        coverage=full_coverage, fold_coverage=fold_coverage,
        missing_fit_action_condition_support=missing_fit_support,
        original_scorer_unchanged=True, label_changes=0, weights_changed=False,
        training_started=False, dev_test_predictions_read=0,
        interpretation='Slot errors are only counted when schema and action sequence align; other rows are not slot successes.')
    return cases, report, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-dir', type=Path, required=True)
    parser.add_argument('--release-manifest-sha256', required=True)
    parser.add_argument('--train-predictions', type=Path, required=True)
    parser.add_argument('--predictions-sha256', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    release = args.release_dir
    if (sha(release / 'manifest.json') != args.release_manifest_sha256
            or sha(args.train_predictions) != args.predictions_sha256):
        raise ValueError('input provenance hash changed')
    manifest = json.loads((release / 'manifest.json').read_text(encoding='utf-8'))
    names = ('reviewed_rows.jsonl', 'do_not_train_ids.json', 'upstream_eval_exclusion_hashes.jsonl',
             'test_exclusion_registry.json', 'supplemental_exclusion_registry.json')
    if manifest.get('split_frozen') is not True or any(
            sha(release / n) != manifest['artifact_sha256'].get(n) for n in names):
        raise ValueError('frozen release input changed')
    reviewed = load_jsonl(release / 'reviewed_rows.jsonl')
    test, supplement = release / 'test_exclusion_registry.json', release / 'supplemental_exclusion_registry.json'
    external_protected = external_registry(test) | external_registry(supplement, role='INDEPENDENT_VALIDATION')
    # The release validator requires its original Train/Val coverage; never falsify splits to satisfy it.
    audit = audit_rows(reviewed, external_protected=external_protected,
        protected_groups=registry_groups(test) | registry_groups(supplement))
    if not audit['data_ready_for_tokenization']:
        raise ValueError('approved release audit failed: ' + str(audit['global_errors']) + str(audit['issue_counts']))
    records = [r for r in reviewed if r['split'] == 'train']
    # Upstream exclusions also include the existing Dev, so apply them only to the Train mining pool.
    protected = (protected_hashes() | external_protected
        | {r['normalized_text_sha256'] for r in load_jsonl(release / 'upstream_eval_exclusion_hashes.jsonl')})
    held = set(json.loads((release / 'do_not_train_ids.json').read_text(encoding='utf-8'))['ids'])
    cases, report, plan = audit_train(records, load_jsonl(args.train_predictions), protected=protected, held_ids=held)
    report['dataset_version'] = manifest['dataset_version']
    out = output_directory(args.output_dir)
    out.mkdir(parents=True)
    write_rows(out / 'train_error_review.jsonl', cases)
    for name, value in [('report', report), ('grouped_exploration_plan', plan)]:
        (out / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Train错误分型与同组标签对照', '',
        '只有Train；原批准标签不改。非空条件包含关系不是语义等价判定，动作不齐时不猜测槽位错误。', '']
    for case in cases:
        lines.extend([f"## {case['sample_id']}", '', case['source_text'], '',
            '错误类型：' + ', '.join(case['error_types']), '',
            '差异：`' + json.dumps(case['diagnostic']['slot_differences'], ensure_ascii=False) + '`', '',
            '批准标签：`' + json.dumps(case['approved_label'], ensure_ascii=False) + '`', '',
            '模型原始输出：`' + case['model_raw'].replace('\n', ' ') + '`', ''])
        for sibling in case['same_group_review_context']:
            lines.extend([f"同组 {sibling['sample_id']}：{sibling['source_text']}", '',
                '`' + json.dumps(sibling['approved_label'], ensure_ascii=False) + '`', ''])
    (out / 'REVIEW.md').write_text('\n'.join(lines), encoding='utf-8')
    provenance = dict(dataset_manifest_sha256=args.release_manifest_sha256,
        predictions_sha256=args.predictions_sha256, train_records_sha256=canonical_hash(records),
        implementation_sha256=sha(Path(__file__)),
        dependencies_sha256={n: sha(Path(__file__).with_name(n)) for n in
            ('mine_train_hard_cases.py', 'diagnose.py', 'semantic_metrics.py', 'generalization_audit.py')},
        artifacts={p.name: sha(p) for p in sorted(out.iterdir())})
    (out / 'artifact_manifest.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    print(json.dumps(dict(train_rows=len(records), hard_cases=len(cases),
        error_types=report['error_types_row_counts_overlap'],
        folds=[dict(fold=f['fold'], fit=len(f['fit_ids']), development=len(f['development_ids'])) for f in plan['folds']],
        output=str(out)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
