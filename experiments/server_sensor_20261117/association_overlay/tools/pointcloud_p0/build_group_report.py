import collections,json,math,pathlib,itertools,hashlib
import numpy as np
from PIL import Image,ImageDraw
from integration.duplicate_detection_grouper import box_iou
B=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');OUT=B/'pointcloud_p0_diagnosis_20261117/group_acceptance';(OUT/'images').mkdir(parents=True,exist_ok=True)
sets=[('original55','pointcloud_p0_rear_final_20261117','pointcloud_group_regression55_20261117'),('new20','pointcloud_overlap20_raw_20261117','pointcloud_group_regression20_20261117'),('sweep10','pointcloud_overlap_sweep_raw_20261117','pointcloud_group_sweep_20261117'),('focus12','pointcloud_overlap_focus_raw_20261117','pointcloud_group_focus_20261117'),('holdout12','pointcloud_overlap_holdout_raw_20261117','pointcloud_group_holdout_20261117')]
summary={};scenes=[];physical=collections.Counter()
for name,rawname,resultname in sets:
 rawroot=B/rawname;resroot=B/resultname;summary[name]=json.loads((resroot/'summary.json').read_text())
 for f in sorted(resroot.glob('*/*/result.json')):
  result=json.loads(f.read_text());orig=json.loads((rawroot/f.parent.parent.name/f.parent.name/'result.json').read_text());raw=rawroot/f.parent.parent.name/f.parent.name
  scene_id=f'{name}_{orig["case"]}_{orig["repeat"]}';dest=OUT/'images'/f'{scene_id}.png';img=Image.open(raw/'camera.png').convert('RGB');draw=ImageDraw.Draw(img)
  palette=['#55ccff','#ffdc5a','#f582eb','#91ee80','#ffa677']
  for k,g in enumerate(result['groups']):
   for m in g['members']:
    b=[v*s for v,s in zip(m['bbox'],[800,450,800,450])];draw.rectangle(b,outline=palette[k%len(palette)],width=2);draw.text((b[0],max(0,b[1]-12)),g['group_id']+':'+m['id'],fill=palette[k%len(palette)])
  lidar=np.fromfile(raw/'lidar.bin',dtype=np.float32).reshape(-1,4)[:,:3];lw=np.c_[lidar,np.ones(len(lidar))]@np.asarray(orig['lidar_transform']).T;cam=lw@np.linalg.inv(np.asarray(orig['camera_transform'])).T;focal=800/(2*math.tan(math.radians(50)));u=focal*cam[:,1]/np.maximum(cam[:,0],1e-9)+400;v=-focal*cam[:,2]/np.maximum(cam[:,0],1e-9)+225
  status=np.fromfile(f.parent/'point_status.u8',dtype=np.uint8);why=np.fromfile(f.parent/'point_reason.u8',dtype=np.uint8);mask=np.zeros(len(status),dtype=bool)
  for group in result['groups']:
   for m in group['members']:
    x1,y1,x2,y2=m['bbox'];mask|=(cam[:,0]>1)&(u>=x1*800)&(u<=x2*800)&(v>=y1*450)&(v<=y2*450)
  for idx in np.flatnonzero(mask):
   x,y=float(u[idx]),float(v[idx]);color='#33ee7d' if status[idx]==1 else ('#ee65fa' if status[idx]==2 else '#ffae42');rr=2 if status[idx]==1 else 1;draw.ellipse((x-rr,y-rr,x+rr,y+rr),fill=color)
  img.save(dest,optimize=True)
  gt=list(orig['evaluation']['gt_projected_boxes_px'].values());giou=max([box_iou(a,b) for a,b in itertools.combinations(gt,2)] or [0]);det=orig.get('original_yolo_predictions',[]);diou=max([box_iou(a['bbox'],b['bbox']) for a,b in itertools.combinations(det,2)] or [0]);physical[name+'_runs']+=1;physical[name+'_physical_overlap']+=int(giou>0);physical[name+'_physical_overlap_two_matched']+=int(giou>0 and len(orig['evaluation']['matched_roles'])>=2);physical[name+'_real_detection_overlap']+=int(diou>0)
  scenes.append({'set':name,'case':orig['case'],'repeat':orig['repeat'],'frame':orig['frame'],'weather':orig.get('weather'),'lidar_channels':orig['sensors']['channels'],'image':'images/'+scene_id+'.png','original_image':None,'injected_duplicate':orig.get('injected_duplicate'),'expected':len(result['expected_roles']),'baseline_located':len(set(result['baseline_located_roles'])),'located':len(result['located_roles']),'physical_gt_box_iou':giou,'real_detection_iou':diou,'groups':result['groups'],'pair_evidence':result['pair_evidence'],'state_counts':result['point_states'],'truth_counts':result['truth_precision_counts'],'point_recall_numerator':result['recall_numerator'],'point_recall_denominator':result['recall_denominator']})
t1=next(s for s in scenes if s['set']=='original55' and s['case']=='night' and s['repeat']==0);g=next(x for x in t1['groups'] if len(x['members'])>1)
old_exp=json.loads((B/'pointcloud_overlap_study_20261117/results.json').read_text());states=np.fromfile(B/'pointcloud_group_regression55_20261117/night/0/point_status.u8',dtype=np.uint8);t1points=collections.Counter(int(states[p['point_index']]) for p in old_exp['overlap_points'])
adversarial={}
for key,folder in [('before','pointcloud_group_adversarial_20261117/result_before_depth_guard.json'),('after','pointcloud_group_adversarial_20261117/result.json'),('holdout','pointcloud_group_holdout_adversarial_20261117/result.json')]:
 x=json.loads((B/folder).read_text());adversarial[key]={'cases':x['case_count'],'false_merges':x['different_vehicles_merged']}
report={'summary':summary,'scenes':scenes,'physical_counts':dict(physical),'t1':{'group':g,'overlap_point_states':dict(t1points),'point_count':53,'truth_vehicle':35,'truth_environment':18,'earlier_experiment_surface_m':old_exp['results']['C']['objects'][0]['nearest_surface_distance_m']},'adversarial':adversarial,'notes':['Real CARLA images and sensor data; five near-identical duplicate detections deliberately injected into actual YOLO results.','Adversarial stress widened two different real YOLO detections artificially and retained original actor references for audit only.','No verified environmental classifier was supplied: ground-like points remain AMBIGUOUS; ENVIRONMENT is supported but not asserted.','Recall is limited to target-labeled lidar points within matched detections; missed cars excluded.','Ranges measured to horizontal bounding-box surface; historical timestamps are unavailable during replay.','The ground-truth projected boxes and semantic lidar are evaluation-only, not inputs to grouping or localization.']}
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Report ready',len(scenes),'frames',dict(physical),'T1 states',dict(t1points))
