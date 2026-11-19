import copy
import hashlib
import json

import pytest

from experiments.semantic_sft.data import canonical_hash
from experiments.semantic_sft.semantic_metrics import score_text
from experiments.semantic_sft.tests.test_preparation import approved
from experiments.semantic_sft.weighting import group_action_weights, load_train_replay_audit, train_replay_weights


def inputs():
    rows = [approved('UNIT_' + name) for name in ('normal', 'failed', 'retained', 'span')]
    rows[3]['label']['steps'][0]['condition'] = '标记'
    cases = []
    for row in rows[1:]:
        observed = copy.deepcopy(row['label'])
        if row['sample_id'].endswith('span'):
            observed['steps'][0]['condition'] = '到标记'
        else:
            observed['requires_confirmation'] = True
        raw = json.dumps(observed)
        cases.append(dict(sample_id=row['sample_id'], source_text=row['source_text'], source_sha256=row['source_sha256'],
            approved_label=row['label'], approved_label_sha256=canonical_hash(row['label']), model_raw=raw,
            score=score_text(row['source_text'], raw, row['label'], complete=True), split='train',
            reference_regressions=['semantic_exact'] if row['sample_id'].endswith('retained') else []))
    return rows, group_action_weights(rows), cases


def test_replay_boost_is_bounded_normalized_and_keeps_all_examples_and_originals():
    rows, base, cases = inputs()
    before = copy.deepcopy((rows, base, cases))
    result = train_replay_weights(rows, base, cases)
    assert before == (rows, base, cases)
    assert [s['sample_id'] for s in result['samples']] == [r['sample_id'] for r in rows]
    assert [s['replay_multiplier'] for s in result['samples']] == [1, 1.5, 2, 1]
    assert sum(s['weight'] for s in result['samples']) == pytest.approx(len(rows))
    assert result['train_replay_policy']['boosted_rows'] == 2
    assert result['train_replay_policy']['deferred_span_only_rows'] == 1
    assert group_action_weights(rows) == base


@pytest.mark.parametrize('failure', ['dev', 'unknown_id', 'source', 'label', 'score', 'duplicate', 'base_order', 'bad_weight'])
def test_unverified_or_non_train_material_cannot_change_weights(failure):
    rows, base, cases = inputs()
    if failure == 'dev':
        cases[0]['split'] = 'val'
    elif failure == 'unknown_id':
        cases[0]['sample_id'] = 'UNIT_DEV_UNKNOWN'
    elif failure == 'source':
        cases[0]['source_text'] += 'changed'
    elif failure == 'label':
        cases[0]['approved_label_sha256'] = '0' * 64
    elif failure == 'score':
        cases[0]['score']['checks']['semantic_exact'] = True
    elif failure == 'duplicate':
        cases.append(copy.deepcopy(cases[0]))
    elif failure == 'base_order':
        base['samples'].reverse()
    else:
        base['samples'][0]['weight'] = float('nan')
    with pytest.raises(ValueError):
        train_replay_weights(rows, base, cases)


def test_replay_loader_rejects_wrong_dataset_and_modified_artifact(tmp_path):
    _, _, cases = inputs()
    (tmp_path / 'train_hard_cases.jsonl').write_text('\n'.join(json.dumps(c) for c in cases), encoding='utf-8')
    report = dict(scope='TRAIN_ONLY_HARD_CASE_AUDIT_NOT_NEW_DATA_OR_WEIGHT_UPDATE',
        dataset_manifest_sha256='a'*64, candidate_manifest_sha256='b'*64, prediction_sha256='c'*64,
        label_changes=0, dev_or_test_rows_imported=0, model_predictions_used_as_labels=False, hard_cases=len(cases),
        reference_train_rows=1, reference_provenance={'manifest_sha256':'d'*64},
        reference_retention_regressions={'raw_action_order_exact':[], 'semantic_exact':['UNIT_retained']})
    (tmp_path / 'report.json').write_text(json.dumps(report))
    manifest = dict(artifacts={name: hashlib.sha256((tmp_path/name).read_bytes()).hexdigest()
        for name in ('report.json','train_hard_cases.jsonl')})
    (tmp_path / 'artifact_manifest.json').write_text(json.dumps(manifest))
    loaded, provenance = load_train_replay_audit(tmp_path, expected_dataset_manifest_sha256='a'*64)
    assert len(loaded) == 3 and provenance['source_candidate_manifest_sha256'] == 'b'*64
    with pytest.raises(ValueError):
        load_train_replay_audit(tmp_path, expected_dataset_manifest_sha256='wrong')
    (tmp_path / 'train_hard_cases.jsonl').write_text('changed')
    with pytest.raises(ValueError):
        load_train_replay_audit(tmp_path, expected_dataset_manifest_sha256='a'*64)
