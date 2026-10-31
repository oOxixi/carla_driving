from collections import Counter
from experiments.semantic_sft.evaluation.test_candidate_v1 import candidates
from experiments.semantic_sft.data import audit_rows


def test_candidates_are_held_apart_from_training_and_not_frozen_or_approved():
    rows=candidates()
    assert len(rows)==len({r['case_id'] for r in rows})==len({r['evaluation_group_id'] for r in rows})==12
    assert set(Counter(r['semantic_family'] for r in rows).values())=={2}
    assert all(r['reserved_for_evaluation'] and r['status']=='TEST_CANDIDATE_NOT_FROZEN' for r in rows)
    report=audit_rows(rows)
    assert all(i['errors'][0].startswith('INVALID_RECORD_SCHEMA') for i in report['issues'])
    assert not report['data_ready_for_tokenization']
