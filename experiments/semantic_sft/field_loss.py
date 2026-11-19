"""Assistant-only semantic value weighting, never an inference action rule."""
import json

POLICY = dict(version='semantic_values_v1', action=4.0, condition=3.0,
              direction=2.0, prohibited_actions=3.0, other_or_null=1.0)
ACTION_ONLY_POLICY = dict(version='action_only_v1', action=4.0, condition=1.0,
                          direction=1.0, prohibited_actions=1.0, other_or_null=1.0)
STEP_BOUNDARY_POLICY = ACTION_ONLY_POLICY | dict(version='step_boundary_v1', step_boundary=3.0)
CONDITION_POLICY = ACTION_ONLY_POLICY | dict(version='condition_both_values_v1', condition=3.0, condition_null=3.0)


def value_spans(label, *, policy=POLICY):
    """Serialize canonical JSON and locate semantic values structurally, not by keyword search."""
    chunks, spans = [], []
    position = 0
    def emit(text):
        nonlocal position
        chunks.append(text)
        position += len(text)
    def visit(value, path):
        start = position
        if isinstance(value, dict):
            emit('{')
            for i, key in enumerate(sorted(value)):
                if i:
                    emit(',')
                emit(json.dumps(key, ensure_ascii=False) + ':')
                visit(value[key], path + (key,))
            emit('}')
        elif isinstance(value, list):
            emit('[')
            boundary = policy.get('step_boundary') if path == ('steps',) else None
            if boundary:
                spans.append((start, position, boundary))
            for i, item in enumerate(value):
                delimiter = position
                if i:
                    emit(',')
                if boundary:
                    spans.append((delimiter, position + 1, boundary))
                visit(item, path + (i,))
                if boundary:
                    spans.append((position - 1, position, boundary))
            emit(']')
            if boundary:
                spans.append((position - 1, position, boundary))
        else:
            emit(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')))
        field = path[-1] if path else None
        if ((len(path) == 3 and path[0] == 'steps' and field in ('action', 'condition', 'direction')
             and value is not None) or (path == ('prohibited_actions',) and value)):
            spans.append((start, position, policy[field]))
        if len(path) == 3 and path[0] == 'steps' and field == 'condition' and value is None and policy.get('condition_null'):
            spans.append((start, position, policy['condition_null']))
    visit(label, ())
    return ''.join(chunks), spans


def semantic_token_weights(tokenizer, messages, token_record, *, policy=POLICY):
    if not getattr(tokenizer, 'is_fast', False):
        raise ValueError('semantic field loss requires verified fast-tokenizer offsets')
    content = messages[-1]['content']
    canonical, spans = value_spans(json.loads(content), policy=policy)
    if content != canonical:
        raise ValueError('semantic field loss requires exact canonical assistant JSON')
    prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    full = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False, enable_thinking=False)
    if not full.startswith(prefix + content):
        raise ValueError('cannot prove assistant character boundary')
    encoded = tokenizer(full, add_special_tokens=False, return_offsets_mapping=True)
    if encoded['input_ids'] != token_record['input_ids'] or len(encoded['offset_mapping']) != len(token_record['labels']):
        raise ValueError('offset mapping differs from audited training tokens')
    weights = []
    for (left, right), target in zip(encoded['offset_mapping'], token_record['labels']):
        if target == -100:
            weights.append(0.0)
        else:
            # Boundary tokens overlapping a value receive its weight; EOS and other syntax stay at 1.
            weights.append(max([1.0] + [w for a, b, w in spans if left < len(prefix) + b and right > len(prefix) + a]))
    return weights


def assistant_weighted_ce(logits, labels, weights):
    """logits cover assistant_tokens+1 trailing positions; final unused logit is excluded."""
    import torch
    import torch.nn.functional as F
    if (logits.ndim != 3 or logits.shape[:2] != (1, len(labels) + 1) or len(labels) != len(weights)
            or not labels or any(v < 0 for v in labels) or any(v <= 0 for v in weights)):
        raise ValueError('invalid supervised assistant alignment or weights')
    targets = torch.tensor([labels], device=logits.device)
    coefficients = torch.tensor(weights, device=logits.device, dtype=torch.float32)
    losses = F.cross_entropy(logits[:, :-1].float().transpose(1, 2), targets, reduction='none')[0]
    return (losses * coefficients).sum() / coefficients.sum()
