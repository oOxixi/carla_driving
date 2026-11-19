import copy
import json

import pytest

from experiments.semantic_sft.generalization_audit import error_accounting, train_group_folds
from experiments.semantic_sft.semantic_metrics import score_text
from experiments.semantic_sft.batches.boundaries_v2.build import step


def test_internal_folds_preserve_groups_and_original_rows():
    rows = [dict(sample_id=f'{family}_{g}_{i}', group_id=f'{family}_{g}', semantic_family=family, split='train')
            for family in ('a', 'b') for g in range(5) for i in range(2)]
    before = copy.deepcopy(rows)
    plan = train_group_folds(rows)
    assert rows == before and plan == train_group_folds(rows)
    for f in plan['folds']:
        fit, dev = set(f['fit_ids']), set(f['development_ids'])
        assert len(fit) == 16 and len(dev) == 4 and not fit & dev
        assert {r['group_id'] for r in rows if r['sample_id'] in fit}.isdisjoint(
            {r['group_id'] for r in rows if r['sample_id'] in dev})
    assert sorted(i for f in plan['folds'] for i in f['development_ids']) == sorted(r['sample_id'] for r in rows)
    rows[0]['split'] = 'val'
    with pytest.raises(ValueError, match='Train only'):
        train_group_folds(rows)


def test_accounting_uses_frozen_scores_and_keeps_denominators_separate():
    label = dict(steps=[step('STOP', 'UNIT_STOP', condition='UNIT_GATE')], prohibited_actions={}, requires_confirmation=False)
    record = dict(sample_id='UNIT_A', source_text='UNIT_GATE UNIT_STOP', label=label)
    observed = copy.deepcopy(label)
    observed['steps'][0]['condition'] = None
    raw = json.dumps(observed)
    prediction = dict(sample_id='UNIT_A', raw=raw, score=score_text(record['source_text'], raw, label, complete=True))
    result = error_accounting([record], [prediction])
    assert result['exclusive_failure_stages'] == {'slots_or_global_flags': 1}
    assert result['condition_step_errors_on_aligned_rows'] == {'condition_missing': 1}
    prediction['score']['checks']['semantic_exact'] = True
    with pytest.raises(ValueError, match='stored score'):
        error_accounting([record], [prediction])
