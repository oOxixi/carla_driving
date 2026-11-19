"""Model-output scoring only: no repair, task inference, execution, or Test access."""
import json
import math

import jsonschema
from qwen_service.shadow_planner import _unique_object
from qwen_service.task_understanding import TASK_SCHEMA, validate_extraction

SLOT_FIELDS = ('target_text', 'direction', 'speed_kph', 'gap_m', 'condition')


def score_text(source, raw, expected, *, complete):
    checks = dict(json_valid=False, schema_valid=False, extraction_valid=False, complete=complete,
        raw_action_order_exact=False, step_count_exact=False, prohibited_actions_exact=False,
        confirmation_exact=False, semantic_exact=False, **{f + '_exact': False for f in SLOT_FIELDS})
    observed, error = None, None
    def reject_constant(value):
        raise ValueError('non-finite JSON constant: ' + value)
    try:
        observed = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=reject_constant)
        checks['json_valid'] = True
        # Do not let unrelated direction/prohibition format failures zero raw action understanding.
        if isinstance(observed, dict) and isinstance(observed.get('steps'), list):
            steps = observed['steps']
            checks['raw_action_order_exact'] = complete and all(isinstance(s, dict) and isinstance(s.get('action'), str) for s in steps) and (
                [s['action'] for s in steps] == [s['action'] for s in expected['steps']])
        jsonschema.Draft202012Validator(TASK_SCHEMA).validate(observed)
        checks['schema_valid'] = True
        try:
            validate_extraction(source, observed)
            checks['extraction_valid'] = True
        except (ValueError, jsonschema.ValidationError) as exc:
            error = str(exc)
        actual, gold = observed['steps'], expected['steps']
        checks['step_count_exact'] = len(actual) == len(gold)
        for field in SLOT_FIELDS:
            def equal(a, b):
                if type(a) in (int, float) and type(b) in (int, float):
                    return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= 1e-6
                return a == b
            checks[field + '_exact'] = len(actual) == len(gold) and all(equal(a[field], b[field]) for a, b in zip(actual, gold))
        checks['prohibited_actions_exact'] = observed['prohibited_actions'] == expected['prohibited_actions']
        checks['confirmation_exact'] = observed['requires_confirmation'] == expected['requires_confirmation']
        checks['semantic_exact'] = all(value for key, value in checks.items() if key != 'semantic_exact')
    except (ValueError, TypeError, jsonschema.ValidationError) as exc:
        error = str(exc)
    return dict(checks=checks, observed=observed, error=error)


def summarize(rows):
    if not rows or len({row['sample_id'] for row in rows}) != len(rows):
        raise ValueError('every development sample must have exactly one scored generation')
    return dict(cases=len(rows), correct_cases={key: sum(row['score']['checks'][key] for row in rows)
        for key in rows[0]['score']['checks']}, family_semantic_correct={family: sum(
            row['score']['checks']['semantic_exact'] for row in rows if row['semantic_family'] == family)
            for family in sorted({row['semantic_family'] for row in rows})})


def baseline_regressions(candidate, baseline):
    if (not baseline or len({r['sample_id'] for r in candidate}) != len(candidate)
            or len({r['sample_id'] for r in baseline}) != len(baseline)
            or {r['sample_id'] for r in candidate} != {r['sample_id'] for r in baseline}):
        raise ValueError('paired development generations must cover the same unique sample IDs')
    by_id = {r['sample_id']: r for r in candidate}
    return {field: [r['sample_id'] for r in baseline if r['score']['checks'][field]
                   and not by_id[r['sample_id']]['score']['checks'][field]]
            for field in ('raw_action_order_exact', 'semantic_exact')}


def selection_rank(summary, loss):
    if not math.isfinite(loss):
        raise ValueError('non-finite loss cannot select a candidate')
    correct = summary['correct_cases']
    return correct['semantic_exact'], correct['raw_action_order_exact'], correct['extraction_valid'], -float(loss)
