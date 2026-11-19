import copy
import json

import pytest

from experiments.semantic_sft.semantic_metrics import score_text, summarize, baseline_regressions, selection_rank


def example():
    source = '先向右转，路灯亮起后靠边停车'
    first = dict(action='TURN_RIGHT', target_text=None, direction='RIGHT', speed_kph=None, gap_m=None, condition=None, evidence='先向右转')
    second = dict(first, action='PULL_OVER', direction=None, condition='路灯亮起后', evidence='靠边停车')
    return source, dict(steps=[first, second], prohibited_actions={}, requires_confirmation=False)


def row(identifier='UNIT', *, bad_direction=False, missing_step=False):
    source, expected = example()
    predicted = copy.deepcopy(expected)
    if bad_direction: predicted['steps'][0]['direction'] = '右边'
    if missing_step: predicted['steps'].pop()
    return dict(sample_id=identifier, semantic_family='UNIT_ONLY', score=score_text(source, json.dumps(predicted), expected, complete=True))


def test_raw_action_metric_is_not_zeroed_by_other_protocol_failures():
    result = row(bad_direction=True)['score']
    assert result['checks']['raw_action_order_exact']
    assert not result['checks']['schema_valid'] and not result['checks']['semantic_exact']


@pytest.mark.parametrize('change', ['condition', 'prohibition', 'confirmation', 'hallucinated_evidence', 'incomplete', 'missing_step'])
def test_semantic_match_requires_all_tasks_bindings_and_literal_quotes(change):
    source, expected = example()
    predicted = copy.deepcopy(expected)
    if change == 'condition': predicted['steps'][1]['condition'] = None
    elif change == 'prohibition': predicted['prohibited_actions'] = {'FOLLOW': True}
    elif change == 'confirmation': predicted['requires_confirmation'] = True
    elif change == 'hallucinated_evidence': predicted['steps'][0]['evidence'] = '编造的右转'
    elif change == 'missing_step': predicted['steps'].pop()
    result = score_text(source, json.dumps(predicted), expected, complete=change != 'incomplete')
    assert not result['checks']['semantic_exact']


def test_valid_alternative_evidence_does_not_change_semantic_score():
    source, expected = example()
    predicted = copy.deepcopy(expected)
    predicted['steps'][0]['evidence'] = '向右转'
    assert score_text(source, json.dumps(predicted), expected, complete=True)['checks']['semantic_exact']


@pytest.mark.parametrize('raw', ['```json\n{}\n```', '{"steps":[],"steps":[]}', '{"x":NaN}'])
def test_no_model_output_repair_or_duplicate_key_recovery(raw):
    source, expected = example()
    assert not score_text(source, raw, expected, complete=True)['checks']['json_valid']


def test_selection_prioritizes_generated_semantics_over_lower_loss_and_reports_regressions():
    correct = [row()]
    wrong = [row(missing_step=True)]
    assert selection_rank(summarize(correct), .8) > selection_rank(summarize(wrong), .01)
    assert baseline_regressions(wrong, correct) == {'raw_action_order_exact':['UNIT'], 'semantic_exact':['UNIT']}
    assert not any(baseline_regressions(correct, wrong).values())
    # Keeping actions but breaking protocol must not hide a previously complete success either.
    assert baseline_regressions([row(bad_direction=True)], correct)['semantic_exact'] == ['UNIT']


@pytest.mark.parametrize('bad', [[], [row('OTHER')], [row(), row()]])
def test_pairing_cannot_silently_skip_or_duplicate_development_cases(bad):
    with pytest.raises(ValueError): baseline_regressions(bad, [row()])
