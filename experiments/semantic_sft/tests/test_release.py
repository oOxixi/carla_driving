import copy
import hashlib
import json

import pytest

from experiments.semantic_sft.data import PLAN
from experiments.semantic_sft.release import assign_approved_groups
from experiments.semantic_sft.tests.test_preparation import approved


def inputs():
    # Fabricated UNIT_ONLY records; no real review or artifact is created.
    previous = [approved(f'UNIT_OLD_{split}_{i}', split, family)
                for split in ('train', 'val')
                for i, family in enumerate(PLAN['data_smoke_thresholds']['required_families'])]
    batch = [approved(f'UNIT_NEW_{split}_{i}', 'UNASSIGNED', family)
             for split in ('train', 'val')
             for i, family in enumerate(PLAN['data_smoke_thresholds']['required_families'])]
    planned = {r['group_id']: ('train' if '_train_' in r['sample_id'] else 'val') for r in batch}
    return previous, batch, planned


def options(monkeypatch):
    monkeypatch.setitem(PLAN['data_smoke_thresholds'], 'minimum_train', 1)
    monkeypatch.setitem(PLAN['data_smoke_thresholds'], 'minimum_val', 1)
    return dict(external_protected={'0'*64}, supplemental_protected={'1'*64}, protected_groups=set())


def test_freeze_preserves_old_rows_reviews_and_declared_groups(monkeypatch):
    previous, batch, planned = inputs()
    before = copy.deepcopy((previous, batch, planned))
    combined, report = assign_approved_groups(previous, batch, planned, **options(monkeypatch))
    assert (previous, batch, planned) == before
    assert combined[:len(previous)] == previous
    assert all(r['split'] == planned[r['group_id']] for r in combined[len(previous):])
    assert report['data_ready_for_tokenization'] and not report['ready_for_training']


@pytest.mark.parametrize('change', ['unapproved', 'stale_review', 'extra_group', 'already_split', 'cross_split', 'protected'])
def test_invalid_release_is_not_silently_filtered_or_approved(change, monkeypatch):
    previous, batch, planned = inputs()
    kwargs = options(monkeypatch)
    if change == 'unapproved':
        batch[0]['annotation_status'] = 'DRAFT'
    elif change == 'stale_review':
        batch[0]['reviews'][0]['label_sha256'] = '0'*64
    elif change == 'extra_group':
        planned['UNUSED'] = 'train'
    elif change == 'already_split':
        batch[0]['split'] = 'val'
    elif change == 'cross_split':
        del planned[batch[0]['group_id']]
        batch[0]['group_id'] = previous[0]['group_id']
        planned[batch[0]['group_id']] = 'val'
    else:
        kwargs['protected_groups'] = {batch[0]['group_id']}
    with pytest.raises(ValueError):
        assign_approved_groups(previous, batch, planned, **kwargs)


@pytest.mark.parametrize('bad_receipt', [False, True])
def test_cli_binds_receipt_preserves_quarantine_and_never_creates_a_gate(tmp_path, monkeypatch, bad_receipt):
    from experiments.semantic_sft import release
    from experiments.semantic_sft.tests.test_review import packets
    options(monkeypatch)
    previous, batch, planned = inputs()
    quarantine = [r for r in packets() if r['proposal']['contract_gap']]
    receipt = {'scope': 'HUMAN_REVIEW_RECORD_NOT_TRAINING_GATE', 'approval_quote': 'UNIT_ONLY_NOT_REAL_APPROVAL',
               'accepted_rows': [{'sample_id': r['sample_id'], 'source_sha256': r['source_sha256'],
                                  'label_sha256': r['reviews'][-1]['label_sha256']} for r in batch]}
    if bad_receipt:
        receipt['accepted_rows'][0]['label_sha256'] = '0'*64
    paths = {name: tmp_path / (name + '.jsonl') for name in ['previous', 'approved-batch', 'quarantine']}
    for name, records in [('previous', previous), ('approved-batch', batch), ('quarantine', quarantine)]:
        release.write_rows(paths[name], records)
    metadata = {'planned-groups': planned, 'approval-receipt': receipt}
    for name, role in [('test-registry', 'FROZEN_TEST'), ('supplemental-registry', 'INDEPENDENT_VALIDATION')]:
        metadata[name] = dict(registry_schema_version=2, protected_set_role=role, frozen=True,
            test_version='UNIT_ONLY', source_revision='0'*40, publisher='UNIT_ONLY',
            normalization='nfkc_casefold_remove_whitespace_v1', text_sha256=['0'*64], group_ids=[])
    for name, content in metadata.items():
        paths[name] = tmp_path / (name + '.json')
        paths[name].write_text(json.dumps(content), encoding='utf-8')
    target = tmp_path / 'release'
    arguments = ['release', '--dataset-version', 'UNIT_ONLY', '--output-dir', str(target)]
    for name, path in paths.items():
        arguments += ['--' + name, str(path)]
    monkeypatch.setattr(release, 'output_directory', lambda path: path)
    monkeypatch.setattr('sys.argv', arguments)
    if bad_receipt:
        with pytest.raises(ValueError, match='receipt'):
            release.main()
        assert not target.exists()
        return
    release.main()
    manifest = json.loads((target/'manifest.json').read_text())
    assert manifest['split_frozen'] and not manifest['ready_for_training']
    assert not manifest['training_started'] and not manifest['formal_performance_gate_passed']
    assert (target/'quarantine.jsonl').read_bytes() == paths['quarantine'].read_bytes()
    assert all(hashlib.sha256((target/name).read_bytes()).hexdigest() == digest
               for name, digest in manifest['artifact_sha256'].items())
    assert b'\r\n' not in (target/'train.jsonl').read_bytes()
