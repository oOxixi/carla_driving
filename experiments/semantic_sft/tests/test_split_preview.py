import copy
import json

import pytest

from experiments.semantic_sft.data import HERE, load_jsonl, text_hash
from experiments.semantic_sft.proposals import draft_packets
from experiments.semantic_sft.review import first_review
from experiments.semantic_sft.split_preview import split_preview
from experiments.semantic_sft.tests.test_review import reviewed


def unit_rows():
    # UNIT_ONLY reviewer metadata; never actual approvals or training material.
    old, _ = reviewed()
    folder = HERE / 'batches/negative_v1'
    draft = draft_packets(load_jsonl(folder / 'seeds.jsonl'), load_jsonl(folder / 'draft_labels.jsonl'))
    new, _ = first_review(draft, reviewer_id='UNIT_ONLY_A', reviewed_at='2026-11-01T01:00:00+08:00',
                         approval_reference='UNIT_ONLY', approval_quote='UNIT_ONLY')
    rows = old + new
    for row in rows:
        if row['label'] is not None:
            second = dict(row['reviews'][0], reviewer_id='UNIT_ONLY_B')
            row['reviews'].append(second)
            row['annotation_status'] = 'APPROVED'
    return rows


def test_split_is_deterministic_label_blind_and_preserves_reviews_and_quarantine():
    rows = unit_rows()
    before = copy.deepcopy(rows)
    candidate, quarantine, report = split_preview(rows)
    assert rows == before
    assert (candidate, quarantine, report) == split_preview(list(reversed(rows)))
    assert len(candidate) == 29 and len(quarantine) == 3
    lookup = {r['sample_id']:r for r in rows}
    assert all(dict(r, split='UNASSIGNED') == lookup[r['sample_id']] for r in candidate)
    assert all(r == lookup[r['sample_id']] for r in quarantine)
    train = {r['group_id'] for r in candidate if r['split']=='train'}
    val = {r['group_id'] for r in candidate if r['split']=='val'}
    assert not train & val
    assert len(val) == 6
    assert len(report['family_counts']['train']) == len(report['family_counts']['val']) == 6
    assert not report['split_frozen'] and not report['ready_for_training']
    assert 'EXTERNAL_FROZEN_TEST_EXCLUSION_REGISTRY_MISSING' in report['candidate_audit']['global_errors']


@pytest.mark.parametrize('change', ['stale_review', 'already_split', 'draft', 'duplicate', 'protected', 'mixed_family'])
def test_invalid_or_unreviewed_data_is_not_silently_skipped(change):
    rows = unit_rows()
    protected = None
    if change == 'stale_review':
        rows[0]['reviews'][1]['label_sha256'] = '0'*64
    elif change == 'already_split':
        rows[0]['split'] = 'train'
    elif change == 'draft':
        rows[0]['annotation_status'] = 'DRAFT'
    elif change == 'duplicate':
        rows.append(copy.deepcopy(rows[0]))
    elif change == 'protected':
        protected = {text_hash(rows[0]['source_text'])}
    else:
        rows[2]['group_id'] = rows[4]['group_id']
    with pytest.raises(ValueError):
        split_preview(rows, external_protected=protected)


def test_cli_writes_preview_not_training_files_and_export_stays_blocked(tmp_path, monkeypatch):
    from experiments.semantic_sft import prepare
    source = tmp_path/'unit.jsonl'
    source.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in unit_rows()), encoding='utf-8')
    output = tmp_path/'preview'
    monkeypatch.setattr(prepare, 'output_directory', lambda path:path)
    monkeypatch.setattr('sys.argv', ['prepare','split-preview','--input',str(source),'--output-dir',str(output)])
    assert prepare.main() == 0
    assert len(load_jsonl(output/'split_preview.jsonl')) == 29
    assert len(load_jsonl(output/'quarantine.jsonl')) == 3
    assert b'\r\n' not in (output/'split_preview.jsonl').read_bytes()
    assert not (output/'train.jsonl').exists() and not (output/'val.jsonl').exists()
    export = tmp_path/'export'
    monkeypatch.setattr('sys.argv', ['prepare','export','--input',str(output/'split_preview.jsonl'),'--output-dir',str(export)])
    assert prepare.main() == 1
    assert not (export/'train.jsonl').exists() and not (export/'val.jsonl').exists()
