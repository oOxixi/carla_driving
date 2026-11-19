'''Offline formal detector/tracker and all group output fields, before/after isolated auxiliary processing.'''
import ast,hashlib,json,pathlib,sys,types
import numpy as np
from PIL import Image
from integration.rgb_detector import OnnxYoloDetector,_letterbox
from integration.object_tracker import SensorObjectTracker
from integration.target_group_localization import localize_groups
from integration.target_pointcloud_localization import _transform
from tools.pointcloud_p0.replay_io import Radar
R=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');P=R/'pointcloud_adaptive_development_20261117';D=R/'yolo_dual_channel_isolation_20261117';O=R/'candidate_local_cluster_recovery_20261117';OLD=R/'yolo_threshold_sensitivity_20261117';sys.path.insert(0,str(P));from eval_helpers import sample_new
model=pathlib.Path('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx');det=OnnxYoloDetector(model);assert det.confidence_threshold==.35 and det.iou_threshold==.45
prior=[x for x in json.loads((OLD/'detections.json').read_text()) if x['threshold']==.2];cases=sorted({x['case'] for x in json.loads((O/'cases.json').read_text())});expected_clusters=json.loads((O/'clusters.json').read_text());nodes=ast.parse((O/'run_local_cluster.py').read_text()).body;tree=ast.Module(body=[next(n for n in nodes if isinstance(n,ast.FunctionDef) and n.name=='comps')],type_ignores=[]);scope={'np':np};exec(compile(tree,'cluster_geometry','exec'),scope);comps=scope['comps'];aud=[]
def detection(img,frame):
 tensor,tf=_letterbox(img,det._input_width,det._input_height);raw=det._session.run(None,{det._input_name:tensor})[0];return [o for o in SensorObjectTracker().update(frame,det._decode(raw,tf)) if o.class_name in ('car','truck','bus')]
def sig(o):return {'id':o.track_id,'class':o.class_name,'confidence':round(float(o.confidence),7),'bbox':[round(float(v),7) for v in o.bbox_xyxy_norm]}
def normalized(loc):
 def convert(x):
  if isinstance(x,np.ndarray):return {'dtype':str(x.dtype),'shape':list(x.shape),'sha256':hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()}
  if isinstance(x,(np.floating,np.integer)):return x.item()
  if isinstance(x,dict):return {str(k):convert(v) for k,v in x.items()}
  if isinstance(x,(list,tuple)):return [convert(v) for v in x]
  return x
 return convert(loc)
for case in cases:
 s=sample_new(P/'new_scenes/holdout'/case);d=s['d'];img=np.asarray(Image.open(P/'new_scenes/holdout'/case/'camera.png').convert('RGB'));f=d['frame'];before_det=detection(img,f);saved=d['predictions'];assert len(before_det)==len(saved)
 for o,r in zip(before_det,saved):assert o.track_id==r['id'] and o.class_name==r['class'] and abs(o.confidence-r['confidence'])<1e-5 and np.max(np.abs(np.asarray(o.bbox_xyxy_norm)-np.asarray(r['bbox'])))<1e-5
 before=localize_groups(before_det,s['lid'],s['rgb'],s['rad'],s['ego']);baseline=normalized(before);raw=np.frombuffer(s['lid'].raw_data,dtype=np.float32).reshape(-1,4);uv=before['uv'];cam=_transform(before['lidar_world'],np.asarray(s['rgb'].transform.get_inverse_matrix()));valid=(cam[:,0]>1)&(before['lidar_ego'][:,0]>0)&np.isfinite(before['lidar_ego']).all(axis=1);reserved=np.zeros(len(raw),bool)
 for o in before_det:
  x1,y1,x2,y2=o.bbox_xyxy_norm;reserved|=valid&(uv[:,0]>=x1)&(uv[:,0]<=x2)&(uv[:,1]>=y1)&(uv[:,1]<=y2)
 reserved|=(before['point_state']==1);keep=np.flatnonzero(~reserved);auxlid=types.SimpleNamespace(raw_data=raw[keep].tobytes(),transform=s['lid'].transform,frame=s['lid'].frame,timestamp=s['lid'].timestamp);rad=Radar(b'',s['rad'].transform,s['rad'].frame);rad.timestamp=s['rad'].timestamp
 lows=[r for r in prior if r['case']==case and r['low_confidence_candidate']];objs=[types.SimpleNamespace(track_id=r['id'],class_name=r['class'],confidence=r['confidence'],bbox_xyxy_norm=[v/q for v,q in zip(r['bbox_px'],[800,450,800,450])]) for r in lows];aux=localize_groups(objs,auxlid,s['rgb'],rad,s['ego'])
 for expected in [x for x in expected_clusters if x['case']==case]:
  group=next(g for g in aux['groups'] if expected['candidate'] in [m['id'] for m in g['members']]);ix=np.asarray(group['nonground_point_indices'],dtype=int);xyz=aux['lidar_ego'][ix];components=comps(xyz,expected['radius_m']);eligible=[c for c in components if len(c)>=3 and np.all(np.ptp(xyz[c],axis=0)<=np.asarray([6.5,3.5,3.]))];ambiguous=len(eligible)>1 and len(eligible[1])>=.67*len(eligible[0]);chosen=[] if not eligible or ambiguous else sorted((eligible[0]+1).tolist());assert chosen==sorted(expected['chosen_point_nos'])
 assert normalized(before)==baseline;after_det=detection(img,f);assert [sig(x) for x in before_det]==[sig(x) for x in after_det];after=localize_groups(after_det,s['lid'],s['rgb'],s['rad'],s['ego']);assert normalized(after)==baseline
 assert all(not np.any(reserved[keep[np.asarray(g['selected_point_indices'],dtype=int)]]) for g in aux['groups'])
 aud.append({'case':case,'formal_detector_boxes':len(before_det),'aux_boxes':len(objs),'formal_yolo_and_tracker_equal':True,'formal_group_all_fields_equal':True,'local_cluster_recovery_exercised':True,'original_formal_group_not_mutated':True,'formal_selected_or_reserved_points_not_in_aux':True});print('PASS',case,'formal',len(before_det),'aux',len(objs),flush=True)
(O/'formal_chain_audit.json').write_text(json.dumps({'frames':aud,'scope':'same saved frames; offline YOLO 0.35, tracker, entire localize_groups return; excludes lane, FOLLOW, policy, runtime and dynamic scenarios','model_sha256':hashlib.sha256(model.read_bytes()).hexdigest()},indent=2)+'\n');print('PASS formal pipeline',len(aud),'frames; lane and control not tested')
