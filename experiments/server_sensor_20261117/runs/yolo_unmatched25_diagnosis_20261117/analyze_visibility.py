import collections,csv,json,math,pathlib,numpy as np
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/yolo_unmatched25_diagnosis_20261117');d=json.loads((P/'diagnosis.json').read_text());data={x.stem:json.loads(x.read_text()) for x in (P/'visibility_cases').glob('*.json')};assert len(data)==21
rows=[]
def coverage(mask,box):
 x1=max(0,int(math.floor(box[0])));y1=max(0,int(math.floor(box[1])));x2=min(800,int(math.ceil(box[2])));y2=min(450,int(math.ceil(box[3])));n=int(mask[y1:y2,x1:x2].sum()) if x2>x1 and y2>y1 else 0;area=max(0,x2-x1)*max(0,y2-y1);return {'target_pixels_inside':n,'target_pixel_coverage':n/int(mask.sum()) if mask.sum() else None,'fraction_box_pixels_target':n/area if area else None}
for r in d['all_target_rows']:
 v=data[r['case']];arr=np.fromfile(P/'reconstructed'/f"{r['case']}_full_instance.bgra",dtype=np.uint8).reshape(450,800,4);ids=arr[:,:,0].astype(np.uint32)*256+arr[:,:,1].astype(np.uint32);tag=arr[:,:,2];instance=v['full_visible'][r['role']]['actor_id']%65536;mask=(ids==instance)&np.isin(tag,[14,15,16]);assert int(mask.sum())==v['full_visible'][r['role']]['visible_pixels']
 final=[]
 for box in r['all_final_detections']:
  a=coverage(mask,box['bbox_px']);others={}
  for role,z in v['full_visible'].items():
   if role!=r['role']:
    masko=(ids==z['actor_id']%65536)&np.isin(tag,[14,15,16]);others[role]=coverage(masko,box['bbox_px'])
  final.append({'id':box['id'],'class':box['class'],'confidence':box['confidence'],'target':a,'others':others})
 raw=r['best_pre_nms_vehicle_iou30'];rawcover=coverage(mask,raw['box_px']) if raw else None
 best=max(final,key=lambda z:z['target']['target_pixels_inside']) if final else None
 rows.append({'case':r['case'],'frame':r['frame'],'role':r['role'],'matched':r['matched'],'class_category':r['class_category'],'visible_pixels_reconstructed':int(mask.sum()),'solo_pixels_reconstructed':v['solo_visible'][r['role']]['visible_pixels'],'visible_fraction_vs_without_other_vehicles':v['visibility_ratio'][r['role']],'whole_image_reconstruction_mae':v['rgb_original_vs_reconstruction_mae_0_255'],'gt_projection_error_px':v['box_projection_max_delta_px'][r['role']],'best_final_mask_support':best,'best_low_confidence_candidate_mask_support':rawcover})
assert len(rows)==35 and sum(not x['matched'] for x in rows)==25
(P/'visible_mask_audit.json').write_text(json.dumps({'rows':rows,'note':'Instance masks captured in a newly reconstructed static scene, not original RGB capture. Full scene compared to same target without other spawned vehicles; environment occlusion remains. Pixel overlap is geometric support, not a standalone detection verdict.'},ensure_ascii=False,indent=2)+'\n')
for r in rows:
 if not r['matched']:
  b=r['best_final_mask_support'];raw=r['best_low_confidence_candidate_mask_support'];print(r['case'],r['role'],'visible',r['visible_pixels_reconstructed'],'ratio',round(r['visible_fraction_vs_without_other_vehicles'],2) if r['visible_fraction_vs_without_other_vehicles'] is not None else None,'final',round(b['target']['target_pixel_coverage'],2) if b and b['target']['target_pixel_coverage'] is not None else None,'other', {k:round(v['target_pixel_coverage'],2) if v['target_pixel_coverage'] is not None else None for k,v in b['others'].items()} if b else {},'raw',round(raw['target_pixel_coverage'],2) if raw and raw['target_pixel_coverage'] is not None else None)
