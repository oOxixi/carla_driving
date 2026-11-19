import json

import pytest

from experiments.semantic_sft.field_loss import ACTION_ONLY_POLICY, POLICY, assistant_weighted_ce, semantic_token_weights, value_spans
from experiments.semantic_sft.field_loss import CONDITION_POLICY, STEP_BOUNDARY_POLICY


def label():
    return dict(steps=[dict(action='TURN_RIGHT', condition='道闸显示"放行"后', direction='RIGHT',
                           evidence='不要搜索字符串action或condition', target_text=None, speed_kph=None, gap_m=None)],
                prohibited_actions={'CHANGE_LANE_RIGHT': True}, requires_confirmation=False)


def test_structural_spans_match_canonical_json_and_do_not_weight_evidence_or_nulls():
    payload = label()
    text, spans = value_spans(payload)
    assert text == json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    assert {json.loads(text[a:b]) if not text[a:b].startswith('{') else 'PROHIBITION' for a, b, w in spans} == {
        'TURN_RIGHT', '道闸显示"放行"后', 'RIGHT', 'PROHIBITION'}
    payload['steps'][0]['condition'] = None
    payload['steps'][0]['direction'] = None
    payload['prohibited_actions'] = {}
    assert len(value_spans(payload)[1]) == 1


class OffsetTokenizer:
    is_fast = True
    def apply_chat_template(self, messages, **kwargs):
        return 'UNIT_PROMPT:' + (messages[-1]['content'] + '<EOS>' if messages[-1]['role'] == 'assistant' else '')
    def __call__(self, text, **kwargs):
        return dict(input_ids=list(range(len(text))), offset_mapping=[(i, i+1) for i in range(len(text))])


def test_offsets_never_weight_prompt_and_keep_eos_supervised():
    tokenizer = OffsetTokenizer()
    content, spans = value_spans(label())
    messages = [dict(role='user', content='UNIT_ONLY'), dict(role='assistant', content=content)]
    full = tokenizer.apply_chat_template(messages)
    prefix = len('UNIT_PROMPT:')
    record = dict(input_ids=tokenizer(full)['input_ids'], labels=[-100]*prefix + list(range(prefix, len(full))))
    weights = semantic_token_weights(tokenizer, messages, record)
    assert weights[:prefix] == [0]*prefix
    assert weights[-5:] == [1]*5
    for a, b, w in spans:
        assert weights[prefix+a:prefix+b] == [w]*(b-a)
    record['input_ids'][0] = -999
    with pytest.raises(ValueError, match='audited training tokens'):
        semantic_token_weights(tokenizer, messages, record)


def test_action_only_changes_no_other_semantic_values_or_nulls_and_preserves_legacy():
    tokenizer = OffsetTokenizer()
    content, spans = value_spans(label(), policy=ACTION_ONLY_POLICY)
    messages = [dict(role='user', content='UNIT_ONLY'), dict(role='assistant', content=content)]
    full = tokenizer.apply_chat_template(messages)
    prefix = len('UNIT_PROMPT:')
    record = dict(input_ids=tokenizer(full)['input_ids'], labels=[-100]*prefix + list(range(prefix, len(full))))
    weights = semantic_token_weights(tokenizer, messages, record, policy=ACTION_ONLY_POLICY)
    expected = [0]*prefix + [1]*(len(full)-prefix)
    action_spans = [(a, b) for a, b, w in spans if w > 1]
    assert len(action_spans) == 1
    for a, b in action_spans:
        expected[prefix+a:prefix+b] = [4]*(b-a)
    assert weights == expected
    assert value_spans(label()) == value_spans(label(), policy=POLICY)


def test_weighted_ce_alignment_normalization_and_backward():
    torch = pytest.importorskip('torch')
    torch.manual_seed(7)
    logits = torch.randn(1, 4, 5, requires_grad=True)
    labels = [2, 3, 4]
    plain = torch.nn.functional.cross_entropy(logits[:, :-1].reshape(-1, 5), torch.tensor(labels))
    assert torch.allclose(assistant_weighted_ce(logits, labels, [1, 1, 1]), plain)
    loss = assistant_weighted_ce(logits, labels, [4, 3, 1])
    loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(logits.grad).all()
    assert logits.grad[:, -1].abs().sum() == 0
    assert logits.grad[:, :-1].abs().sum() > 0
    with pytest.raises(ValueError):
        assistant_weighted_ce(logits, [-100, 3, 4], [4, 3, 1])


@pytest.mark.parametrize('policy', [STEP_BOUNDARY_POLICY, CONDITION_POLICY])
def test_new_ablations_change_only_their_declared_character_spans(policy):
    payload = label()
    payload['steps'].append(dict(payload['steps'][0], condition=None))
    old_text, old_spans = value_spans(payload, policy=ACTION_ONLY_POLICY)
    text, spans = value_spans(payload, policy=policy)
    assert text == old_text
    def weights(ss):
        return [max([1] + [w for a, b, w in ss if a <= i < b]) for i in range(len(text))]
    before, after = weights(old_spans), weights(spans)
    assert all(a >= b for a, b in zip(after, before))
    changed = [i for i, (a, b) in enumerate(zip(after, before)) if a != b]
    if policy == STEP_BOUNDARY_POLICY:
        assert ''.join(text[i] for i in changed) == '[{},{' + '}]'
        assert all(after[i] == 3 for i in changed)
    else:
        assert ''.join(text[i] for i in changed) == json.dumps(payload['steps'][0]['condition'], ensure_ascii=False) + 'null'
        assert all(after[i] == 3 for i in changed)
    tokenizer = OffsetTokenizer()
    messages = [dict(role='user', content='UNIT_ONLY'), dict(role='assistant', content=text)]
    full = tokenizer.apply_chat_template(messages)
    prefix = len('UNIT_PROMPT:')
    record = dict(input_ids=tokenizer(full)['input_ids'], labels=[-100]*prefix + list(range(prefix, len(full))))
    actual = semantic_token_weights(tokenizer, messages, record, policy=policy)
    assert actual == [0]*prefix + after + [1]*5
