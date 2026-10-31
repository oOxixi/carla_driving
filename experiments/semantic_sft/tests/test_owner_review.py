import copy

from experiments.semantic_sft.data import PLAN, audit_rows, validate_plan_safety
from experiments.semantic_sft.review import first_review
from experiments.semantic_sft.tests.test_review import packets


def test_explicit_owner_policy_finalizes_only_owner_and_preserves_gaps(monkeypatch):
    monkeypatch.setitem(PLAN['data_smoke_thresholds'],'independent_reviewers',1)
    kwargs=dict(reviewed_at='2026-11-01T12:00:00+08:00',approval_reference='UNIT_ONLY',approval_quote='UNIT_ONLY')
    rows,receipt=first_review(packets(),reviewer_id=PLAN['review_owner_id'],**kwargs)
    assert receipt['owner_finalized_rows']==21
    assert sum(row['annotation_status']=='APPROVED' for row in rows)==21
    assert sum(row['label'] is None for row in rows)==3
    assert all(len(row['reviews'])==1 for row in rows if row['label'] is not None)
    assert 'OWNER_LABEL_REVIEW_REQUIRED' not in audit_rows(rows)['issue_counts']
    assert not audit_rows(rows)['ready_for_training']
    peer,_=first_review(packets(),reviewer_id='UNIT_ONLY_NOT_OWNER',**kwargs)
    assert all(row['annotation_status']=='DRAFT' for row in peer)
    assert audit_rows(peer)['issue_counts']['OWNER_LABEL_REVIEW_REQUIRED']==21
    rows[0]['label']['requires_confirmation']=True
    assert audit_rows(rows)['issue_counts']['OWNER_LABEL_REVIEW_REQUIRED']==1


def test_review_requirement_cannot_be_disabled():
    import pytest
    invalid=copy.deepcopy(PLAN)
    invalid['data_smoke_thresholds']['independent_reviewers']=0
    with pytest.raises(ValueError,match='review policy'):
        validate_plan_safety(invalid)
