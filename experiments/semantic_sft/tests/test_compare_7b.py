import copy
import json
import pytest
from experiments.semantic_sft.compare_7b import encode_prompt, inference_messages, verify_reference
from experiments.semantic_sft.data import chat_record
from experiments.semantic_sft.semantic_metrics import score_text
from experiments.semantic_sft.tests.test_preparation import approved


def fixture():
    row=approved()
    record=chat_record(row)
    raw=json.dumps(row['label'])
    generated=dict(sample_id=row['sample_id'],raw=raw,score=score_text(row['source_text'],raw,row['label'],complete=True))
    return record,generated


def test_comparison_never_passes_gold_to_inference():
    record,_=fixture()
    before=copy.deepcopy(record)
    assert [m['role'] for m in inference_messages(record)]==['system','user']
    assert record==before


def test_prompt_tokens_use_flat_ids_not_version_dependent_chat_template_encoding():
    record,_=fixture()
    class Tokenizer:
        def apply_chat_template(self,messages,**kwargs):
            assert [m['role'] for m in messages]==['system','user']
            assert kwargs['tokenize'] is False
            return 'UNIT_ONLY_PROMPT'
        def __call__(self,text,**kwargs):
            assert text=='UNIT_ONLY_PROMPT' and kwargs['add_special_tokens'] is False
            return {'input_ids':[1,2,3]}
    assert encode_prompt(Tokenizer(),record)==[1,2,3]


@pytest.mark.parametrize('change',['none','duplicate','score','raw','id'])
def test_cached_comparison_requires_exact_paired_ids_and_rescored_raw(change):
    record,generated=fixture()
    rows=[generated]
    if change=='duplicate': rows*=2
    elif change=='score': generated['score']['checks']['semantic_exact']=False
    elif change=='raw': generated['raw']='{}'
    elif change=='id': generated['sample_id']='WRONG'
    if change=='none': assert verify_reference(rows,[record])==rows
    else:
        with pytest.raises(ValueError): verify_reference(rows,[record])
