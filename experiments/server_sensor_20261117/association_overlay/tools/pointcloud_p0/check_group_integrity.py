import json,pathlib,collections,math
import numpy as np
BASE=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');sets=['pointcloud_group_regression55_20261117','pointcloud_group_regression20_20261117','pointcloud_group_sweep_20261117','pointcloud_group_focus_20261117','pointcloud_group_holdout_20261117'];counts=collections.Counter();range_diffs=[]
for name in sets:
 for f in (BASE/name).glob('*/*/result.json'):
  d=json.loads(f.read_text());source=pathlib.Path(d['point_data_source']);raw=json.loads((source/'result.json').read_text());n=(source/'lidar.bin').stat().st_size//16;state=np.fromfile(f.parent/'point_status.u8',dtype=np.uint8);owner=np.fromfile(f.parent/'point_owner.i32',dtype='<i4');reason=np.fromfile(f.parent/'point_reason.u8',dtype=np.uint8);assert len(state)==len(owner)==len(reason)==n;assert set(np.unique(state))<={0,1,2};assert set(np.unique(reason))<={0,1,2,3,4,5,6};assert np.all(owner[state!=1]==-1)
  actual=[]
  for i,g in enumerate(d['groups']):
   indices=g['selected_point_indices'];actual.extend(indices);assert all(state[k]==1 and owner[k]==i and reason[k]==4 for k in indices)
  assert len(actual)==len(set(actual))==int((state==1).sum());counts.update({'frames':1,'points':n,'assigned':int((state==1).sum()),'ambiguous':int((state==0).sum()),'environment':int((state==2).sum())})
  old={e['gt_match']['role']:e['errors']['nearest_surface_range_error_m'] for e in raw['evaluation']['detections'] if e.get('gt_match') and 'errors' in e}
  for g in d['groups']:
   role=g.get('role_audit')
   if role in old and 'range_error_m' in g:range_diffs.append(abs(g['range_error_m']-old[role]))
assert counts['frames']==109
out={'frames':counts['frames'],'points':counts['points'],'assigned':counts['assigned'],'ambiguous':counts['ambiguous'],'environment':counts['environment'],'all_points_unique_owner_and_reason':True,'comparable_old_new_range_samples':len(range_diffs),'same_sample_range_error_delta_p95':float(np.percentile(range_diffs,95)) if range_diffs else None,'same_sample_range_error_delta_max':max(range_diffs) if range_diffs else None}
(BASE/'pointcloud_p0_diagnosis_20261117/group_acceptance/integrity.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,indent=2))
