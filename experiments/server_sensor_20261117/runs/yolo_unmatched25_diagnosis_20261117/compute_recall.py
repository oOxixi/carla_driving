import collections,json,pathlib,numpy as np
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/yolo_unmatched25_diagnosis_20261117');d=json.loads((P/'diagnosis.json').read_text());v=json.loads((P/'visible_mask_audit.json').read_text())['rows'];vis={(x['case'],x['role']):x for x in v};raw={x.stem:json.loads(x.read_text()) for x in (P/'visibility_cases').glob('*.json')}
def iou(a,b):
 a=np.asarray(a,float);b=np.asarray(b,float);wh=np.maximum(0,np.minimum(a[2:],b[2:])-np.maximum(a[:2],b[:2]));intr=np.prod(wh);return float(intr/max(1e-9,np.prod(np.maximum(a[2:]-a[:2],0))+np.prod(np.maximum(b[2:]-b[:2],0))-intr))
bycase=collections.defaultdict(list)
for x in d['all_target_rows']:bycase[x['case']].append(x)
matched_visible=[];frame_data=[]
for case,targets in sorted(bycase.items()):
 dets=targets[0]['all_final_detections'];pairs=[]
 for a in dets:
  for t in targets:
   box=raw[case]['full_visible'][t['role']]['visible_bbox_px']
   if box:
    overlap=iou(a['bbox_px'],box)
    if overlap>=.3:pairs.append((overlap,a['id'],t['role']))
 pairs.sort(reverse=True);ud=set();ur=set();chosen=[]
 for ov,di,ro in pairs:
  if di in ud or ro in ur:continue
  ud.add(di);ur.add(ro);chosen.append({'id':di,'role':ro,'iou':ov});matched_visible.append((case,ro))
 frame_data.append({'case':case,'expected':len(targets),'vehicle_detection_count':len(dets),'matches_visible_box':chosen})
strict={(x['case'],x['role']) for x in d['all_target_rows'] if x['matched']};alternative=set(matched_visible);unmatched=[x for x in d['all_target_rows'] if not x['matched']];maskcover=[]
for x in v:
 b=x['best_final_mask_support'];
 if b and b['target']['target_pixel_coverage'] is not None and b['target']['target_pixel_coverage']>=.5:maskcover.append((x['case'],x['role']))
rawveh=[x for x in unmatched if x['best_pre_nms_vehicle_iou30']];below=[x for x in rawveh if x['best_pre_nms_vehicle_iou30']['confidence']<.35];wrong=[x for x in unmatched if x['best_pre_nms_wrong_class_iou30'] and x['best_pre_nms_wrong_class_iou30']['confidence']>=.35];result={'expected':len(v),'official_vehicle_boxes':sum(len(t[0]['all_final_detections']) for t in bycase.values()),'strict_original_full_3d_projected_box_matched':len(strict),'visible_bbox_iou30_one_to_one_matches':len(alternative),'visible_bbox_only':sorted(alternative-strict),'full_gt_bbox_only':sorted(strict-alternative),'visible_mask_50percent_coverage_without_one_to_one':len(maskcover),'mask_proxy_extra_targets':sorted(set(maskcover)-strict),'low_score_vehicle_iou30_raw_count':len(below),'no_vehicle_iou30_raw_count':sum(x['best_pre_nms_vehicle_iou30'] is None for x in unmatched),'raw_vehicle_iou30_high_score_count':sum(x['raw_vehicle_iou30_above_threshold']>0 for x in unmatched),'raw_high_conf_wrong_class_iou30_count':len(wrong),'unmatched_with_other_vehicle_occlusion_reconstruction':sum(1 for x in v if not x['matched'] and x['visible_fraction_vs_without_other_vehicles'] is not None and x['visible_fraction_vs_without_other_vehicles']<.99),'frames':frame_data}
(P/'recall_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='frames'},ensure_ascii=False,indent=2))
