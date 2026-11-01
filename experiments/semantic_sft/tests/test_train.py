import json
from pathlib import Path

import pytest

from experiments.semantic_sft.data import PLAN, canonical_hash, chat_record
from experiments.semantic_sft.release import write_rows
from experiments.semantic_sft.train import artifact_fingerprint, epoch_batches, select_idle_gpu, sha, validate_config, verify_release
from experiments.semantic_sft.tests.test_preparation import approved


def test_epoch_accumulation_visits_each_training_row_once_including_tail():
    batches = epoch_batches(206, 4, 20261101, 0)
    assert len(batches) == 52 and len(batches[-1]) == 2
    assert sorted(i for batch in batches for i in batch) == list(range(206))
    assert batches == epoch_batches(206, 4, 20261101, 0)
    assert batches != epoch_batches(206, 4, 20261101, 1)


def test_model_fingerprint_matches_b1_recipe_and_ignores_only_local_metadata(tmp_path):
    (tmp_path / 'config.json').write_bytes(b'UNIT_MODEL')
    (tmp_path / '.model_revision').write_bytes(b'UNIT_REVISION')
    cache = tmp_path / '.cache'
    cache.mkdir(); (cache / 'temp').write_bytes(b'IGNORED_CACHE')
    result = artifact_fingerprint(tmp_path)
    expected = [{'path': 'config.json', 'size_bytes': 10, 'sha256': sha(tmp_path / 'config.json')}]
    assert result == {'files': expected, 'artifact_sha256': canonical_hash(expected)}
    (tmp_path / 'config.json').write_bytes(b'DIFFERENT')
    assert artifact_fingerprint(tmp_path)['artifact_sha256'] != result['artifact_sha256']


@pytest.mark.parametrize('index', [0, -1, 8, True])
def test_training_can_never_select_production_gpu(index):
    with pytest.raises(ValueError):
        select_idle_gpu(index)


@pytest.mark.parametrize('used,processes,reject', [('4', '', False), ('17000', '', True),
    ('4', 'GPU-UNIT, 1234\n', True), ('4', 'GPU-OTHER, 2345\n', False)])
def test_gpu_is_rechecked_without_killing_any_process(monkeypatch, used, processes, reject):
    def command(args, **kwargs):
        assert args[0] == 'nvidia-smi'
        return f'GPU-UNIT, {used}, 24576' if '-i' in args else processes
    monkeypatch.setattr('experiments.semantic_sft.train.subprocess.check_output', command)
    if reject:
        with pytest.raises(ValueError, match='occupied'):
            select_idle_gpu(6)
    else:
        assert select_idle_gpu(6) == 'GPU-UNIT'


@pytest.mark.parametrize('key,value', [('epochs', 0), ('learning_rate', float('nan')),
    ('max_grad_norm', 0), ('gradient_accumulation', True), ('unknown', 1)])
def test_invalid_training_config_is_rejected(key, value):
    config = json.loads((Path(__file__).parents[1] / 'train_config.json').read_text())
    validate_config(config)
    config[key] = value
    with pytest.raises(ValueError):
        validate_config(config)


def frozen_unit_release(tmp_path, monkeypatch):
    # UNIT_ONLY fabricated review records; never actual business approvals or training material.
    monkeypatch.setitem(PLAN['data_smoke_thresholds'], 'minimum_train', 1)
    monkeypatch.setitem(PLAN['data_smoke_thresholds'], 'minimum_val', 1)
    rows = [approved(f'UNIT_{split}_{i}', split, family) for split in ('train', 'val')
            for i, family in enumerate(PLAN['data_smoke_thresholds']['required_families'])]
    write_rows(tmp_path / 'reviewed_rows.jsonl', rows)
    for split in ('train', 'val'):
        write_rows(tmp_path / (split + '.jsonl'), [chat_record(r) for r in rows if r['split'] == split])
    for name in ('report.json', 'approval_receipt.json'):
        (tmp_path / name).write_text('{}')
    (tmp_path / 'quarantine.jsonl').write_text('UNIT_ONLY_NOT_USED')
    for filename, role in [('test_exclusion_registry.json', 'FROZEN_TEST'),
                           ('supplemental_exclusion_registry.json', 'INDEPENDENT_VALIDATION')]:
        (tmp_path / filename).write_text(json.dumps(dict(registry_schema_version=2, protected_set_role=role,
            frozen=True, test_version='UNIT_ONLY', source_revision='0'*40, publisher='UNIT_ONLY',
            normalization='nfkc_casefold_remove_whitespace_v1', text_sha256=['0'*64])))
    manifest = dict(split_frozen=True, dataset_version='UNIT_ONLY', base_model=PLAN['base_model'],
        base_revision=PLAN['base_revision'], artifact_sha256={p.name: sha(p) for p in tmp_path.iterdir()})
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest))
    audit = dict(input_sha256=sha(tmp_path / 'reviewed_rows.jsonl'), all_checked_passed=True,
        checked_rows=len(rows), skipped_sample_ids=[], checks=[dict(sample_id=r['sample_id'], status='PASS',
            prompt_loss_masked=True, source_sha256=r['source_sha256'], label_sha256=canonical_hash(r['label'])) for r in rows])
    token_path = tmp_path / 'token_audit.json'
    token_path.write_text(json.dumps(audit))
    return sha(tmp_path / 'manifest.json'), token_path


@pytest.mark.parametrize('change', ['none', 'manifest', 'export', 'token_binding', 'token_mask', 'missing_check'])
def test_training_rechecks_frozen_files_exports_and_all_token_bindings(tmp_path, monkeypatch, change):
    digest, token_path = frozen_unit_release(tmp_path, monkeypatch)
    if change == 'manifest':
        digest = '0'*64
    elif change == 'export':
        (tmp_path / 'train.jsonl').write_text('{}\n')
    elif change in ('token_binding', 'token_mask', 'missing_check'):
        audit = json.loads(token_path.read_text())
        if change == 'token_binding':
            audit['checks'][0]['label_sha256'] = '0'*64
        elif change == 'token_mask':
            audit['checks'][0]['prompt_loss_masked'] = False
        else:
            audit['checks'].pop()
        token_path.write_text(json.dumps(audit))
    if change != 'none':
        with pytest.raises(ValueError):
            verify_release(tmp_path, digest, token_path)
    else:
        exports, version, report = verify_release(tmp_path, digest, token_path)
        assert len(exports['train']) == len(exports['val']) == 6
        assert version == 'UNIT_ONLY' and report['data_ready_for_tokenization']
