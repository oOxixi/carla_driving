import pytest
from experiments.semantic_sft.data import PLAN


@pytest.fixture(autouse=True)
def legacy_two_reviewer_regression(monkeypatch):
    # Existing UNIT_ONLY fixtures exercise the stricter historical policy, not real approvals.
    # Owner-policy tests override this count explicitly; the production JSON is never changed.
    monkeypatch.setitem(PLAN['data_smoke_thresholds'], 'independent_reviewers', 2)
