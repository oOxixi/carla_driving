"""Additive error accounting and Train-only grouped exploration plans; never rescore by relaxed rules."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from .data import audit_rows, canonical_hash, load_jsonl, output_directory
from .semantic_metrics import score_text
from .prepare import external_registry, registry_groups


def error_accounting(records, predictions):
    expected = {r['sample_id']: r for r in records}
    if (len(expected) != len(records) or len(predictions) != len(records)
            or len({p['sample_id'] for p in predictions}) != len(predictions)
            or {p['sample_id'] for p in predictions} != set(expected)):
        raise ValueError('require exactly one generation per expected record')
    stages, slots = Counter(), Counter()
    aligned = 0
    for p in predictions:
        r = expected[p['sample_id']]
        score = score_text(r['source_text'], p['raw'], r['label'], complete=p['score']['checks']['complete'])
        if score['checks'] != p['score']['checks']:
            raise ValueError('stored score disagrees with unmodified scorer')
        c = score['checks']
        stage = ('incomplete' if not c['complete'] else 'json' if not c['json_valid'] else
                 'schema' if not c['schema_valid'] else 'actions' if not c['raw_action_order_exact'] else
                 'literal_or_contract' if not c['extraction_valid'] else
                 'slots_or_global_flags' if not c['semantic_exact'] else 'correct')
        stages[stage] += 1
        if c['schema_valid'] and c['raw_action_order_exact'] and c['complete']:
            aligned += 1
            for gold, observed in zip(r['label']['steps'], score['observed']['steps']):
                g, o = gold['condition'], observed['condition']
                if g != o:
                    slots['condition_missing' if o is None else 'condition_extra' if g is None else 'condition_span_or_scope'] += 1
    return dict(cases=len(records), exclusive_failure_stages=dict(stages), action_aligned_schema_valid_rows=aligned,
                condition_step_errors_on_aligned_rows=dict(slots), original_scorer_unchanged=True,
                stage_order='incomplete/json/schema/actions/literal_or_contract/slots_or_global_flags/correct')


def train_group_folds(rows, folds=5, seed=20261107):
    if not rows or any(r['split'] != 'train' for r in rows):
        raise ValueError('internal folds must use original Train only')
    if type(folds) is not int or folds < 2 or len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('invalid fold count or duplicate IDs')
    families, group_family = defaultdict(set), {}
    for r in rows:
        group, family = r['group_id'], r['semantic_family']
        if group in group_family and group_family[group] != family:
            raise ValueError('group spans semantic families')
        group_family[group] = family
        families[family].add(group)
    assignment = {}
    for family, groups in sorted(families.items()):
        if len(groups) < folds:
            raise ValueError('each family needs at least one group per fold')
        ordered = sorted(groups, key=lambda g: hashlib.sha256(f'{seed}|{family}|{g}'.encode()).hexdigest())
        assignment.update({g: i % folds for i, g in enumerate(ordered)})
    splits = []
    for f in range(folds):
        train = [r['sample_id'] for r in rows if assignment[r['group_id']] != f]
        validation = [r['sample_id'] for r in rows if assignment[r['group_id']] == f]
        assert set(train).isdisjoint(validation) and len(train) + len(validation) == len(rows)
        splits.append(dict(fold=f, fit_ids=train, development_ids=validation))
    return dict(scope='TRAIN_ONLY_GROUPED_EXPLORATION_NOT_NEW_TEST', seed=seed, folds=splits,
                group_to_fold=assignment, original_split_changed=False, weights_must_start_from_base=True,
                existing_adapters_have_seen_all_rows=True, ready_for_training=False)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed-rows', type=Path, required=True)
    parser.add_argument('--dev-predictions', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    rows = load_jsonl(args.reviewed_rows)
    test = args.reviewed_rows.parent / 'test_exclusion_registry.json'
    supplement = args.reviewed_rows.parent / 'supplemental_exclusion_registry.json'
    if not audit_rows(rows, external_protected=external_registry(test),
                      supplemental_protected=external_registry(supplement, role='INDEPENDENT_VALIDATION'),
                      protected_groups=registry_groups(test) | registry_groups(supplement))['data_ready_for_tokenization']:
        raise ValueError('original reviewed rows fail current protected-data audit')
    train = [r for r in rows if r['split'] == 'train']
    dev = [r for r in rows if r['split'] == 'val']
    plan = train_group_folds(train, folds=4)
    if any(len(f['fit_ids']) < 200 or len(f['development_ids']) < 50 for f in plan['folds']):
        raise ValueError('internal fold sizes do not meet the existing engineering minimums')
    stats = dict(train_rows=len(train), train_groups=len(plan['group_to_fold']),
                 train_steps=sum(len(r['label']['steps']) for r in train),
                 shared_condition_cases=sum(len([s['condition'] for s in r['label']['steps'] if s['condition']]) >
                     len({s['condition'] for s in r['label']['steps'] if s['condition']}) for r in train))
    review = [dict(sample_id=r['sample_id'], source_text=r['source_text'],
                   reason='Potential referent switch: yielding target differs from later pedestrian condition; human review, not automatic relabel.')
              for r in train if any(s['condition'] == '确认行人通过后' for s in r['label']['steps'])
              and any(s['action'] == 'YIELD' and s['target_text'] and '人' not in s['target_text']
                      for s in r['label']['steps'])]
    output = output_directory(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)
    payloads = dict(grouped_exploration_plan=plan, data_census=stats, contextual_review_candidates=review,
                    dev_error_accounting=error_accounting(dev, load_jsonl(args.dev_predictions)))
    for name, obj in payloads.items():
        (output / (name + '.json')).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    manifest = dict(input_reviewed_rows_sha256=hashlib.sha256(args.reviewed_rows.read_bytes()).hexdigest(),
                    predictions_sha256=hashlib.sha256(args.dev_predictions.read_bytes()).hexdigest(),
                    payload_hashes={k: canonical_hash(v) for k, v in payloads.items()}, training_started=False)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(dict(census=stats, folds=[dict(fold=f['fold'], fit=len(f['fit_ids']), development=len(f['development_ids']))
        for f in plan['folds']], contextual_review_cases=len(review), dev_accounting=payloads['dev_error_accounting'])))


if __name__ == '__main__':
    main()
