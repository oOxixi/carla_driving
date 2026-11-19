"""Evaluate frozen C1 sensor-only outputs against isolated simulator truth."""
import argparse,json,pathlib,collections,math
import numpy as np
from tools.pointcloud_p0.replay_io import read
from tools.pointcloud_p0.target3d_experiment.run_two_samples import audit_semantic
from integration.target_pointcloud_localization import _transform

def iou(a,b):
 inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));return inter/max((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter,1e-12)
def box_project(vertices,camera):
 q=np.c_[np.array(vertices),np.ones(8)]@np.linalg.inv(camera).T
 if np.any(q[:,0]<=1):return None
 f=800/(2*math.tan(math.radians(100)/2));u=(f*q[:,1]/q[:,0]+400)/800;v=(-f*q[:,2]/q[:,0]+225)/450
 return [float(u.min()),float(v.min()),float(u.max()),float(v.max())]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);a=ap.parse_args();root=a.root;frozen=json.loads((root/'frozen_sensor_decisions.json').read_text());truths=[]
 for row in frozen:
  p=root/'oracle'/str(row['frame'])/'truth.json';truths.append(json.loads(p.read_text()))
 history={'front':[],'adjacent':[]};track_role_history=collections.defaultdict(list);perframe=[];confirmed_semantic_mixed=0;confirmed_unverified=0;selected_semantic_mixed=0
 for fi,(row,truth) in enumerate(zip(frozen,truths)):
  frame=row['frame'];path=root/'frames'/str(frame);oracle=root/'oracle'/str(frame);d,lid,rgb,rad,ego,_=read(path);d['semantic_transform']=truth['semantic_transform'];raw=np.frombuffer(lid.raw_data,dtype=np.float32).reshape(-1,4);world=_transform(raw[:,:3],np.asarray(d['lidar_transform']));observations=row['observations'];roles=['front','adjacent'];boxes=[box_project(truth['actors'][r]['vertices_world'],np.asarray(d['camera_transform'])) for r in roles];scores=np.array([[iou(o['box'],b) if b is not None else 0 for b in boxes] for o in observations]).reshape((len(observations),len(roles)));assignment={}
  # Two truth roles: exhaustive one-to-one maximum-cardinality, then maximum IoU.
  best=(-1,-1.);choices=[None,*range(len(observations))]
  for x in choices:
   for y in choices:
    if x is not None and x==y:continue
    pairs=[(roles[0],x,0),(roles[1],y,1)]
    if any(k is not None and scores[k,j]<.3 for _,k,j in pairs):continue
    value=(sum(k is not None for _,k,_ in pairs),sum(float(scores[k,j]) for _,k,j in pairs if k is not None))
    if value>best:best=value;assignment={r:int(k) for r,k,j in pairs if k is not None}
  tracks={t['observation_id']:t for t in row['tracks'] if t['observation_id'] is not None};ids=sorted({i for o in observations for i in o['point_ids']});labels=audit_semantic(oracle,d,world,ids) if ids else {};actorids={v['actor_id']:k for k,v in truth['actors'].items()};frame_rows={}
  for role in roles:
   box=boxes[roles.index(role)];visible=bool(box and box[2]>0 and box[0]<1 and box[3]>0 and box[1]<1);index=assignment.get(role);o=observations[index] if index is not None else None;mapped_track=tracks.get(o['id']) if o else None;t=mapped_track if mapped_track and mapped_track['state'] not in ('AMBIGUOUS','LOST') else None;points=o['point_ids'] if o else [];labels_for=[labels.get(i,{}).get('id') for i in points];same=sum(i==truth['actors'][role]['actor_id'] for i in labels_for);other=sum(i in actorids and actorids[i]!=role for i in labels_for);unknown=sum(i is None for i in labels_for);environment=len(points)-same-other-unknown
   if other:selected_semantic_mixed+=1
   if t and t['state']=='CONFIRMED_TRACK':
    if other:confirmed_semantic_mixed+=1
    if not points or unknown==len(points):confirmed_unverified+=1
   velocity=None
   if fi>0:
    prev=np.array(truths[fi-1]['actors'][role]['center_world']);current=np.array(truth['actors'][role]['center_world']);velocity=(current-prev)/(row['timestamp']-frozen[fi-1]['timestamp'])
   proxy=np.array(t['position_world_surface_proxy']) if t and t['position_world_surface_proxy'] is not None else None;estvel=np.array(t['velocity_world_surface_proxy']) if t and t['velocity_world_surface_proxy'] is not None else None
   entry={'visible':visible,'detected':o is not None,'channel':o['channel'] if o else None,'observation_id':o['id'] if o else None,'track_id':t['track_id'] if t else None,'state':t['state'] if t else None,'iou':float(scores[index,roles.index(role)]) if o else None,'selected_points':len(points),'semantic_target_approx':same,'semantic_other_actor_approx':other,'semantic_environment_approx':environment,'semantic_unknown':unknown,'surface_proxy_to_center_m':float(np.linalg.norm(proxy-np.array(truth['actors'][role]['center_world']))) if proxy is not None else None,'velocity_vector_error_mps':float(np.linalg.norm(estvel-velocity)) if estvel is not None and velocity is not None else None}
   history[role].append(entry);frame_rows[role]=entry
   if t:track_role_history[t['track_id']].append((fi,role,t['state']))
  perframe.append({'frame':frame,'roles':frame_rows})
 summary={};channel_events=[]
 for role,events in history.items():
  tracked=[(i,e) for i,e in enumerate(events) if e['track_id'] is not None];switches=sum(a[1]['track_id']!=b[1]['track_id'] for a,b in zip(tracked,tracked[1:]));fragments=sum(b[0]>a[0]+1 for a,b in zip(tracked,tracked[1:]));first=tracked[0][0] if tracked else None;conf=next((i for i,e in enumerate(events) if e['state']=='CONFIRMED_TRACK'),None)
  position=[e['surface_proxy_to_center_m'] for e in events if e['surface_proxy_to_center_m'] is not None];speed=[e['velocity_vector_error_mps'] for e in events if e['velocity_vector_error_mps'] is not None];points=sum(e['selected_points'] for e in events);correct=sum(e['semantic_target_approx'] for e in events)
  for i in range(1,len(events)):
   prev,cur=events[i-1],events[i]
   if prev['detected'] and cur['detected'] and prev['channel']!=cur['channel']:
    outcome='unassessable' if not prev['track_id'] or not cur['track_id'] else 'preserved' if prev['track_id']==cur['track_id'] else 'changed'
    channel_events.append({'role':role,'from_frame':frozen[i-1]['frame'],'to_frame':frozen[i]['frame'],'from':prev['channel'],'to':cur['channel'],'outcome':outcome})
  summary[role]={'visible_frames':sum(e['visible'] for e in events),'detection_matched_frames':sum(e['detected'] for e in events),'track_matched_frames':len(tracked),'track_continuity_visible_fraction':len(tracked)/sum(e['visible'] for e in events) if sum(e['visible'] for e in events) else None,'id_switches_across_matches':switches,'fragmentation_gaps':fragments,'track_ids':sorted({e['track_id'] for _,e in tracked}),'confirmation_frame':frozen[conf]['frame'] if conf is not None else None,'confirmation_latency_frames_from_first_matched':conf-first+1 if conf is not None and first is not None else None,'confirmed_matched_frames':sum(e['state']=='CONFIRMED_TRACK' for e in events),'point_precision_conservative':correct/points if points else None,'selected_points':points,'semantic_target_approx':correct,'position_surface_proxy_vs_actor_center_p95_m':float(np.percentile(position,95)) if position else None,'position_surface_proxy_vs_actor_center_max_m':max(position) if position else None,'position_samples':len(position),'velocity_error_p50_mps':float(np.percentile(speed,50)) if speed else None,'velocity_error_p95_mps':float(np.percentile(speed,95)) if speed else None,'velocity_error_max_mps':max(speed) if speed else None,'velocity_samples':len(speed)}
 identity_conflicts=[]
 for tid,entries in track_role_history.items():
  for prev,cur in zip(entries,entries[1:]):
   if prev[1]!=cur[1]:identity_conflicts.append({'track_id':tid,'from_frame':frozen[prev[0]]['frame'],'from_role':prev[1],'to_frame':frozen[cur[0]]['frame'],'to_role':cur[1],'state':cur[2]})
 matched_obs={e['observation_id'] for events in history.values() for e in events if e['observation_id']};unmatched_confirmed=sum(1 for r in frozen for t in r['tracks'] if t['state']=='CONFIRMED_TRACK' and t['observation_id'] not in matched_obs)
 result={'frames':len(frozen),'per_target':summary,'channel_transition_events':channel_events,'channel_transition_counts':dict(collections.Counter(x['outcome'] for x in channel_events)),'track_id_changes_physical_actor':identity_conflicts,'observed_semantic_other_vehicle_mixed_count':selected_semantic_mixed,'confirmed_with_other_vehicle_points_count':confirmed_semantic_mixed,'confirmed_semantic_unverified_count':confirmed_unverified,'confirmed_without_iou_actor_match_count':unmatched_confirmed,'formal_chain_unchanged_frames':sum(r['formal_result_unchanged'] for r in frozen),'unique_point_ownership_frames':sum(r['point_ownership_unique'] for r in frozen),'all_track_ids':sorted({t['track_id'] for r in frozen for t in r['tracks']}),'all_confirmed_frames':sum(t['state']=='CONFIRMED_TRACK' for r in frozen for t in r['tracks']),'may_enter_follow_count':sum(t['may_enter_follow'] for r in frozen for t in r['tracks']),'match_method':'post-freeze 2D projected actor box IoU >=0.30, one-to-one; ambiguous tracks not considered valid identity; semantic LiDAR approximate 8cm nearest point','velocity_truth':'successive simulator actor center differences / frame time; surface-proxy velocity is not vehicle center speed','position_note':'surface proxy distance to actor center is not a vehicle-center position error and includes physical surface-to-center offset','C1_gate_note':'C1 is not automatically passed; research parameters and observed metrics require review; no transition means channel migration not tested'}
 (root/'offline_audit.json').write_text(json.dumps(perframe,indent=2)+'\n');(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
