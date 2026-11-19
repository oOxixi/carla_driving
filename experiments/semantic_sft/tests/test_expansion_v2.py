from collections import Counter
from experiments.semantic_sft.batches.expansion_v2.build import build_batch,review_index
from experiments.semantic_sft.data import audit_rows,text_hash


def test_expansion_is_draft_only_and_does_not_hide_wording_variants_as_new_groups():
    rows,cohorts=build_batch()
    assert len(rows)==216 and len({r['sample_id'] for r in rows})==216
    assert len({text_hash(r['source_text']) for r in rows})==216
    assert len(cohorts)==48
    assert Counter(cohorts[r['group_id']] for r in rows)=={'train':180,'val':36}
    assert cohorts['unspecified_vehicle_reference_01']=='train'
    assert cohorts['contradictory_speed_02']=='val'
    assert all(r['label'] is None and not r['reviews'] and r['split']=='UNASSIGNED' for r in rows)
    assert audit_rows(rows)['issue_counts']['MISSING_LABEL']==216
    index=review_index(rows,cohorts)
    assert index.count('\n## ')==48
    assert all(r['sample_id'] in index for r in rows)
    for cohort in ['train','val']:
        actions={s['action'] for r in rows if cohorts[r['group_id']]==cohort for s in r['proposal']['label']['steps']}
        assert {'TURN_LEFT','TURN_RIGHT','CHANGE_LANE_LEFT','CHANGE_LANE_RIGHT','HOLD','YIELD'}<=actions
