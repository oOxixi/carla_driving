from experiments.semantic_sft.batches.boundaries_v2.build import drafts
from experiments.semantic_sft.data import audit_rows


def test_boundary_drafts_are_not_approved_or_assigned_and_have_no_schema_errors():
    rows = drafts()
    assert len(rows) == 9 and len({r['group_id'] for r in rows}) == 4
    assert all(r['label'] is None and not r['reviews'] and r['split'] == 'UNASSIGNED' for r in rows)
    assert all(r['annotation_status'] == 'DRAFT' and r['proposal']['status'] == 'UNREVIEWED' for r in rows)
    errors = {e for issue in audit_rows(rows)['issues'] for e in issue['errors']}
    assert errors <= {'MISSING_LABEL', 'HUMAN_REVIEW_NOT_APPROVED', 'SPLIT_UNASSIGNED'}
    labels = [r['proposal']['label'] for r in rows]
    assert [s['action'] for s in labels[0]['steps']] == ['AVOID_OBSTACLE']
    assert [s['action'] for s in labels[1]['steps']] == ['YIELD']
    assert labels[2]['prohibited_actions'] == {'PULL_OVER': True}
    assert [s['condition'] for s in labels[6]['steps']] == [None, None]
    assert len(set(s['condition'] for s in labels[7]['steps'])) == 1
    assert len(set(s['condition'] for s in labels[8]['steps'])) == 2
