import copy

import pytest

from experiments.semantic_sft.data import PLAN, canonical_hash, source_hash
from experiments.semantic_sft.revision import SYSTEM_V3, apply_condition_revision, condition_proposals
from experiments.semantic_sft.tests.test_preparation import approved


def unit_revision(monkeypatch):
    # UNIT_ONLY metadata; never a real owner review or a business training record.
    monkeypatch.setitem(PLAN, 'review_owner_id', 'UNIT_ONLY_OWNER')
    row = approved()
    row['source_text'] = '在前方路口向左转'
    row['source_sha256'] = source_hash(row['source_text'])
    row['label']['steps'][0].update(action='TURN_LEFT', direction='LEFT', evidence=row['source_text'])
    proposals = condition_proposals([row])
    approval = dict(reviewer_id='UNIT_ONLY_OWNER', approval_reference='UNIT_ONLY', approval_quote='UNIT_ONLY',
                    reviewed_at='2026-11-02T02:00:00+08:00', proposal_sha256=canonical_hash(proposals))
    return [row], proposals, approval


def test_revision_preserves_parent_source_splits_groups_actions_and_old_reviews(monkeypatch):
    rows, proposals, approval = unit_revision(monkeypatch)
    before = copy.deepcopy(rows)
    updated, receipt = apply_condition_revision(rows, proposals, approval)
    assert rows == before
    assert len(receipt['accepted_rows']) == 1
    assert updated[0]['label']['steps'][0]['condition'] == '在前方路口'
    assert updated[0]['reviews'][:-1] == before[0]['reviews']
    assert updated[0]['reviews'][-1]['label_sha256'] == canonical_hash(updated[0]['label'])
    for key in ('source_text', 'source_sha256', 'group_id', 'split', 'proposal'):
        assert updated[0].get(key) == rows[0].get(key)


@pytest.mark.parametrize('change', ['no_approval', 'no_timezone', 'stale_label', 'split', 'action', 'duplicate', 'not_literal', 'empty'])
def test_revision_cannot_reuse_old_approval_change_actions_or_move_groups(monkeypatch, change):
    rows, proposals, approval = unit_revision(monkeypatch)
    if change == 'no_approval':
        approval['approval_quote'] = ''
    elif change == 'no_timezone':
        approval['reviewed_at'] = '2026-11-02T02:00:00'
    elif change == 'stale_label':
        rows[0]['label']['requires_confirmation'] = True
    elif change == 'split':
        proposals[0]['split'] = 'val'
    elif change == 'action':
        proposals[0]['label']['steps'][0]['action'] = 'YIELD'
    elif change == 'duplicate':
        proposals *= 2
    elif change == 'not_literal':
        proposals[0]['label']['steps'][0]['condition'] = 'UNIT_HALLUCINATION'
    else:
        proposals = []
    if change != 'no_approval':
        approval['proposal_sha256'] = canonical_hash(proposals)
    with pytest.raises(ValueError):
        apply_condition_revision(rows, proposals, approval)


def test_v3_prompt_is_protocol_not_heldout_examples():
    assert 'prohibited_actions是对象' in SYSTEM_V3
    assert 'direction只能是LEFT、RIGHT、STRAIGHT或null' in SYSTEM_V3
    assert 'condition也包括明确指定的将来到达地点' in SYSTEM_V3
    assert 'SCV1_' not in SYSTEM_V3 and 'EXP_V2_' not in SYSTEM_V3
