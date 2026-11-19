"""Train-only group/action balancing. No resampling, new examples, or inference rules."""
from collections import Counter, defaultdict
import copy
import json
import math


def group_action_weights(rows, *, sequence_balance=False):
    if not rows or any(r['split'] != 'train' for r in rows):
        raise ValueError('weights may use Train rows only, never Dev or Test')
    if len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('duplicate training IDs')
    groups = defaultdict(list)
    for row in rows:
        groups[row['group_id']].append(row)
    actions = {g: {s['action'] for r in members for s in r['label']['steps']} for g, members in groups.items()}
    if any(not value for value in actions.values()):
        raise ValueError('training groups must have actions')
    frequency = Counter(a for value in actions.values() for a in value)
    raw = {g: sum(1 / math.sqrt(frequency[a]) for a in sorted(value)) / len(value) / len(groups[g])
           for g, value in actions.items()}
    mean = sum(raw[r['group_id']] for r in rows) / len(rows)
    clipped = [max(0.5, min(2.0, raw[r['group_id']] / mean)) for r in rows]
    policy = 'inverse_sqrt_action_group_frequency_divided_by_group_size_clip_then_mean_one_v1'
    sequence_report = {}
    if sequence_balance:
        pairs = []
        for row in rows:
            ordered = [step['action'] for step in row['label']['steps']]
            pairs.append(set(zip(ordered, ordered[1:])))
        counts = Counter(pair for _, pair in {(r['group_id'], p) for r, ps in zip(rows, pairs) for p in ps})
        # Boost observed rare transitions without duplicating rows or learning Dev-specific patterns.
        boost = [max((1 + 0.35 / counts[p] for p in ps if counts[p] <= 2), default=1.0) for ps in pairs]
        clipped = [w * factor for w, factor in zip(clipped, boost)]
        policy = 'group_action_plus_bounded_rare_transition_boost_v1'
        sequence_report = dict(transition_group_frequency={' -> '.join(p): n for p, n in sorted(counts.items())},
                               transition_boosted_rows=sum(factor > 1 for factor in boost),
                               transition_max_multiplier=1.35)
    normalizer = sum(clipped) / len(rows)
    return dict(policy=policy,
        statistics_split='train', group_action_frequency=dict(sorted(frequency.items())),
        clip_before_final_normalization=[0.5, 2.0], each_row_visited_once_per_epoch=True,
        samples=[dict(sample_id=r['sample_id'], group_id=r['group_id'], weight=w / normalizer)
                 for r, w in zip(rows, clipped)], **sequence_report)


def train_replay_weights(rows, base_report, cases):
    """Bounded Train-error boost; never relabel, resample, or repair model outputs."""
    from .data import canonical_hash, source_hash
    from .semantic_metrics import score_text
    if not rows or any(r.get('split') != 'train' for r in rows):
        raise ValueError('hard-case weights require Train only')
    by_id = {r['sample_id']: r for r in rows}
    samples = base_report['samples']
    if (len(by_id) != len(rows) or [s['sample_id'] for s in samples] != [r['sample_id'] for r in rows]
            or base_report.get('statistics_split') != 'train'):
        raise ValueError('base weights must match this exact ordered Train cohort')
    if not cases or len({c['sample_id'] for c in cases}) != len(cases):
        raise ValueError('hard-case input must be nonempty and unique')
    factors, decisions = {}, []
    for case in cases:
        identifier = case['sample_id']
        if identifier not in by_id or case.get('split') != 'train':
            raise ValueError('Dev/Test/unknown IDs cannot affect Train weights')
        row = by_id[identifier]
        if (case.get('source_sha256') != source_hash(row['source_text']) or case.get('source_text') != row['source_text']
                or case.get('approved_label_sha256') != canonical_hash(row['label'])
                or case.get('approved_label') != row['label']):
            raise ValueError('hard-case labels/source differ from the approved Train release')
        checked = score_text(row['source_text'], case['model_raw'], row['label'],
                             complete=case['score']['checks']['complete'])
        if checked['checks'] != case['score']['checks'] or checked['checks']['semantic_exact']:
            raise ValueError('hard-case score must be a verified failure under the unchanged scorer')
        checks = checked['checks']
        retention = case.get('reference_regressions', [])
        if not isinstance(retention, list) or not set(retention) <= {'raw_action_order_exact', 'semantic_exact'}:
            raise ValueError('unsupported Train retention signal')
        condition_only = (not checks['condition_exact'] and all(value for key, value in checks.items()
            if key not in {'condition_exact', 'semantic_exact'}))
        nonnull_span_only = condition_only and all(gold['condition'] is not None and actual['condition'] is not None
            for gold, actual in zip(row['label']['steps'], checked['observed']['steps'])
            if gold['condition'] != actual['condition'])
        multiplier = 2.0 if retention else 1.0 if nonnull_span_only else 1.5
        reason = 'reference_train_retention' if retention else 'defer_nonnull_condition_span_review' if nonnull_span_only else 'verified_train_failure'
        factors[identifier] = multiplier
        decisions.append(dict(sample_id=identifier, multiplier=multiplier, reason=reason))
    original = [float(s['weight']) for s in samples]
    if any(not math.isfinite(w) or w <= 0 for w in original):
        raise ValueError('invalid base weights')
    updated = [w * factors.get(r['sample_id'], 1.0) for r, w in zip(rows, original)]
    mean = sum(updated) / len(updated)
    result = copy.deepcopy(base_report)
    result['base_policy'] = result['policy']
    result['policy'] += '_bounded_train_replay_boost_v1'
    result['base_clip_before_replay_layer'] = result.pop('clip_before_final_normalization')
    result['samples'] = [dict(sample, base_weight=w, replay_multiplier=factors.get(row['sample_id'], 1.0), weight=new / mean)
        for row, sample, w, new in zip(rows, samples, original, updated)]
    result['train_replay_policy'] = dict(failure_multiplier=1.5, retention_multiplier=2.0,
        decisions=decisions, boosted_rows=sum(d['multiplier'] > 1 for d in decisions),
        deferred_span_only_rows=sum(d['multiplier'] == 1 for d in decisions),
        final_mean_weight=1.0, each_row_visited_once_per_epoch=True,
        no_source_label_group_or_split_changes=True, model_outputs_used_as_labels=False,
        note='Span-only cases are deferred, not declared correct. Retention comes from frozen Train replay, not Dev.')
    return result


def load_train_replay_audit(directory, *, expected_dataset_manifest_sha256):
    from .train import sha
    directory = directory.resolve(strict=True)
    manifest = json.loads((directory / 'artifact_manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['artifacts'].items():
        if name not in {'report.json', 'train_hard_cases.jsonl', 'REVIEW.md'} or sha(directory / name) != expected:
            raise ValueError('hard-case audit artifact changed or is unsupported')
    if not {'report.json', 'train_hard_cases.jsonl'} <= set(manifest['artifacts']):
        raise ValueError('hard-case audit is incomplete')
    report = json.loads((directory / 'report.json').read_text(encoding='utf-8'))
    if (report.get('scope') != 'TRAIN_ONLY_HARD_CASE_AUDIT_NOT_NEW_DATA_OR_WEIGHT_UPDATE'
            or report.get('dataset_manifest_sha256') != expected_dataset_manifest_sha256
            or report.get('label_changes') != 0 or report.get('dev_or_test_rows_imported') != 0
            or report.get('model_predictions_used_as_labels') is not False):
        raise ValueError('hard-case audit is not bound to unchanged Train labels in this release')
    cases = [json.loads(line) for line in (directory / 'train_hard_cases.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    if report.get('hard_cases') != len(cases):
        raise ValueError('hard-case audit count mismatch')
    if {c['sample_id'] for c in cases} & set(report.get('held_ids', [])):
        raise ValueError('held samples cannot affect training weights')
    declared = report.get('reference_retention_regressions', {})
    for key in ('raw_action_order_exact', 'semantic_exact'):
        actual = {c['sample_id'] for c in cases if key in c.get('reference_regressions', [])}
        if actual != set(declared.get(key, [])):
            raise ValueError('retention cases do not match the frozen Train audit')
        if actual and (not report.get('reference_provenance') or not report.get('reference_train_rows')):
            raise ValueError('retention boost requires a recorded frozen Train reference')
    return cases, dict(artifact_manifest_sha256=sha(directory / 'artifact_manifest.json'),
        dataset_manifest_sha256=expected_dataset_manifest_sha256,
        source_candidate_manifest_sha256=report['candidate_manifest_sha256'],
        train_prediction_sha256=report['prediction_sha256'], reference_provenance=report.get('reference_provenance'))
