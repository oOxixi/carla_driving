import json,pathlib,sys,math
import numpy as np
from PIL import Image,ImageDraw
from integration.target_group_localization import localize_groups
from integration.target_pointcloud_localization import _transform
R=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');P=R/'pointcloud_adaptive_development_20261117';O=R/'yolo_dual_channel_isolation_20261117';S=R/'yolo_threshold_sensitivity_20261117';sys.path.insert(0,str(P));from eval_helpers import sample_new,truth_labels
cand=json.loads((O/'candidates.json').read_text());prior=json.loads((S/'detections.json').read_text());annotations=json.loads((O/'manual_annotations.json').read_text())['answers'];(O/'identity_images').mkdir(exist_ok=True);records=[]
def coords(obj):return [float(a*b) for a,b in zip(obj.bbox_xyxy_norm,[800,450,800,450])]
def intersection(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
for c in cand:
 case=c['case'];sample=sample_new(P/'new_scenes/holdout'/case);original=np.asarray(Image.open(P/'new_scenes/holdout'/case/'camera.png').convert('RGB'));formal=localize_groups(sample['objects'],sample['lid'],sample['rgb'],sample['rad'],sample['ego']);uv=formal['uv'];ego=formal['lidar_ego'];cam=_transform(formal['lidar_world'],np.asarray(sample['rgb'].transform.get_inverse_matrix()));valid=(cam[:,0]>1)&(ego[:,0]>0)&np.isfinite(ego).all(axis=1);row=next(x for x in prior if x['threshold']==.2 and x['case']==case and x['id']==c['candidate_id']);box=row['bbox_px'];px=uv[:,0]*800;py=uv[:,1]*450;selected=np.flatnonzero(valid&(px>=box[0])&(px<=box[2])&(py>=box[1])&(py<=box[3]));labels=truth_labels(sample);tid=sample['role_ids'][c['matched_role']];lab=labels[selected];target=int(np.count_nonzero(lab==tid));other=int(np.count_nonzero(np.isin(lab,[v for v in sample['role_ids'].values() if v!=tid])));unknown=int(np.count_nonzero(lab==-1));other_or_env=int(len(lab)-target-other-unknown);assert len(selected)==c['raw_box_points_before_isolation'] and target==c['target_points_raw_before_isolation']
 high=[]
 for o in sample['objects']:
  b=coords(o);area=intersection(box,b);hi={'id':o.track_id,'class':o.class_name,'confidence':float(o.confidence),'bbox':b,'overlap_px2':area,'candidate_area_fraction':area/max(1,(box[2]-box[0])*(box[3]-box[1])),'official_area_fraction':area/max(1,(b[2]-b[0])*(b[3]-b[1]))};high.append(hi)
 rawimg=Image.fromarray(original);draw=ImageDraw.Draw(rawimg)
 for h in high:draw.rectangle(h['bbox'],outline='#00f57e',width=2)
 draw.rectangle(box,outline='#ffff00',width=2);key=case+'__'+c['candidate_id'];rawimg.save(O/'identity_images'/(key+'_boxes.png'))
 points=rawimg.copy();draw=ImageDraw.Draw(points)
 for i in selected:
  color='#00cfff' if labels[i]==tid else '#ff49dd' if labels[i] in sample['role_ids'].values() else '#eeeeee' if labels[i]==-1 else '#ff8700';x,y=px[i],py[i];draw.ellipse((x-6,y-6,x+6,y+6),fill='black');draw.ellipse((x-4.5,y-4.5,x+4.5,y+4.5),fill=color,outline='white',width=1)
 view=box.copy()
 for h in high:
  if h['overlap_px2']>0:view=[min(view[0],h['bbox'][0]),min(view[1],h['bbox'][1]),max(view[2],h['bbox'][2]),max(view[3],h['bbox'][3])]
 x1,y1,x2,y2=view;dx=max(24,(x2-x1)*0.8);dy=max(22,(y2-y1)*0.8);rect=(max(0,math.floor(x1-dx)),max(0,math.floor(y1-dy)),min(800,math.ceil(x2+dx)),min(450,math.ceil(y2+dy)));zoom=rawimg.crop(rect);zoom=zoom.resize((zoom.width*3,zoom.height*3),Image.Resampling.NEAREST);zoom.save(O/'identity_images'/(key+'_zoom.png'));pointzoom=points.crop(rect);pointzoom=pointzoom.resize((pointzoom.width*3,pointzoom.height*3),Image.Resampling.NEAREST);pointzoom.save(O/'identity_images'/(key+'_lidar.png'))
 records.append({'case':case,'id':c['candidate_id'],'key':case+' / '+c['candidate_id'],'candidate_class':c['predicted_class'],'confidence':c['confidence'],'candidate_bbox':box,'auto_matched_role':c['matched_role'],'formal_boxes':high,'raw_total':len(selected),'raw_approx_matched_target':target,'raw_approx_other_specified_vehicle':other,'raw_unknown':unknown,'raw_other_or_environment':other_or_env,'after_nonground_total':c['eligible_nonground_points'],'after_nonground_approx_target':c['target_nonground_semantic'],'selected_cluster_points':c['selected_total'],'cluster_reason':c['group_reason'],'previous_manual':annotations[case+' / '+c['candidate_id']],'image_id':key})
(O/'identity_evidence.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n');print('prepared',len(records),'cases',len({x['case'] for x in records}));
for x in records:print(x['case'],x['id'],'overlap',[(h['id'],round(h['candidate_area_fraction'],2),round(h['official_area_fraction'],2)) for h in x['formal_boxes'] if h['overlap_px2']>0],'raw labels',x['raw_total'],x['raw_approx_matched_target'],x['raw_approx_other_specified_vehicle'],x['raw_other_or_environment'],x['raw_unknown'])
