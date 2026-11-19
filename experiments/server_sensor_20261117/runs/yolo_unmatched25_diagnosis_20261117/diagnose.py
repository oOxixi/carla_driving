"""Read-only YOLO replay; all simulator GT used only after model output."""
import ast,csv,collections,hashlib,json,math,pathlib
import numpy as np
from PIL import Image,ImageDraw
from integration.rgb_detector import OnnxYoloDetector,_letterbox,_class_aware_nms,COCO_ROAD_USERS
from integration.object_tracker import SensorObjectTracker
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');SRC=P/'pointcloud_adaptive_development_20261117/new_scenes/holdout';OUT=P/'yolo_unmatched25_diagnosis_20261117';(OUT/'annotated').mkdir(exist_ok=True)
model=pathlib.Path('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx');detector=OnnxYoloDetector(model);names=ast.literal_eval(detector._session.get_modelmeta().custom_metadata_map['names']);excluded={'holdout_257_36','holdout_257_43','holdout_257_50'};rows=[];allrows=[];validations=[]
def ious(box,boxes):
 boxes=np.asarray(boxes,dtype=float).reshape(-1,4);box=np.asarray(box,dtype=float);q=np.maximum(0,np.minimum(box[2:],boxes[:,2:])-np.maximum(box[:2],boxes[:,:2]));inter=q[:,0]*q[:,1];a=max(0,box[2]-box[0])*max(0,box[3]-box[1]);other=np.prod(np.maximum(0,boxes[:,2:]-boxes[:,:2]),axis=1);return inter/np.maximum(a+other-inter,1e-9)
def best_candidate(indices,iou,scores,cls,boxes,center):
 if len(indices)==0:return None
 j=int(indices[np.argmax(scores[indices])]);return {'row':j,'class_id':int(cls[j]),'class':names[int(cls[j])],'confidence':float(scores[j]),'iou':float(iou[j]),'box_px':[float(x) for x in boxes[j]],'center_distance_px':float(center[j])}
def best_overlap(indices,iou,scores,cls,boxes,center):
 if len(indices)==0:return None
 j=int(indices[np.argmax(iou[indices])]);return {'row':j,'class_id':int(cls[j]),'class':names[int(cls[j])],'confidence':float(scores[j]),'iou':float(iou[j]),'box_px':[float(x) for x in boxes[j]],'center_distance_px':float(center[j])}
for f in sorted(SRC.glob('*/result.json')):
 if f.parent.name in excluded:continue
 d=json.loads(f.read_text());img=np.asarray(Image.open(f.parent/'camera.png').convert('RGB'));assert img.shape==(450,800,3);tensor,tf=_letterbox(img,detector._input_width,detector._input_height);out=detector._session.run(None,{detector._input_name:tensor})[0];a=np.squeeze(out);a=a.T if a.shape[0] in (84,85) else a;assert a.shape[1]==84
 scores_matrix=a[:,4:];cls=np.argmax(scores_matrix,axis=1);scores=scores_matrix[np.arange(len(a)),cls];xywh=a[:,:4];boxes=np.empty_like(xywh);boxes[:,0]=xywh[:,0]-xywh[:,2]/2;boxes[:,1]=xywh[:,1]-xywh[:,3]/2;boxes[:,2]=xywh[:,0]+xywh[:,2]/2;boxes[:,3]=xywh[:,1]+xywh[:,3]/2;boxes[:,[0,2]]=(boxes[:,[0,2]]-tf.pad_x)/tf.scale;boxes[:,[1,3]]=(boxes[:,[1,3]]-tf.pad_y)/tf.scale;boxes[:,[0,2]]=np.clip(boxes[:,[0,2]],0,800);boxes[:,[1,3]]=np.clip(boxes[:,[1,3]],0,450);valid=(boxes[:,2]>boxes[:,0])&(boxes[:,3]>boxes[:,1])&np.isfinite(scores);road=np.isin(cls,list(COCO_ROAD_USERS));vehicle=np.isin(cls,[2,5,7]);eligible=np.flatnonzero(valid&road&(scores>=detector.confidence_threshold));chosen=eligible[_class_aware_nms(boxes[eligible],scores[eligible],cls[eligible],detector.iou_threshold)] if len(eligible) else np.array([],dtype=int);chosen_vehicles=chosen[np.isin(cls[chosen],[2,5,7])]
 decoded=detector._decode(out,tf);tracker=SensorObjectTracker();tracked=[o for o in tracker.update(d['frame'],decoded) if o.class_name in ('car','truck','bus')];old=d['predictions'];assert len(old)==len(tracked),(d['case'],len(old),len(tracked))
 for o,q in zip(old,tracked):assert o['id']==q.track_id and o['class']==q.class_name and abs(o['confidence']-q.confidence)<1e-5 and np.max(np.abs(np.array(o['bbox'])-np.array(q.bbox_xyxy_norm)))<1e-5,(d['case'],o['id'])
 validations.append({'case':d['case'],'predictions':len(old),'exact_replay':True});gt=d['evaluation']['gt_projected_boxes_px'];roleids=d['evaluation']['gt_actor_ids'];matched=set(d['evaluation']['matched_roles']);role_positions=d['gt_positions_all'];tracker_boxes={o['id']:np.asarray(o['bbox'])*[800,450,800,450] for o in old}
 for role in d['evaluation']['expected_roles']:
  target=np.asarray(gt[role],dtype=float);iou=ious(target,boxes);centers=(boxes[:,:2]+boxes[:,2:])/2;tc=(target[:2]+target[2:])/2;cd=np.linalg.norm(centers-tc,axis=1);diag=float(np.linalg.norm(target[2:]-target[:2]));cand=valid&(iou>=.30);vi=np.flatnonzero(cand&vehicle);ai=np.flatnonzero(cand);oi=np.flatnonzero(cand&~vehicle);final=np.array([j for j in chosen_vehicles if iou[j]>=.30],dtype=int);close_final=np.array([j for j in chosen_vehicles if iou[j]>=.10 or (cd[j]<=.5*diag and iou[j]>0)],dtype=int)
  best_final=best_overlap(chosen_vehicles,iou,scores,cls,boxes,cd);best_pre=best_candidate(vi,iou,scores,cls,boxes,cd);best_wrong=best_candidate(oi,iou,scores,cls,boxes,cd);best_any=best_candidate(ai,iou,scores,cls,boxes,cd);potential=best_overlap(close_final,iou,scores,cls,boxes,cd)
  pixelx1=max(0,int(math.floor(target[0])));pixely1=max(0,int(math.floor(target[1])));pixelx2=min(800,int(math.ceil(target[2])));pixely2=min(450,int(math.ceil(target[3])));crop=img[pixely1:pixely2,pixelx1:pixelx2].astype(float);luma=(crop[:,:,0]*.2126+crop[:,:,1]*.7152+crop[:,:,2]*.0722) if crop.size else np.empty(0);front_overlap=[]
  for other,b in gt.items():
   if other==role or role_positions[other]['nearest_box_distance_m']>=role_positions[role]['nearest_box_distance_m']:continue
   b=np.asarray(b);over=np.maximum(0,np.minimum(target[2:],b[2:])-np.maximum(target[:2],b[:2]));frac=float(np.prod(over)/max(np.prod(np.maximum(0,target[2:]-target[:2])),1e-9))
   if frac>0:front_overlap.append({'other_role':other,'gt_box_overlap_fraction':frac})
  raw_pass=vi[scores[vi]>=.35];survive=set(int(x) for x in chosen);suppressed=[int(x) for x in raw_pass if x not in survive]
  other_role_matches=[{'role':e['gt_match']['role'],'id':e['id'],'iou_to_missing':float(ious(target,[tracker_boxes[e['id']]])[0])} for e in d['evaluation']['detections'] if e['gt_match']]
  if role in matched:category='MATCHED'
  elif len(final):category='正式车框达到IoU但匹配冲突'
  elif potential:category='正式车框有空间重叠但IoU不足，待核对'
  elif best_wrong and best_wrong['confidence']>=.35:category='非车辆类别高分候选，待核对'
  elif len(raw_pass) and suppressed:category='高分车候选在NMS中被抑制，待核对'
  elif best_pre and best_pre['confidence']<.35:category='有低于阈值的车类候选'
  else:category='无IoU达0.30的车类候选'
  topvi=sorted(vi,key=lambda j:float(scores[j]),reverse=True)[:8];topother=sorted(oi,key=lambda j:float(scores[j]),reverse=True)[:8]
  row={'case':d['case'],'frame':d['frame'],'role':role,'actor_id':roleids[role],'matched':role in matched,'vehicle_model':d['plan']['model'] if role=='T' else ('vehicle.ford.mustang' if d['plan']['scene_type']=='adjacent' else 'vehicle.audi.a2'),'weather':d['plan']['weather'],'scene_type':d['plan']['scene_type'],'yaw_offset_deg':d['plan']['yaw_offset_deg'] if role=='T' else 0,'distance_center_m':float(np.linalg.norm(np.asarray(role_positions[role]['center_ego'])[:2])),'distance_nearest_box_m':role_positions[role]['nearest_box_distance_m'],'gt_box_px':[float(z) for z in target],'gt_box_width_px':float(target[2]-target[0]),'gt_box_height_px':float(target[3]-target[1]),'gt_box_clipped_area_fraction':float(max(0,min(800,target[2])-max(0,target[0]))*max(0,min(450,target[3])-max(0,target[1]))/max(np.prod(np.maximum(target[2:]-target[:2],0)),1e-9)),'gt_box_crop_mean_luma':float(luma.mean()) if luma.size else None,'gt_box_crop_dark_fraction':float(np.mean(luma<25.5)) if luma.size else None,'front_vehicle_box_overlap':front_overlap,'all_final_detections':[{**o,'bbox_px':tracker_boxes[o['id']].tolist()} for o in old],'best_final_vehicle_iou':best_final,'best_final_close_candidate':potential,'best_pre_nms_vehicle_iou30':best_pre,'best_pre_nms_any_class_iou30':best_any,'best_pre_nms_wrong_class_iou30':best_wrong,'raw_vehicle_iou30_above_threshold':len(raw_pass),'raw_vehicle_iou30_suppressed_nms':len(suppressed),'final_vehicle_iou30_count':len(final),'competing_matched_boxes':other_role_matches,'class_category':category,'top_vehicle_raw_iou30':[best_candidate(np.array([j]),iou,scores,cls,boxes,cd) for j in topvi],'top_other_raw_iou30':[best_candidate(np.array([j]),iou,scores,cls,boxes,cd) for j in topother]}
  allrows.append(row)
  if role not in matched:
   rows.append(row);canvas=Image.fromarray(img).copy();draw=ImageDraw.Draw(canvas);draw.rectangle(tuple(target),outline='red',width=2);draw.text((max(0,target[0]),max(0,target[1]-14)),f'GT {role}',fill='red')
   for o in old:
    b=tracker_boxes[o['id']];draw.rectangle(tuple(b),outline='lime',width=2);draw.text((b[0],max(0,b[1]-12)),f"{o['id']} {o['class']} {o['confidence']:.2f}",fill='lime')
   if best_pre and best_pre['confidence']<.35:
    draw.rectangle(tuple(best_pre['box_px']),outline='yellow',width=1);draw.text((4,4),f"low {best_pre['class']} {best_pre['confidence']:.3f} IoU {best_pre['iou']:.2f}",fill='yellow')
   canvas.save(OUT/'annotated'/f"{d['case']}_{role}.png")
 print('DONE',d['case'],'expected',len(gt),'matched',len(matched),flush=True)
assert len(validations)==21 and len(allrows)==35 and len(rows)==25
meta={'source':str(SRC),'original_model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'original_detector':{'confidence_threshold':detector.confidence_threshold,'nms_iou':detector.iou_threshold,'model_input':[detector._input_width,detector._input_height],'class_argmax_then_filter':True,'vehicle_classes':['car','bus','truck'],'matching':'greedy 1-to-1 projected full actor 3D-box IoU>=0.3'},'exact_replay_images':len(validations),'rows':rows,'all_target_rows':allrows,'replay_checks':validations,'warning':'GT full actor projected boxes include occluded surfaces; IoU does not independently measure image visibility or prove detection assignment. Low confidence raw anchors are diagnostic candidates, not production detections.'}
(OUT/'diagnosis.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n');fields=['case','frame','role','vehicle_model','weather','scene_type','distance_center_m','distance_nearest_box_m','gt_box_width_px','gt_box_height_px','gt_box_clipped_area_fraction','gt_box_crop_mean_luma','gt_box_crop_dark_fraction','class_category','final_vehicle_iou30_count','raw_vehicle_iou30_above_threshold','raw_vehicle_iou30_suppressed_nms']
with (OUT/'unmatched25.csv').open('w',encoding='utf-8-sig',newline='') as o:
 w=csv.DictWriter(o,fieldnames=fields+['best_raw_car_score','best_raw_car_iou','best_wrong_class','best_wrong_score','best_wrong_iou','best_final_iou','best_final_class','front_overlap'],extrasaction='ignore');w.writeheader()
 for r in rows:
  b=r['best_pre_nms_vehicle_iou30'] or {};x=r['best_pre_nms_wrong_class_iou30'] or {};z=r['best_final_vehicle_iou'] or {};w.writerow({**r,'best_raw_car_score':b.get('confidence'),'best_raw_car_iou':b.get('iou'),'best_wrong_class':x.get('class'),'best_wrong_score':x.get('confidence'),'best_wrong_iou':x.get('iou'),'best_final_iou':z.get('iou'),'best_final_class':z.get('class'),'front_overlap':r['front_vehicle_box_overlap']})
print('COMPLETE',len(rows),'categories',dict(collections.Counter(r['class_category'] for r in rows)))
