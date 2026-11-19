"""Offline confidence sensitivity; no production threshold or control integration."""
import csv,hashlib,html,json,math,pathlib,sys,time
import numpy as np
from PIL import Image,ImageDraw
from integration.rgb_detector import OnnxYoloDetector,_letterbox
from integration.object_tracker import SensorObjectTracker
from integration.target_group_localization import localize_groups
from integration.target_pointcloud_localization import _transform
from tools.pointcloud_p0.run_matrix import iou
BASE=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');PREV=BASE/'pointcloud_adaptive_development_20261117';PRIOR=BASE/'yolo_unmatched25_diagnosis_20261117';OUT=BASE/'yolo_threshold_sensitivity_20261117';(OUT/'overlays').mkdir(exist_ok=True);sys.path.insert(0,str(PREV));from eval_helpers import sample_new,truth_labels
SRC=PREV/'new_scenes/holdout';EXCLUDED={'holdout_257_36','holdout_257_43','holdout_257_50'};files=[x for x in sorted(SRC.glob('*/result.json')) if x.parent.name not in EXCLUDED];assert len(files)==21
MODEL=pathlib.Path('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx');detector=OnnxYoloDetector(MODEL);assert detector.confidence_threshold==.35 and detector.iou_threshold==.45;thresholds=[.35,.30,.25,.20,.15];records=[];frames=[];base_checked=0;strong_checked=0

def match(detections,gt):
 cand=[]
 for o in detections:
  box=[v*s for v,s in zip(o.bbox_xyxy_norm,[800,450,800,450])]
  for role,b in gt.items():
   score=iou(box,b)
   if score>=.3:cand.append((score,o.track_id,role))
 cand.sort(reverse=True);used_ids=set();used_roles=set();out={}
 for score,ident,role in cand:
  if ident not in used_ids and role not in used_roles:out[ident]={'role':role,'iou':score};used_ids.add(ident);used_roles.add(role)
 return out

def pixels(mask,box):
 x1=max(0,int(math.floor(box[0])));y1=max(0,int(math.floor(box[1])));x2=min(800,int(math.ceil(box[2])));y2=min(450,int(math.ceil(box[3])));return int(mask[y1:y2,x1:x2].sum()) if x2>x1 and y2>y1 else 0

def signature(o):return (o.class_name,round(o.confidence,6),tuple(round(v,6) for v in o.bbox_xyxy_norm))
for n,f in enumerate(files):
 sample=sample_new(f.parent);d=sample['d'];img=np.asarray(Image.open(f.parent/'camera.png').convert('RGB'));tensor,tf=_letterbox(img,detector._input_width,detector._input_height);raw=detector._session.run(None,{detector._input_name:tensor})[0];labels=truth_labels(sample);original=d['predictions'];gt=d['evaluation']['gt_projected_boxes_px'];roleids=d['evaluation']['gt_actor_ids'];truthpos=d['gt_positions_all'];v=json.loads((PRIOR/'visibility_cases'/f"{d['case']}.json").read_text());arr=np.fromfile(PRIOR/'reconstructed'/f"{d['case']}_full_instance.bgra",dtype=np.uint8).reshape(450,800,4);instance=arr[:,:,0].astype(np.uint32)*256+arr[:,:,1].astype(np.uint32);tag=arr[:,:,2];vehicle_mask=np.isin(tag,[14,15,16]);masks={role:(instance==item['actor_id']%65536)&vehicle_mask for role,item in v['full_visible'].items()};assert all(int(masks[k].sum())==v['full_visible'][k]['visible_pixels'] for k in masks)
 base_signatures=None;baseline_match=None;baseline_group=None
 for threshold in thresholds:
  detector.confidence_threshold=threshold;decoded=detector._decode(raw,tf);tracked=[o for o in SensorObjectTracker().update(d['frame'],decoded) if o.class_name in ('car','truck','bus')];mapping=match(tracked,gt);strong={signature(o) for o in tracked if o.confidence>=.35};low=[o for o in tracked if o.confidence<.35]
  if threshold==.35:
   assert len(tracked)==len(original)
   for old,o in zip(original,tracked):assert old['id']==o.track_id and old['class']==o.class_name and abs(old['confidence']-o.confidence)<1e-5 and np.max(np.abs(np.array(old['bbox'])-np.array(o.bbox_xyxy_norm)))<1e-5
   assert {m['role'] for m in mapping.values()}==set(d['evaluation']['matched_roles']);base_signatures=strong;baseline_match={m['role'] for m in mapping.values()};base_checked+=1
  else:assert strong==base_signatures;strong_checked+=1
  loc=localize_groups(tracked,sample['lid'],sample['rgb'],sample['rad'],sample['ego']);
  if threshold==.35:baseline_group=loc
  rw=loc['radar_world'];rc=_transform(rw,np.asarray(sample['rgb'].transform.get_inverse_matrix()));focal=800/(2*math.tan(math.radians(50)));su=(focal*rc[:,1]/np.maximum(rc[:,0],1e-6)+400)/800;sv=(-focal*rc[:,2]/np.maximum(rc[:,0],1e-6)+225)/450;radm=[]
  for group in loc['groups']:
   mask=np.zeros(len(rw),dtype=bool)
   for member in group['members']:
    x1,y1,x2,y2=member['bbox'];mask|=(rc[:,0]>1)&(su>=x1)&(su<=x2)&(sv>=y1)&(sv<=y2)
   radm.append(mask)
  radcount=np.sum(radm,axis=0) if radm else np.zeros(len(rw),dtype=int)
  radar_role_masks={}
  for role,box in d['gt_bbox_all'].items():
   local=_transform(rw,np.linalg.inv(np.asarray(box['matrix_world'])));radar_role_masks[role]=np.all(np.abs(local)<=np.asarray(box['extent'])+.2,axis=1)
  info_by_id={m['id']:(i,g) for i,g in enumerate(loc['groups']) for m in g['members']};frame_multi=0;frame_nomask=0;frame_rows=[]
  for o in tracked:
   bbox=[float(x*s) for x,s in zip(o.bbox_xyxy_norm,[800,450,800,450])];cover={role:(pixels(mask,bbox)/int(mask.sum()) if mask.any() else None) for role,mask in masks.items()};multi=sum(vv is not None and vv>=.5 for vv in cover.values())>=2;vehicle_pixels=pixels(vehicle_mask,bbox);low_flag=o.confidence<.35;matched=mapping.get(o.track_id);role=matched['role'] if matched else None;gi,g=info_by_id[o.track_id];radar_unique=radm[gi]&(radcount==1);radar_target=int(np.sum(radar_unique & radar_role_masks[role] & (sum(mask.astype(int) for mask in radar_role_masks.values())==1))) if role else None;ng_indices=np.asarray(g['nonground_point_indices'],dtype=int);box_indices=np.asarray(g['box_point_indices'],dtype=int);lidar_box_target=int(np.sum(labels[box_indices]==roleids[role])) if role else None;lidar_ng_target=int(np.sum(labels[ng_indices]==roleids[role])) if role else None;mapped_roles={mapping[m['id']]['role'] for m in g['members'] if m['id'] in mapping};sel=np.asarray(g['selected_point_indices'],dtype=int);lab=labels[sel];tid=roleids.get(role);target=int(np.sum(lab==tid)) if role else 0;other=int(np.sum(np.isin(lab,[v for k,v in roleids.items() if k!=role]))) if role else 0;unknown=int(np.sum(lab==-1));background=int(len(lab)-target-other-unknown) if role else 0;pure=bool(role and len(mapped_roles)==1 and g['status']=='LOCATED_UNVALIDATED' and len(sel)>=3 and target==len(sel));dist_error=(float(g['nearest_surface_distance_m']-truthpos[role]['nearest_box_distance_m']) if role and g['status']=='LOCATED_UNVALIDATED' else None)
   row={'case':d['case'],'frame':d['frame'],'threshold':threshold,'id':o.track_id,'class':o.class_name,'confidence':float(o.confidence),'bbox_px':bbox,'low_confidence_candidate':low_flag,'matched_role':role,'match_iou':matched['iou'] if matched else None,'recovered_vs_baseline':bool(role and role not in baseline_match),'visible_vehicle_pixels_in_box_reconstructed':vehicle_pixels,'per_target_visible_pixel_coverage':cover,'box_covers_two_targets_50pct':multi,'group_id':g['group_id'],'group_member_ids':[m['id'] for m in g['members']],'group_mapped_roles':sorted(mapped_roles),'group_status':g['status'],'group_reason':g['reason'],'lidar_box_points':len(g['box_point_indices']),'lidar_nonground':len(g['nonground_point_indices']),'lidar_box_target_semantic':lidar_box_target,'lidar_nonground_target_semantic':lidar_ng_target,'radar_unique_group':int(np.sum(radar_unique)),'radar_target_bbox_approx':radar_target,'selected_total':len(sel),'selected_target':target,'selected_other_vehicle':other,'selected_background':background,'selected_unmatched_semantic':unknown,'correct_3d_point_support':pure,'nearest_surface_error_m':dist_error,'radar_is_synchronized':True,'manual_review':'NOT_PERFORMED'};frame_rows.append(row);records.append(row);frame_multi+=int(multi);frame_nomask+=int(vehicle_pixels==0)
  strong_changes=[]
  if threshold!=.35:
   oldmap={m['id']:g for g in baseline_group['groups'] for m in g['members']};newmap={m['id']:g for g in loc['groups'] for m in g['members']}
   for ident,old in oldmap.items():
    new=newmap[ident]
    if old['status']!=new['status'] or old['reason']!=new['reason'] or old['selected_point_indices']!=new['selected_point_indices'] or [m['id'] for m in old['members']]!=[m['id'] for m in new['members']]:strong_changes.append(ident)
  frame={'case':d['case'],'frame':d['frame'],'threshold':threshold,'expected_roles':list(roleids),'matched_roles':sorted({v['role'] for v in mapping.values()}),'matched_detection_count':len(mapping),'output_vehicle_boxes':len(tracked),'high_boxes':len(strong),'low_boxes':len(low),'low_matched_boxes':sum(x['low_confidence_candidate'] and x['matched_role'] is not None for x in frame_rows),'low_unmatched_boxes':sum(x['low_confidence_candidate'] and x['matched_role'] is None for x in frame_rows),'low_no_vehicle_pixels':sum(x['low_confidence_candidate'] and x['visible_vehicle_pixels_in_box_reconstructed']==0 for x in frame_rows),'shared_boxes':frame_multi,'shared_low_boxes':sum(x['low_confidence_candidate'] and x['box_covers_two_targets_50pct'] for x in frame_rows),'low_supported_boxes':sum(x['low_confidence_candidate'] and x['correct_3d_point_support'] for x in frame_rows),'recovered_roles':sorted({x['matched_role'] for x in frame_rows if x['recovered_vs_baseline']}),'lost_baseline_roles':sorted(baseline_match-{v['role'] for v in mapping.values()}),'strong_group_changes':strong_changes,'no_vehicle_mask_boxes':frame_nomask,'gt_matched':mapping};frames.append(frame)
  if threshold<.35 and low:
   canvas=Image.fromarray(img).copy();draw=ImageDraw.Draw(canvas)
   for role,b in gt.items():draw.rectangle(tuple(b),outline='#ff4545',width=1);draw.text((b[0],max(0,b[1]-12)),f'GT {role}',fill='#ff4545')
   for o in tracked:
    box=[float(x*s) for x,s in zip(o.bbox_xyxy_norm,[800,450,800,450])];color='#ffcf00' if o.confidence<.35 else '#38f585';draw.rectangle(tuple(box),outline=color,width=2);draw.text((box[0],min(438,max(0,box[1]-10))),f'{o.track_id} {o.class_name} {o.confidence:.3f}',fill=color)
   canvas.save(OUT/'overlays'/f"{d['case']}_t{int(round(threshold*100)):02d}.png")
 print('DONE',n+1,d['case'],flush=True)
detector.confidence_threshold=.35;assert len(frames)==105 and base_checked==21 and strong_checked==84
meta={'frames':len(files),'original_targets':sum(len(x['evaluation']['expected_roles']) for x in [json.loads(f.read_text()) for f in files]),'thresholds':thresholds,'original_confidence':.35,'nms_iou':.45,'matching':'greedy one-to-one IoU>=0.30 with projected actor 3D bounding boxes; misses retained in denominator','reconstructed_mask':'supplemental reconstruction from previous task, target coverage threshold 50% per actor; not original-image semantic truth; unmatched detection is not confirmed false positive','three_d_support':'matched candidate group LOCATED_UNVALIDATED with >=3 selected LiDAR points, all assigned by 0.08m semantic nearest neighbor to matched actor and no unknowns; these are offline truth checks, not a calibrated safe/control claim','single_frame':'all 21 images are separate scenarios, no valid temporal persistence test','radar':'new dataset radar timestamps genuinely aligned to LiDAR; only original scheme C use, no motion or cross-frame validation','manual_review':'NOT_PERFORMED; overlays and candidate records supplied for human annotation','production':'unchanged, low boxes never passed to vehicle control','model_sha256':hashlib.sha256(MODEL.read_bytes()).hexdigest(),'original_replay_checks':base_checked,'strong_detector_output_preservation_checks':strong_checked}
(OUT/'frames.json').write_text(json.dumps(frames,ensure_ascii=False,indent=2)+'\n');(OUT/'detections.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n');(OUT/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n');keys=list(records[0]);
with (OUT/'detections.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(records)
print('COMPLETE frames',len(frames),'detection rows',len(records),'baseline',base_checked,'high-box unchanged',strong_checked)
