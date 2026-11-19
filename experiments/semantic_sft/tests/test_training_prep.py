import json
import pytest

from experiments.semantic_sft.build_exclusion_registry import registry
from experiments.semantic_sft.data import text_hash, protected_hashes
from experiments.semantic_sft.prepare import external_registry
from experiments.semantic_sft.synthetic_smoke import synthetic_messages


def test_registry_deduplicates_normalized_text_and_does_not_publish_answers(tmp_path):
    result=registry([{'source_text':'STOP A','label':'PRIVATE'}, {'source_text':'stopa'}], 'UNIT_ONLY_B2', 'UNIT_ONLY_FROZEN',
                    role='FROZEN_TEST',source_revision='a'*40,frozen=True)
    assert result['text_sha256']==[text_hash('STOP A')]
    assert result['input_rows']==2 and result['unique_texts']==1
    assert 'PRIVATE' not in json.dumps(result) and 'STOP A' not in json.dumps(result)
    path=tmp_path/'hashes.json'
    path.write_text(json.dumps(result))
    assert external_registry(path)=={text_hash('stopa')}


@pytest.mark.parametrize('rows,publisher,version', [([], 'B2','v1'), ([{'source_text':' '}],'B2','v1'),
    ([{'other':'wrong field'}],'B2','v1'), ([{'source_text':'UNIT'}],'','v1')])
def test_registry_rejects_empty_or_incomplete_inputs(rows,publisher,version):
    with pytest.raises(ValueError):registry(rows,publisher,version,role='FROZEN_TEST',source_revision='a'*40,frozen=True)


def test_validation_registry_cannot_satisfy_test_gate(tmp_path):
    from experiments.semantic_sft.data import audit_rows
    from experiments.semantic_sft.tests.test_preparation import approved
    payload=registry([{'source_text':'UNIT_HOLDOUT'}], 'UNIT_B1', 'UNIT_IV',
                     role='INDEPENDENT_VALIDATION',source_revision='b'*40,frozen=True)
    path=tmp_path/'iv.json'
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='Validation cannot substitute'):
        external_registry(path)
    hashes=external_registry(path,role='INDEPENDENT_VALIDATION')
    report=audit_rows([approved()],supplemental_protected=hashes)
    assert 'EXTERNAL_FROZEN_TEST_EXCLUSION_REGISTRY_MISSING' in report['global_errors']


def test_smoke_uses_only_explicit_synthetic_protocol_units():
    for value in (17,23,31):
        messages=synthetic_messages(value)
        assert messages[1]['content'].startswith('SYNTHETIC_PIPELINE_UNIT_')
        assert text_hash(messages[1]['content']) not in protected_hashes()
        assert json.loads(messages[-1]['content'])=={'unit_value':value}


def test_protected_group_is_rejected_even_when_text_does_not_match(tmp_path):
    from experiments.semantic_sft.data import audit_rows
    from experiments.semantic_sft.prepare import registry_groups
    from experiments.semantic_sft.tests.test_preparation import approved
    row=approved()
    result=registry([{'source_text':'DIFFERENT_UNIT_TEXT','group_id':row['group_id']}], 'UNIT', 'UNIT_TEST',
                    role='FROZEN_TEST',source_revision='a'*40,frozen=True)
    path=tmp_path/'groups.json'
    path.write_text(json.dumps(result))
    report=audit_rows([row],external_protected=external_registry(path),protected_groups=registry_groups(path))
    assert report['issue_counts']['PROTECTED_EVALUATION_GROUP']==1
    assert not report['data_ready_for_tokenization']
