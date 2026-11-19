"""Run sensor-only tracking on the fixed, synchronized reconstructed sequence.
This script does not open the oracle directory. No output is driving-authorized.
"""
import argparse,json,pathlib,time,types
import numpy as np
from PIL import Image
from integration.rgb_detector import OnnxYoloDetector,_letterbox
from integration.object_tracker import SensorObjectTracker
from integration.target_group_localization import localize_groups
from integration.target_pointcloud_localization import _transform
from tools.pointcloud_p0.replay_io import read,Radar
from tools.pointcloud_p0.target3d_experiment.run_two_samples import choose,normalized
from tools.pointcloud_p0.target3d_experiment.disambiguator import Target3DDisambiguator,TargetObservation,PairObservation
from tools.pointcloud_p0.target_tracking_experiment.tracker import Config,Observation,TargetTracker

def iou(a,b):
 x=max(0,min(a[2],b[2])-max(a[0],b[0]));y=max(0,min(a[3],b[3])-max(a[1],b[1]));inter=x*y
 return inter/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter+1e-12)
def pick(objects,box,cls):
 candidates=[(iou(o.bbox_xyxy_norm,box),o) for o in objects if o.class_name==cls and iou(o.bbox_xyxy_norm,box)>=.3];candidates.sort(key=lambda x:x[0],reverse=True)
 return candidates[0][1] if len(candidates)==1 else None
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);a=ap.parse_args();root=a.root;plan=json.loads((root/'predeclared_plan.json').read_text());manifest=json.loads((root/'capture_manifest.json').read_text());det=OnnxYoloDetector('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx');official_tracker=SensorObjectTracker();tracker=TargetTracker();disamb=Target3DDisambiguator();out=[]
 for frame in manifest['frames']:
  start=time.perf_counter();path=root/'frames'/str(frame);d,lid,rgb,rad,ego,_=read(path);ts=d['sensors']['timestamps'];lid.timestamp=ts['lidar'];rgb.timestamp=ts['rgb'];rad.timestamp=ts['radar'];image=np.array(Image.open(path/'camera.png').convert('RGB'));tensor,tf=_letterbox(image,det._input_width,det._input_height);rawdet=det._session.run(None,{det._input_name:tensor})[0]
  det.confidence_threshold=.35;high0=det._decode(rawdet,tf);det.confidence_threshold=.20;all0=det._decode(rawdet,tf);hi=lambda o:o.confidence>=.35
  signature=lambda oo:sorted((o.class_name,round(o.confidence,8),tuple(round(x,8) for x in o.bbox_xyxy_norm)) for o in oo)
  assert signature(high0)==signature([o for o in all0 if hi(o)]),'formal detections changed'
  formal_objects=[o for o in official_tracker.update(frame,high0) if o.class_name.lower() in {'car','truck','bus'}];low_objects=[types.SimpleNamespace(track_id='AUX-'+str(i),class_name=o.class_name,confidence=o.confidence,bbox_xyxy_norm=o.bbox_xyxy_norm) for i,o in enumerate(all0) if .20<=o.confidence<.35 and o.class_name.lower() in {'car','truck','bus'}]
  formal=localize_groups(formal_objects,lid,rgb,rad,ego);before=normalized(formal);raw=np.frombuffer(lid.raw_data,dtype=np.float32).reshape(-1,4);uv=formal['uv'];cam=_transform(formal['lidar_world'],np.asarray(rgb.transform.get_inverse_matrix()));valid=(cam[:,0]>1)&(formal['lidar_ego'][:,0]>0)&np.isfinite(formal['lidar_ego']).all(axis=1);reserved=np.zeros(len(raw),dtype=bool)
  for o in formal_objects:
   x1,y1,x2,y2=o.bbox_xyxy_norm;reserved|=valid&(uv[:,0]>=x1)&(uv[:,0]<=x2)&(uv[:,1]>=y1)&(uv[:,1]<=y2)
  reserved|=formal['point_state']==1;keep=np.flatnonzero(~reserved);aux_lid=types.SimpleNamespace(raw_data=raw[keep].tobytes(),transform=lid.transform,frame=frame,timestamp=lid.timestamp);empty=Radar(b'',rad.transform,frame);empty.timestamp=rad.timestamp;aux=localize_groups(low_objects,aux_lid,rgb,empty,ego)
  assert normalized(formal)==before and normalized(localize_groups(formal_objects,lid,rgb,rad,ego))==before
  fo=pick(formal_objects,plan['seed_formal_box'],'car');ao=pick(low_objects,plan['seed_aux_box'],'truck');fg=next((g for g in formal['groups'] if fo and fo.track_id in [m['id'] for m in g['members']]),None);ag=next((g for g in aux['groups'] if ao and ao.track_id in [m['id'] for m in g['members']]),None)
  fids=np.asarray(fg['selected_point_indices'] if fg and len(fg['members'])==1 else [],dtype=int);aeligible=keep[np.asarray(ag['nonground_point_indices'],dtype=int)] if ag and len(ag['members'])==1 else np.asarray([],dtype=int);components,amb,selected=choose(formal['lidar_ego'][aeligible],.52);aids=aeligible[np.asarray(selected,dtype=int)];assert not set(fids)&set(aeligible);assert not np.any(reserved[aeligible]);assert len(set(aeligible))==len(aeligible)
  pair=None;metrics={};pair_ok=False
  if fo and ao:
   fobs=TargetObservation(fo.track_id,frame,lid.timestamp,'lidar',tuple(fo.bbox_xyxy_norm),fids.astype(np.int64),raw[fids,:3].astype(float),fids.astype(np.int64));aobs=TargetObservation(ao.track_id,frame,lid.timestamp,'lidar',tuple(ao.bbox_xyxy_norm),aeligible.astype(np.int64),raw[aeligible,:3].astype(float),aids.astype(np.int64));pair=disamb.evaluate(PairObservation(fobs,aobs));metrics=pair.get('current',{});pair_ok=not metrics.get('reasons') and len(fids)>=3 and len(aids)>=3 and metrics.get('nearest_3d_points_m',0)>=Config().min_pairwise_gap_m and metrics.get('radial_interval_gap_m',0)>=Config().min_radial_gap_m
  observations=[]
  for channel,obj,ids in [('formal',fo,fids),('auxiliary',ao,aids)]:
   if obj is None:continue
   xyz=tuple(np.median(formal['lidar_world'][ids],axis=0).tolist()) if len(ids)>=3 else None
   unresolved=(len(ids)>=3 and not pair_ok)
   observations.append(Observation(channel+'-'+str(frame),channel,obj.class_name,obj.confidence,tuple(obj.bbox_xyxy_norm),lid.timestamp,xyz,tuple(int(i) for i in ids),unresolved))
  states=tracker.step(frame,lid.timestamp,observations)
  out.append({'frame':frame,'timestamp':lid.timestamp,'formal_detection_count':len(high0),'formal_box_matched':fo is not None,'aux_box_matched':ao is not None,'formal_result_unchanged':True,'formal_ids':fids.tolist(),'aux_candidate_ids':aeligible.tolist(),'aux_selected_ids':aids.tolist(),'aux_component_sizes':[len(x) for x in components],'aux_cluster_ambiguous':amb,'unique_points':not bool(set(fids)&set(aeligible)),'pair_geometry':metrics,'pair_separation_pass':bool(pair_ok),'states':states,'formal_observation_bbox':list(fo.bbox_xyxy_norm) if fo else None,'aux_observation_bbox':list(ao.bbox_xyxy_norm) if ao else None,'processing_ms':(time.perf_counter()-start)*1000})
  print('FRAME',frame,'formal',len(fids),'aux',len(aeligible),len(aids),'pair',pair_ok,'states',[(x['channel'],x['state']) for x in states],flush=True)
 (root/'frozen_sensor_decisions.json').write_text(json.dumps(out,indent=2)+'\n');print('FROZEN',len(out),flush=True)
if __name__=='__main__':main()
