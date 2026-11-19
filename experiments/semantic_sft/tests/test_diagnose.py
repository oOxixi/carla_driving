import copy
import json

import pytest

from experiments.semantic_sft.diagnose import diagnose_case, prompt_only
from experiments.semantic_sft.semantic_metrics import score_text
from experiments.semantic_sft.tests.test_preparation import approved


def test_generation_prefix_excludes_every_assistant_gold_token():
    record = dict(prompt_tokens=2, input_ids=[7, 8, 111, 222], labels=[-100, -100, 111, 222])
    assert prompt_only(record) == [7, 8]
    assert record['input_ids'] == [7, 8, 111, 222]
    for bad in (dict(record, prompt_tokens=4), dict(record, labels=[7, -100, 111, 222])):
        with pytest.raises(ValueError):
            prompt_only(bad)


def test_diagnosis_never_changes_old_scores_or_repairs_answers():
    row = approved()
    source, expected = row['source_text'], row['label']
    actual = copy.deepcopy(expected)
    actual['steps'][0]['condition'] = '停车'
    raw = json.dumps(actual, ensure_ascii=False)
    result = diagnose_case(source, raw, expected, complete=True)
    assert result['score'] == score_text(source, raw, expected, complete=True)
    assert 'CONDITION_EXTRA' in result['diagnostic']['tags']
    assert 'LITERAL_OR_CONTRACT_REJECTION' in result['diagnostic']['tags']
    assert result['score']['observed'] == actual
    assert expected['steps'][0]['condition'] is None


def test_wrong_actions_and_schema_failures_do_not_create_fake_slot_errors():
    row = approved()
    actual = copy.deepcopy(row['label'])
    actual['steps'][0].update(action='FOLLOW', target_text='UNIT_OTHER', condition='UNIT_OTHER')
    result = diagnose_case(row['source_text'], json.dumps(actual), row['label'], complete=True)
    assert 'ACTION_SEQUENCE_MISMATCH' in result['diagnostic']['tags']
    assert result['diagnostic']['slot_differences'] == []
    actual['steps'][0]['evidence'] = None
    result = diagnose_case(row['source_text'], json.dumps(actual), row['label'], complete=True)
    assert 'SCHEMA_INVALID' in result['diagnostic']['tags']
    assert result['diagnostic']['slot_differences'] == []


def test_incomplete_but_parseable_generation_is_not_called_a_wrong_action_sequence():
    row = approved()
    result = diagnose_case(row['source_text'], json.dumps(row['label']), row['label'], complete=False)
    assert result['diagnostic']['tags'] == ['INCOMPLETE_GENERATION']
