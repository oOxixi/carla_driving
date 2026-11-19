from collections import Counter
import copy

import pytest

from experiments.semantic_sft.batches.semantic_contrasts_v1.build import build_batch, check_materials, coverage, signature
from experiments.semantic_sft.data import audit_rows, text_hash


def test_contrasts_are_72_unapproved_records_in_18_four_case_groups():
    rows, groups = build_batch()
    assert len(rows) == len({r['sample_id'] for r in rows}) == len({text_hash(r['source_text']) for r in rows}) == 72
    assert len(groups) == 18
    assert set(Counter(r['group_id'] for r in rows).values()) == {4}
    assert set(Counter(r['semantic_family'] for r in rows).values()) == {12}
    assert all(r['label'] is None and not r['reviews'] and r['annotation_status'] == 'DRAFT'
               and r['split'] == 'UNASSIGNED' for r in rows)
    assert audit_rows(rows)['issue_counts']['MISSING_LABEL'] == 72
    for group in groups:
        # Require differing task/condition/prohibition semantics, not just target names or numbers.
        assert len({signature(r['proposal']['label']) for r in rows if r['group_id'] == group}) >= 2


def test_coverage_has_every_action_and_new_turn_lane_wording_without_implied_targets():
    rows, _ = build_batch()
    report = coverage(rows, drafts=True)
    assert all(v['steps'] > 0 for v in report['actions'].values())
    assert report['actions']['TURN_LEFT']['distinct_evidence'] >= 5
    assert report['actions']['TURN_RIGHT']['distinct_evidence'] >= 5
    assert report['actions']['CHANGE_LANE_RIGHT']['distinct_evidence'] >= 5
    for row in rows:
        for step in row['proposal']['label']['steps']:
            if step['action'] in {'TURN_LEFT','TURN_RIGHT','CHANGE_LANE_LEFT','CHANGE_LANE_RIGHT'}:
                assert step['target_text'] is None
    follow = next(r for r in rows if r['source_text'].startswith('跟随左前方的黄色轿车'))
    assert follow['proposal']['label']['steps'][0]['direction'] is None
    assert follow['proposal']['label']['steps'][0]['target_text'] == '左前方的黄色轿车'


def test_positive_controls_and_shared_conditions_prevent_blanket_hold_or_condition_loss():
    rows, _ = build_batch()
    ambiguous = [r['proposal']['label'] for r in rows if r['semantic_family'] == 'ambiguity']
    assert {p['requires_confirmation'] for p in ambiguous} == {True, False}
    shared = [p for r in rows for p in [r['proposal']['label']]
              if any(n >= 2 for condition,n in Counter(s['condition'] for s in p['steps'] if s['condition']).items())]
    assert len(shared) >= 3
    assert all(p['steps'][0]['action'] == 'HOLD' for p in ambiguous if p['requires_confirmation'])


@pytest.mark.parametrize('change', ['existing_duplicate', 'normalized_duplicate', 'protected_text', 'protected_group', 'approved'])
def test_draft_checks_reject_leakage_duplicates_and_implicit_approval(change):
    rows, _ = build_batch()
    rows = copy.deepcopy(rows)
    old, protected, groups = [], set(), set()
    if change == 'existing_duplicate':
        old = [rows[0]]
    elif change == 'normalized_duplicate':
        rows[1]['source_text'] = ' '.join(rows[0]['source_text'])
    elif change == 'protected_text':
        protected = {text_hash(rows[0]['source_text'])}
    elif change == 'protected_group':
        groups = {rows[0]['group_id']}
    else:
        rows[0]['annotation_status'] = 'APPROVED'
    with pytest.raises(ValueError):
        check_materials(rows, old, protected, groups)
