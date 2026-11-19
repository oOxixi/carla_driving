import json,os
from pathlib import Path
P=Path(os.environ.get('POINTCLOUD_P0_OUTPUT','/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_p0_radar_compare_20261117'))
out={'frames':[]}
for rep in range(5):
 path=P/'occlusion'/str(rep)/'result.json'
 if not path.exists():out['frames'].append({'repeat':rep,'status':'ERROR'});continue
 d=json.loads(path.read_text())
 row={'repeat':rep,'frame':d['frame'],'status':d['status']}
 for name,pred,ev in [('before',d['baseline']['predictions'],d['baseline']['evaluation']),('after',d['predictions'],d['evaluation'])]:
  r={'target':0,'other_vehicle':0,'outside_actor_boxes':0,'ambiguous':0,'total':0,'matched_located':0,'selected_lidar_target':0,'selected_lidar_other':0,'selected_lidar_unknown':0}
  for e in ev['detections']:
   if e.get('errors'):r['matched_located']+=1
   if e.get('gt_match') and e['selected']['target'] is not None:
    z=e['selected'];r['selected_lidar_target']+=z['target'];r['selected_lidar_other']+=z['matched_semantic']-z['target'];r['selected_lidar_unknown']+=z['unknown']
   for k in ('target','other_vehicle','outside_actor_boxes','ambiguous','total'):
    r[k]+=e.get('radar_box_audit',{}).get(k,0)
  row[name]=r
 out['frames'].append(row)
for name in ('before','after'):
 out[name]={k:sum(x.get(name,{}).get(k,0) for x in out['frames']) for k in ('target','other_vehicle','outside_actor_boxes','ambiguous','total','matched_located','selected_lidar_target','selected_lidar_other','selected_lidar_unknown')}
(P/'summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
