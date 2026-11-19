"""Stress test: widen two real YOLO boxes of different cars to near-identical boxes."""
import json,pathlib,types
from tools.pointcloud_p0.replay_io import read
from integration.target_group_localization import localize_groups
from integration.duplicate_detection_grouper import box_iou
BASE=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');source=[BASE/'pointcloud_overlap_holdout_raw_20261117'];out=BASE/'pointcloud_group_holdout_adversarial_20261117';out.mkdir(exist_ok=True);results=[]
for root in source:
 for file in sorted(root.glob('*/*/result.json')):
  d,l,r,rad,e,objects=read(file.parent);ev=d['evaluation'];match={x['id']:x['gt_match']['role'] for x in ev['detections'] if x['gt_match']};pairs=[(a,b) for i,a in enumerate(objects) for b in objects[i+1:] if a.track_id in match and b.track_id in match and match[a.track_id]!=match[b.track_id]]
  if not pairs:continue
  a,b=pairs[0];q0=a.bbox_xyxy_norm;q1=b.bbox_xyxy_norm;union=(min(q0[0],q1[0]),min(q0[1],q1[1]),max(q0[2],q1[2]),max(q0[3],q1[3]));shift=.0001;new=[]
  for o,box in [(a,union),(b,(union[0]+shift,union[1],union[2]+shift,union[3]))]:new.append(types.SimpleNamespace(track_id=o.track_id,class_name=o.class_name,confidence=o.confidence,bbox_xyxy_norm=box))
  result=localize_groups(new,l,r,rad,e);merged=any(len(g['members'])>1 for g in result['groups']);pair=result['pair_evidence'][0];results.append({'source':str(file.parent),'roles_before_box_perturbation':[match[a.track_id],match[b.track_id]],'ids':[a.track_id,b.track_id],'original_iou':box_iou(q0,q1),'injected_iou':box_iou(new[0].bbox_xyxy_norm,new[1].bbox_xyxy_norm),'merged':merged,'pair_evidence':pair,'group_results':[{'members':[m['id'] for m in g['members']],'status':g['status'],'reason':g['reason']} for g in result['groups']]});print('case',len(results),file.parent, 'merged',merged,pair['reason'],flush=True)
summary={'description':'Artificial stress, not raw YOLO: two original detections matched to different actors; both boxes replaced by almost identical enclosing boxes. Actor labels only used to score after inference; source roles may no longer be spatially distinguishable in the altered boxes.','case_count':len(results),'different_vehicles_merged':sum(x['merged'] for x in results),'results':results};(out/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print('SUMMARY',len(results),summary['different_vehicles_merged'])
