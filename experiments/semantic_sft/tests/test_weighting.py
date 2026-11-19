import copy

import pytest

from experiments.semantic_sft.weighting import group_action_weights


def row(identifier, group, action, split='train'):
    return dict(sample_id=identifier, group_id=group, split=split, label=dict(steps=[dict(action=action)]))


def test_weights_use_group_frequency_not_template_duplicate_count():
    rows = [row(f'F{i}', 'F', 'FOLLOW') for i in range(5)] + [row('L', 'L', 'TURN_LEFT')]
    before = copy.deepcopy(rows)
    report = group_action_weights(rows)
    weights = [r['weight'] for r in report['samples']]
    assert report['group_action_frequency'] == {'FOLLOW': 1, 'TURN_LEFT': 1}
    assert sum(weights) / len(weights) == pytest.approx(1)
    assert weights[-1] > weights[0] > 0
    assert rows == before
    assert [r['sample_id'] for r in report['samples']] == [r['sample_id'] for r in rows]


def test_rare_action_has_higher_weight_for_equal_group_sizes():
    rows = [row(f'F{i}', f'FG{i}', 'FOLLOW') for i in range(5)] + [row('L', 'L', 'TURN_LEFT')]
    weights = [r['weight'] for r in group_action_weights(rows)['samples']]
    assert weights[-1] > weights[0]
    assert group_action_weights(rows) == group_action_weights(rows)


@pytest.mark.parametrize('rows', [[], [row('V', 'V', 'FOLLOW', 'val')],
    [row('T', 'T', 'TURN_LEFT', 'test')], [row('A', 'A', 'FOLLOW'), row('A', 'B', 'STOP')]])
def test_weights_reject_validation_test_empty_and_duplicate_ids(rows):
    with pytest.raises(ValueError):
        group_action_weights(rows)
    with pytest.raises(ValueError):
        group_action_weights(rows, sequence_balance=True)


def test_transition_boost_counts_ordered_pairs_by_group_and_preserves_legacy():
    rows = [row(identifier, group, 'TURN_RIGHT') for identifier, group in
            [('A', 'G1'), ('B', 'G1'), ('C', 'G2'), ('D', 'G3'), ('E', 'G4'), ('F', 'G5')]]
    for item in rows[:4]:
        item['label']['steps'].append({'action': 'KEEP_LANE'})
    rows[4]['label']['steps'] = [{'action': 'KEEP_LANE'}, {'action': 'TURN_RIGHT'}]
    frozen = copy.deepcopy(rows)
    legacy = group_action_weights(rows)
    result = group_action_weights(rows, sequence_balance=True)
    assert group_action_weights(rows, sequence_balance=False) == legacy
    assert result['transition_group_frequency'] == {'KEEP_LANE -> TURN_RIGHT': 1, 'TURN_RIGHT -> KEEP_LANE': 3}
    assert result['transition_boosted_rows'] == 1
    assert sum(r['weight'] for r in result['samples']) == pytest.approx(len(rows))
    ratios = [new['weight'] / old['weight'] for new, old in zip(result['samples'], legacy['samples'])]
    assert ratios[4] / ratios[5] == pytest.approx(1.35)
    assert ratios[:4] == pytest.approx([ratios[5]] * 4)
    assert rows == frozen
