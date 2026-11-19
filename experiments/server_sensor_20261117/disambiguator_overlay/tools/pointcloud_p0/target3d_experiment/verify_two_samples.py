"""Recheck saved outcomes with sensor-only geometry and ownership independently."""
import argparse,csv,json,pathlib
import numpy as np

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=pathlib.Path);ap.add_argument('--holdout-root',required=True,type=pathlib.Path);args=ap.parse_args();p=args.output
 frozen=json.loads((p/'frozen_sensor_decisions.json').read_text());audits=json.loads((p/'formal_audit.json').read_text());post=json.loads((p/'offline_audit.json').read_text());ownership=list(csv.DictReader((p/'point_ownership.csv').open(encoding='utf-8-sig')))
 assert len(frozen)==8 and len(post)==8 and len(audits)==2
 assert all(v['unchanged_all_localizer_return_fields'] and v['unique_sensor_point_ownership'] and v['geometry_algorithm_truth_free'] for v in audits)
 assert all(v['decision']['status']=='UNKNOWN' and not v['decision']['formal_control_authority'] for v in frozen)
 for e in frozen:
  formal=set(e['formal_selected_ids']);candidate=set(e['candidate_point_ids']);selected=set(e['candidate_cluster_ids']);neighbor=set(e['other_auxiliary_candidate_ids']);reserved=set(e['formal_reserved_ids']);assert not formal&candidate and not candidate&neighbor and not candidate&reserved and selected<=candidate
  rows=[r for r in ownership if r['case']==e['case'] and r['radius_name']==e['radius_name']];assert len(rows)==len({r['point_id'] for r in rows});assert set(int(r['point_id']) for r in rows if r['owner']=='FORMAL_SELECTED')==formal;assert set(int(r['point_id']) for r in rows if r['owner']=='AUX_CLUSTER_UNVALIDATED')==selected
 e=next(x for x in frozen if x['case']=='holdout_extra_250_25' and x['radius_name']=='TEST');assert len(e['formal_selected_ids'])==11 and len(e['candidate_point_ids'])==16 and len(e['candidate_cluster_ids'])==11;assert {'TEMPORAL_EVIDENCE_MISSING','THRESHOLDS_NOT_CALIBRATED'}<=set(e['decision']['reasons'])
 raw=np.fromfile(args.holdout_root/e['case']/'lidar.bin',dtype=np.float32).reshape(-1,4)[:,:3].astype(float);formal_xyz=raw[e['formal_selected_ids']];aux_xyz=raw[e['candidate_cluster_ids']];dist=float(np.min(np.linalg.norm(formal_xyz[:,None,:]-aux_xyz[None,:,:],axis=2)));fr=np.linalg.norm(formal_xyz,axis=1);ar=np.linalg.norm(aux_xyz,axis=1);gap=max(0.,float(ar.min()-fr.max()),float(fr.min()-ar.max()));assert abs(dist-e['decision']['current']['nearest_3d_points_m'])<1e-8 and abs(gap-e['decision']['current']['radial_interval_gap_m'])<1e-8
 second=[x for x in frozen if x['case']=='holdout_250_30'];assert [x['radius_m'] for x in second[1:]]==[.5098,.53,.55,.58,.60];assert all(not x['formal_target_id'] and not x['candidate_cluster_ids'] and 'NO_AUXILIARY_CLUSTER' in x['decision']['reasons'] for x in second)
 a=next(x for x in post if x['case']=='holdout_extra_250_25' and x['radius_name']=='TEST');assert a['point_precision']==1.0 and a['point_recall_conditional']==11/16 and a['other_vehicle_approx']==0
 print('PASS 8 frozen strategies, 2 frame invariants, point ownership, independent 3D/depth geometry, .5098-.60 sweep, post-hoc metrics')
if __name__=='__main__':main()
