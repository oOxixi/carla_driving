"""Offline diagnostic of frozen recordings; does not call or change localization."""
import json,math,collections,pathlib,hashlib
import numpy as np, carla
from PIL import Image
ROOT=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_p0_rear_final_20261117')
OUT=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_p0_diagnosis_20261117')
SEM=np.dtype([('x','<f4'),('y','<f4'),('z','<f4'),('cos','<f4'),('id','<u4'),('tag','<u4')])
client=carla.Client('127.0.0.1',22170);client.set_timeout(15);mp=client.get_world().get_map()
assert 'Town05' in mp.name,mp.name
fail=[];located=[];sync=[];poses={};projection=[]
def qstats(vals):
 a=np.asarray(vals,dtype=float)
 return {'n':len(a),'signed_median':float(np.median(a)),'absolute_median':float(np.percentile(np.abs(a),50)),'absolute_p95':float(np.percentile(np.abs(a),95))} if len(a) else None
for f in sorted(ROOT.glob('*/*/result.json')):
 d=json.loads(f.read_text()); ev=d['evaluation'];s=d['sensors'];ego=np.asarray(d['ego_transform']);camera=np.asarray(d['camera_transform']);lidar=np.asarray(d['lidar_transform']);radar=np.asarray(d['radar_transform']);sem_tf=np.asarray(d['semantic_transform'])
 sync.append({'case':d['case'],'repeat':d['repeat'],'frame':d['frame'],'frames_equal':len({d['frame'],s['rgb_frame'],s['lidar_frame'],s['radar_frame'],s['semantic_frame']})==1})
 poses[f'{d["case"]}/{d["repeat"]}']={k:(np.linalg.inv(ego)@m).tolist() for k,m in [('camera',camera),('lidar',lidar),('radar',radar),('semantic',sem_tf)]}
 width,height=Image.open(f.parent/'camera.png').size;assert (width,height)==(800,450)
 focal=width/(2*math.tan(math.radians(100)/2))
 sem=np.fromfile(f.parent/'semantic_lidar.bin',dtype=SEM)
 xyz=np.column_stack([sem['x'],sem['y'],sem['z']]);world=(np.c_[xyz,np.ones(len(xyz))]@sem_tf.T);cam=world@np.linalg.inv(camera).T;dep=cam[:,0];u=focal*cam[:,1]/np.maximum(dep,1e-9)+width/2;v=-focal*cam[:,2]/np.maximum(dep,1e-9)+height/2
 for role,actor_id in ev['gt_actor_ids'].items():
  mask=(sem['id']==actor_id)&(dep>1)&(u>=0)&(u<width)&(v>=0)&(v<height);box=ev['gt_projected_boxes_px'].get(role)
  if box:
   x1,y1,x2,y2=box;inside=mask&(u>=x1)&(u<=x2)&(v>=y1)&(v<=y2)
   projection.append({'case':d['case'],'repeat':d['repeat'],'role':role,'visible_sem_points':int(mask.sum()),'inside_projected_gt_box':int(inside.sum())})
 predictions={x['id']:x for x in d['predictions']};entries={x['id']:x for x in ev['detections']}
 for role in ev['unmatched_roles']:
  fail.append({'case':d['case'],'repeat':d['repeat'],'role':role,'prediction_id':None,'primary':'检测未匹配','reason':'DETECTION_MISS','explanation':'没有与该真值车辆匹配的检测框；IoU 一对一阈值 0.3。','box':None,'nonground':None,'radar_box_exclusive_count':None,'clusters':None,'flags':['检测未匹配']})
 for ident,e in entries.items():
  if not e['gt_match']:continue
  o=predictions[ident];role=e['gt_match']['role']
  if o['status']=='LOCATED_UNVALIDATED':
   est=np.asarray(o['cluster_center_ego']);est_world=(ego@np.array([est[0],-est[1],est[2],1]))[:3];gt=np.asarray(e['gt']['center_world']);w=mp.get_waypoint(carla.Location(x=float(gt[0]),y=float(gt[1]),z=float(gt[2])),project_to_road=True,lane_type=carla.LaneType.Driving)
   if w is None or w.is_junction:raise RuntimeError('Road direction unavailable')
   vec=w.transform.get_forward_vector();norm=math.hypot(vec.x,vec.y);forward=np.array([vec.x/norm,vec.y/norm]);left=np.array([vec.y/norm,-vec.x/norm]);dif=est_world-gt
   located.append({'case':d['case'],'repeat':d['repeat'],'role':role,'id':ident,'road_id':w.road_id,'lane_id':w.lane_id,'road_yaw':w.transform.rotation.yaw,'longitudinal_m':float(dif[:2]@forward),'lateral_left_m':float(dif[:2]@left),'vertical_m':float(dif[2]),'center_3d_m':float(np.linalg.norm(dif)),'nearest_surface_range_m':e['errors']['nearest_surface_range_error_m'],'points':o['cluster_count']})
  else:
   reason=o['reason'];b=e['box'];ng=e['nonground'];exclusive=set(o['exclusive_point_indices']);box=set(o['box_point_indices']);ngidx=set(o['nonground_point_indices']);flags=[]
   if b['total']==0:flags.append('框内无点')
   if len(ngidx)<3:flags.append('筛选后少于3点')
   ground_remaining=sum(ng['tag_counts'].get(str(i),0) for i in (1,2,24,25))
   other_remaining=ng['other_or_environment'];other_vehicle=ng['other_test_vehicle']
   if ground_remaining:flags.append('筛选后有地面类别点')
   if other_remaining:flags.append('筛选后有环境点')
   if other_vehicle:flags.append('筛选后有其他测试车点')
   if not o['radar_box_exclusive_count']:flags.append('框内无独占Radar点')
   if len(o['clusters'])>1:flags.append('多个候选点簇')
   if reason=='INSUFFICIENT_LIDAR_POINTS':primary='筛选后点数不足';explain='进入聚类的点少于3个；需区分原始点少和重叠框剔除。'
   elif reason=='NO_PLAUSIBLE_CLUSTER':primary='未形成可用点簇';explain='至少3点但没有满足当前连接与尺寸条件的点簇；不能仅凭状态认定是背景造成。'
   elif reason=='MULTIPLE_PLAUSIBLE_CLUSTERS':primary='多个点簇无法区分';explain='多个候选簇满足当前拒绝规则；是否跨车混淆须结合真值。'
   else:primary='其他或待确认';explain=reason
   fail.append({'case':d['case'],'repeat':d['repeat'],'role':role,'prediction_id':ident,'primary':primary,'reason':reason,'explanation':explain,'box':b,'nonground':ng,'exclusive_points':len(exclusive),'removed_by_overlap':len(box-exclusive),'removed_by_height':len(exclusive-ngidx),'radar_box_exclusive_count':o['radar_box_exclusive_count'],'clusters':o['clusters'],'flags':flags,'semantic_iou':e['gt_match']['iou'],'ground_remaining':ground_remaining,'other_vehicle_remaining':other_vehicle,'other_environment_remaining':other_remaining})
assert len(fail)==49 and len(located)==121 and len(sync)==55 and all(r['frames_equal'] for r in sync)
counts=collections.Counter(x['primary'] for x in fail);flags=collections.Counter(flag for x in fail for flag in x['flags'])
metrics={k:qstats([r[k] for r in located]) for k in ('longitudinal_m','lateral_left_m','vertical_m','center_3d_m','nearest_surface_range_m')}
proj_sum=sum(r['visible_sem_points'] for r in projection);inside_sum=sum(r['inside_projected_gt_box'] for r in projection)
summary={'source':str(ROOT),'map':mp.name,'sample_count':len(located),'failure_count':len(fail),'metrics':metrics,'failure_status_counts':dict(counts),'failure_flags_overlapping':dict(flags),'failure_rows':fail,'located_rows':located,'sync_frames_all_equal':all(r['frames_equal'] for r in sync),'timestamps_note':'RGB/LiDAR/Radar at runtime checked <=1 ms by localize; raw timestamps not persisted, semantic timestamp not checked independently. Cannot reconstruct actual time deltas.','camera':{'width':800,'height':450,'fov_degrees_from_runner':100,'fx_fy_pixels':focal,'cx_pixels':400,'cy_pixels':225,'runtime_attributes_not_saved':True},'relative_poses_first':next(iter(poses.values())),'relative_poses_max_variation':{k:float(max(np.max(np.abs(np.asarray(p[k])-np.asarray(next(iter(poses.values()))[k]))) for p in poses.values())) for k in ('camera','lidar','radar','semantic')},'semantic_projected_box_check':{'visible_car_points':proj_sum,'inside_gt_box':inside_sum,'ratio':inside_sum/proj_sum if proj_sum else None,'note':'GT bounding boxes and semantic points projected with the same camera transform and intrinsics; internal consistency only, not independent calibration accuracy.'},'source_code_sha256':{name:hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() for name in ('integration/target_pointcloud_localization.py','tools/pointcloud_p0/run_matrix.py')},'limitations':['Point-cluster median is visible surface, not inferred vehicle center.','Road tangent at ground-truth target waypoint; local straight-road approximation, not full curvilinear s/d.','Radar truth not saved per failed detection; no reliable attribution of radar cause.','Offline semantic labels use 0.08 m nearest-neighbor association; not independent physical calibration.','Coordinates of unlocated target truth and per-sensor timestamps were not saved.']}
OUT.mkdir(parents=True,exist_ok=True);(OUT/'diagnosis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:summary[k] for k in ('sample_count','failure_count','metrics','failure_status_counts','failure_flags_overlapping','camera','relative_poses_max_variation','semantic_projected_box_check')},ensure_ascii=False,indent=2))
