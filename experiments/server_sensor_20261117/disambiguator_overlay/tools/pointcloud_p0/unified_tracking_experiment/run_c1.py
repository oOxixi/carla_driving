"""Replay actual detections and sensor observations; never opens simulator truth."""
import argparse,json,pathlib,time,types
import numpy as np
from PIL import Image
from integration.rgb_detector import OnnxYoloDetector,_letterbox
from integration.object_tracker import SensorObjectTracker
from integration.target_group_localization import localize_groups
from integration.target_pointcloud_localization import _transform
from tools.pointcloud_p0.replay_io import read,Radar
from tools.pointcloud_p0.target3d_experiment.run_two_samples import normalized
from tools.pointcloud_p0.target3d_experiment.disambiguator import Target3DDisambiguator,TargetObservation,PairObservation
from tools.pointcloud_p0.unified_tracking_experiment.tracker import UnifiedTracker,Observation

def intersection(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);a=ap.parse_args();root=a.root;manifest=json.loads((root/'capture_manifest.json').read_text());det=OnnxYoloDetector('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx');official_tracker=SensorObjectTracker();tracker=UnifiedTracker();disamb=Target3DDisambiguator();out=[]
 for frame in manifest['frames']:
  start=time.perf_counter();path=root/'frames'/str(frame);d,lid,rgb,rad,ego,_=read(path);ts=d['sensors']['timestamps'];lid.timestamp=ts['lidar'];rgb.timestamp=ts['rgb'];rad.timestamp=ts['radar'];image=np.asarray(Image.open(path/'camera.png').convert('RGB'));tensor,tf=_letterbox(image,det._input_width,det._input_height);network=det._session.run(None,{det._input_name:tensor})[0]
  det.confidence_threshold=.35;high0=det._decode(network,tf);det.confidence_threshold=.20;all0=det._decode(network,tf)
  signature=lambda oo:sorted((o.class_name,round(o.confidence,8),tuple(round(x,8) for x in o.bbox_xyxy_norm)) for o in oo)
  assert signature(high0)==signature([o for o in all0 if o.confidence>=.35])
  high=[o for o in official_tracker.update(frame,high0) if o.class_name.lower() in {'car','truck','bus'}];low=[types.SimpleNamespace(track_id='LOW-'+str(i),class_name=o.class_name,confidence=o.confidence,bbox_xyxy_norm=o.bbox_xyxy_norm) for i,o in enumerate(all0) if .20<=o.confidence<.35 and o.class_name.lower() in {'car','truck','bus'}]
  formal=localize_groups(high,lid,rgb,rad,ego);before=normalized(formal);raw=np.frombuffer(lid.raw_data,dtype=np.float32).reshape(-1,4);uv=formal['uv'];cam=_transform(formal['lidar_world'],np.asarray(rgb.transform.get_inverse_matrix()));valid=(cam[:,0]>1)&(formal['lidar_ego'][:,0]>0)&np.isfinite(formal['lidar_ego']).all(axis=1);reserved=np.zeros(len(raw),bool)
  for o in high:
   x1,y1,x2,y2=o.bbox_xyxy_norm;reserved|=valid&(uv[:,0]>=x1)&(uv[:,0]<=x2)&(uv[:,1]>=y1)&(uv[:,1]<=y2)
  reserved|=formal['point_state']==1;keep=np.flatnonzero(~reserved);small=types.SimpleNamespace(raw_data=raw[keep].tobytes(),transform=lid.transform,frame=frame,timestamp=lid.timestamp);empty=Radar(b'',rad.transform,frame);empty.timestamp=rad.timestamp;aux=localize_groups(low,small,rgb,empty,ego)
  assert normalized(formal)==before and normalized(localize_groups(high,lid,rgb,rad,ego))==before
  rows=[]
  for channel,groups,objects in [('formal',formal['groups'],high),('auxiliary',aux['groups'],low)]:
   for group in groups:
    obj=next(o for o in objects if o.track_id==group['representative']);indices=np.asarray(group['selected_point_indices'],dtype=int);indices=indices if channel=='formal' else keep[indices]
    if channel=='auxiliary':assert not np.any(reserved[indices])
    rows.append({'id':channel+'-'+group['group_id']+'-'+str(frame),'channel':channel,'cls':obj.class_name,'confidence':float(obj.confidence),'box':list(obj.bbox_xyxy_norm),'point_ids':indices.tolist(),'members':group['members'],'group_reason':group['reason'],'unresolved':False})
  allids=[i for row in rows for i in row['point_ids']];assert len(allids)==len(set(allids)),'selected points must be unique'
  pair_evidence=[]
  for f in [r for r in rows if r['channel']=='formal']:
   for lowrow in [r for r in rows if r['channel']=='auxiliary']:
    if intersection(f['box'],lowrow['box'])<=0:continue
    def target(r):
     ids=np.asarray(r['point_ids'],dtype=np.int64);return TargetObservation(r['id'],frame,lid.timestamp,'lidar',tuple(r['box']),ids,raw[ids,:3].astype(float),ids)
    pair=disamb.evaluate(PairObservation(target(f),target(lowrow)));m=pair.get('current',{});separated=not m.get('reasons') and len(f['point_ids'])>=3 and len(lowrow['point_ids'])>=3 and m.get('nearest_3d_points_m',0)>=1. and m.get('radial_interval_gap_m',0)>=.5
    if not separated:f['unresolved']=True;lowrow['unresolved']=True
    pair_evidence.append({'formal_id':f['id'],'auxiliary_id':lowrow['id'],'spatially_separated':bool(separated),'metrics':m})
  observations=[]
  for r in rows:
   ids=np.asarray(r['point_ids'],dtype=int);p=tuple(np.median(formal['lidar_world'][ids],axis=0).tolist()) if len(ids)>=3 else None
   r['position_world_surface_proxy']=list(p) if p is not None else None;observations.append(Observation(r['id'],r['channel'],r['cls'],r['confidence'],tuple(r['box']),lid.timestamp,p,tuple(int(i) for i in ids),r['unresolved']))
  states=tracker.step(frame,lid.timestamp,observations);out.append({'frame':frame,'timestamp':lid.timestamp,'detections_formal':len(high),'detections_auxiliary':len(low),'formal_result_unchanged':True,'point_ownership_unique':True,'observations':rows,'cross_channel_evidence':pair_evidence,'tracks':states,'processing_ms':(time.perf_counter()-start)*1000});print('FRAME',frame,'obs',len(rows),'states',[(t['track_id'],t['channel'],t['state']) for t in states if t['state']!='LOST'],flush=True)
 (root/'frozen_sensor_decisions.json').write_text(json.dumps(out,indent=2)+'\n');print('FROZEN',len(out),flush=True)
if __name__=='__main__':main()
