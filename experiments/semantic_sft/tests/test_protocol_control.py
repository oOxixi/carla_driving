import copy
import json

import pytest

from qwen_service.task_understanding import TASK_SCHEMA
from experiments.semantic_sft.protocol_control import control_schema, with_condition_guidance


def test_condition_addendum_changes_only_system_text():
    record={'messages':[{'role':'system','content':'BASE'}, {'role':'user','content':'原始指令'},
                        {'role':'assistant','content':'UNIT_ONLY_GOLD'}]}
    candidate=with_condition_guidance(record)
    assert candidate['messages'][0]['content'].startswith('BASE\n')
    assert candidate['messages'][1:]==record['messages'][1:]
    assert record['messages'][0]['content']=='BASE'


def test_grammar_is_only_original_contract_not_gold_or_scenario_choices():
    schema=control_schema()
    expected=copy.deepcopy(TASK_SCHEMA)
    expected['required'].sort()
    expected['properties']['steps']['items']['required'].sort()
    assert schema==expected
    assert len(schema['properties']['steps']['items']['properties']['action']['enum'])==14
    assert schema['properties']['steps']['minItems']==1
    assert schema['properties']['steps']['maxItems']==8
    assert 'enum' not in schema['properties']['steps']['items']['properties']['target_text']
    schema['properties']['steps']['maxItems']=1
    assert TASK_SCHEMA['properties']['steps']['maxItems']==8


def test_real_compiler_accepts_canonical_object_and_rejects_missing_or_duplicate_fields():
    xgr=pytest.importorskip('xgrammar')
    from experiments.semantic_sft.tests.test_preparation import approved
    info=xgr.TokenizerInfo([chr(i) for i in range(128)]+['<eos>'],xgr.VocabType.RAW,stop_token_ids=[128])
    grammar=xgr.GrammarCompiler(info).compile_json_schema(control_schema(),any_order=False)
    good=json.dumps(approved()['label'],sort_keys=True,separators=(',',':'),ensure_ascii=False)
    assert xgr.GrammarMatcher(grammar).accept_string(good)
    missing=good.replace('"action":"STOP",','')
    duplicate=good.replace('"target_text":null','"target_text":null,"target_text":null')
    assert not xgr.GrammarMatcher(grammar).accept_string(missing)
    assert not xgr.GrammarMatcher(grammar).accept_string(duplicate)
