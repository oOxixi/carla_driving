import json,os
from pathlib import Path
import numpy as np
ROOT=Path(os.environ.get('POINTCLOUD_P0_OUTPUT','/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_p0_20261117'))
cases=[('near','近距离'),('middle','中距离'),('far','远距离'),('occlusion','部分遮挡'),('sparse','点云稀疏'),('close','多车紧邻'),('rain','雨天'),('night','夜间'),('fog','雾天'),('default_mid','默认32线中距离'),('default_far','默认32线远距离')]
def quantile(a):
 return {'n':len(a),'p50':round(float(np.percentile(a,50)),3),'p95':round(float(np.percentile(a,95)),3)} if a else {'n':0,'p50':None,'p95':None}
def summarize(records):
 out={'runs':len(records),'expected':0,'detections':0,'matched_detections':0,'localized_predictions':0,'located_matched':0,
      'box_lidar':{'total':0,'semantic_matched':0,'target':0,'other':0,'unknown':0,'unscorable':0},
      'selected_lidar':{'total':0,'semantic_matched':0,'target':0,'other':0,'unknown':0,'unscorable':0},
      'radar':{'total':0,'target':0,'other_vehicle':0,'ambiguous':0,'outside_actor_boxes':0},
      'errors':{},'unknown_reasons':{},'sample_details':[]}
 errors={k:[] for k in ('cluster_center_vs_vehicle_center_3d_m','longitudinal_center_difference_m','lateral_center_difference_m','rear_longitudinal_error_m','nearest_surface_range_error_m','p10_surface_range_error_m')}
 for d in records:
  pred={o['id']:o for o in d['predictions']};ev=d['evaluation']
  out['expected']+=len(ev['expected_roles']);out['detections']+=len(pred);out['matched_detections']+=len(ev['matched_roles'])
  out['localized_predictions']+=sum(o['status']=='LOCATED_UNVALIDATED' for o in pred.values())
  for e in ev['detections']:
   o=pred[e['id']]
   if o['status']!='LOCATED_UNVALIDATED':out['unknown_reasons'][o['reason']]=out['unknown_reasons'].get(o['reason'],0)+1
   for stage,dest in [('box','box_lidar'),('selected','selected_lidar')]:
    z=e[stage];a=out[dest];a['total']+=z['total']
    if not e['gt_match']:
     a['unscorable']+=z['total'];continue
    a['semantic_matched']+=z['matched_semantic'];a['unknown']+=z['unknown'];a['target']+=z['target']
    a['other']+=z['matched_semantic']-z['target']
   if e.get('errors'):
    out['located_matched']+=1
    for k,v in e['errors'].items():errors[k].append(abs(v))
   if 'radar_box_audit' in e:
    for k in out['radar']:out['radar'][k]+=e['radar_box_audit'][k]
  out['sample_details'].append({'case':d['case'],'repeat':d['repeat'],'frame':d['frame'],'expected':len(ev['expected_roles']),'matched':len(ev['matched_roles']),'located_matched':sum(bool(x.get('errors')) for x in ev['detections']),'unmatched':ev['unmatched_roles']})
 out['detection_recall']=out['matched_detections']/out['expected'] if out['expected'] else None
 out['detection_precision']=out['matched_detections']/out['detections'] if out['detections'] else None
 out['unlocatable_expected']=out['expected']-out['located_matched']
 out['unlocatable_fraction']=out['unlocatable_expected']/out['expected'] if out['expected'] else None
 for a in (out['box_lidar'],out['selected_lidar']):
  a['semantic_coverage']=a['semantic_matched']/(a['semantic_matched']+a['unknown']) if a['semantic_matched']+a['unknown'] else None
  a['target_fraction']=a['target']/a['semantic_matched'] if a['semantic_matched'] else None
  a['other_fraction']=a['other']/a['semantic_matched'] if a['semantic_matched'] else None
 out['errors']={k:quantile(v) for k,v in errors.items()}
 return out
progress=json.loads((ROOT/'progress.json').read_text())
summary={'definitions':{'detection':'one-to-one full actor projected bbox IoU >=0.3; includes occluded actors','point_precision':'among semantic-matched points for uniquely assigned detections; semantic matching tolerance 0.08m, unmatched listed separately','radar':'point in CARLA actor OBB expanded 0.2m; outside/overlap unconfirmed, not necessarily wrong','center_error':'median visible surface point vs physical bounding-box center; NOT estimated vehicle center','surface_error':'min/p10 lidar horizontal radius versus nearest 2D OBB distance; may be negative','percentiles':'absolute errors of detected-and-located-matched vehicles only','unlocatable':'expected GT vehicles missing detection, unmatched or without valid cluster; no successes-only denominator','runs':'five static distance variations per category on one map; correlated, not independent generalization'},'cases':{},'run_errors':[]}
allrows=[]
for name,label in cases:
 rows=[]
 for run in progress['runs']:
  if run['case']!=name:continue
  if run['status']!='COMPLETED':summary['run_errors'].append(run);continue
  rows.append(json.loads((ROOT/name/str(run['repeat'])/'result.json').read_text()))
 allrows.extend(rows);summary['cases'][name]={'label':label,**summarize(rows)}
summary['overall']=summarize(allrows);summary['status']='COMPLETED' if len(progress['runs'])==55 else 'INCOMPLETE'
(ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
for name,c in summary['cases'].items():
 print(name,'detect',str(c['matched_detections'])+'/'+str(c['expected']),'located',str(c['located_matched'])+'/'+str(c['expected']),'selected lidar',c['selected_lidar']['target'],'/',c['selected_lidar']['semantic_matched'],'range p50/p95',c['errors']['nearest_surface_range_error_m'])
print('OVERALL',json.dumps(summary['overall'],ensure_ascii=False))
