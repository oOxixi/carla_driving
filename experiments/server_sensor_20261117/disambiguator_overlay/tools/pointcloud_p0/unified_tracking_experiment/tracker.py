"""Provisional sensor-only tracking. No simulator truth or driving authority."""
from dataclasses import dataclass,field
from collections import deque
import math
import numpy as np

@dataclass(frozen=True)
class Config:
 window:int=5
 confirm_observations:int=3
 max_missed:int=3
 max_dt:float=.20
 max_image_center_shift:float=.10
 max_position_shift_m:float=2.0
 max_mahalanobis:float=16.27
 max_surface_speed_mps:float=25.0
 measurement_std_m:float=.40
 acceleration_std_mps2:float=2.0

@dataclass(frozen=True)
class Observation:
 id:str
 channel:str
 cls:str
 confidence:float
 box:tuple
 timestamp:float
 position:tuple|None
 point_ids:tuple=()
 unresolved:bool=False

@dataclass
class Track:
 id:str
 cls:str
 channel:str
 box:tuple
 mean:object=None
 covariance:object=None
 last_3d_timestamp:float|None=None
 last_3d_position:object=None
 history:deque=field(default_factory=lambda:deque(maxlen=5))
 missed:int=0
 state:str='VISUAL_ONLY'
 reason:str=''
 obs_id:str|None=None
 migrations:int=0
 velocity_measurements:int=0

class UnifiedTracker:
 def __init__(self,config=Config()):
  if config.window!=5 or config.confirm_observations!=3 or config.max_missed<1:raise ValueError('invalid configuration')
  self.c=config;self.tracks={};self.next_id=1;self.last_frame=None;self.last_time=None
 @staticmethod
 def center(b):return np.array([(b[0]+b[2])/2,(b[1]+b[3])/2])
 @staticmethod
 def boxes_overlap(a,b):
  return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
 @staticmethod
 def validate(o):
  b=np.asarray(o.box,float)
  if not o.id or o.channel not in ('formal','auxiliary') or not o.cls or not math.isfinite(o.timestamp) or not math.isfinite(o.confidence) or b.shape!=(4,) or not np.isfinite(b).all() or b[0]>=b[2] or b[1]>=b[3]:raise ValueError('invalid observation')
  if len(o.point_ids)!=len(set(o.point_ids)):raise ValueError('duplicate IDs within observation')
  if o.position is not None and (len(o.point_ids)<3 or np.asarray(o.position).shape!=(3,) or not np.isfinite(o.position).all()):raise ValueError('invalid 3D observation')
 def predict(self,t,dt):
  if t.mean is None:return
  F=np.eye(6);F[:3,3:]=np.eye(3)*dt;G=np.vstack((np.eye(3)*.5*dt**2,np.eye(3)*dt));t.mean=F@t.mean;t.covariance=F@t.covariance@F.T+G@G.T*self.c.acceleration_std_mps2**2
 def match(self,t,o):
  c=self.c
  if t.cls!=o.cls or not self.boxes_overlap(t.box,o.box) or np.linalg.norm(self.center(t.box)-self.center(o.box))>c.max_image_center_shift:return False
  if t.channel!=o.channel and (t.mean is None or o.position is None or o.unresolved):return False
  if t.mean is not None and o.position is not None:
   d=np.asarray(o.position)-t.mean[:3];S=t.covariance[:3,:3]+np.eye(3)*c.measurement_std_m**2
   if np.linalg.norm(d)>c.max_position_shift_m or float(d@np.linalg.solve(S,d))>c.max_mahalanobis:return False
   delta=o.timestamp-t.last_3d_timestamp
   if delta<=0 or np.linalg.norm(np.asarray(o.position)-t.last_3d_position)/delta>c.max_surface_speed_mps:return False
  return True
 def update(self,t,o):
  if o.position is None:return
  z=np.asarray(o.position,float);R=np.eye(3)*self.c.measurement_std_m**2
  if t.mean is None:t.mean=np.r_[z,np.zeros(3)];t.covariance=np.diag([.64,.64,.64,25.,25.,25.])
  else:
   H=np.hstack((np.eye(3),np.zeros((3,3))));S=H@t.covariance@H.T+R;K=t.covariance@H.T@np.linalg.inv(S);t.mean=t.mean+K@(z-H@t.mean);I=np.eye(6)-K@H;t.covariance=I@t.covariance@I.T+K@R@K.T
  t.last_3d_timestamp=o.timestamp;t.last_3d_position=z.copy();t.velocity_measurements+=1
 def step(self,frame,timestamp,observations):
  if not isinstance(frame,int) or not math.isfinite(timestamp) or (self.last_frame is not None and (frame<=self.last_frame or timestamp<=self.last_time)):raise ValueError('frame/time must strictly increase')
  for o in observations:
   self.validate(o)
   if abs(o.timestamp-timestamp)>.001:raise ValueError('timestamp mismatch')
  if len({o.id for o in observations})!=len(observations):raise ValueError('duplicate observation ID')
  dt=0 if self.last_time is None else timestamp-self.last_time;skipped=0 if self.last_frame is None else frame-self.last_frame-1;c=self.c
  active=[t for t in self.tracks.values() if t.state!='LOST']
  for t in active:
   for _ in range(min(skipped,c.window)):t.history.append(False);t.missed+=1
   if t.missed>=c.max_missed or dt>c.max_dt:t.state='LOST';t.reason='FRAME_GAP_OR_TIMEOUT';t.obs_id=None
   else:self.predict(t,dt)
  active=[t for t in active if t.state!='LOST'];owners={}
  for j,o in enumerate(observations):
   for i in o.point_ids:owners.setdefault(i,[]).append(j)
  collision={j for v in owners.values() if len(v)>1 for j in v};blocked=collision|{j for j,o in enumerate(observations) if o.unresolved}
  edges=[(i,j) for i,t in enumerate(active) for j,o in enumerate(observations) if self.match(t,o)]
  td={i:sum(x==i for x,y in edges) for i in range(len(active))};od={j:sum(y==j for x,y in edges) for j in range(len(observations))}
  disputed_t={i for i,j in edges if td[i]>1 or od[j]>1};disputed_o={j for i,j in edges if td[i]>1 or od[j]>1};assigned_t=set();assigned_o=set()
  for i,j in edges:
   if i in disputed_t or j in disputed_o:continue
   t,o=active[i],observations[j];assigned_t.add(i);assigned_o.add(j);t.box=o.box;t.obs_id=o.id;t.missed=0
   if j in blocked:t.history.append(False);t.state='AMBIGUOUS';t.reason='DUPLICATE_POINTS' if j in collision else 'SPATIAL_IDENTITY_UNRESOLVED';continue
   if t.channel!=o.channel:t.migrations+=1;t.channel=o.channel
   is3d=o.position is not None
   if is3d:self.update(t,o)
   t.history.append(is3d)
   t.state='VISUAL_ONLY' if not is3d else 'CONFIRMED_TRACK' if sum(t.history)>=c.confirm_observations else 'TENTATIVE_3D';t.reason='NO_CURRENT_3D' if not is3d else 'THREE_OF_FIVE' if t.state=='CONFIRMED_TRACK' else 'INSUFFICIENT_TEMPORAL_EVIDENCE'
  for i,t in enumerate(active):
   if i in assigned_t:continue
   t.obs_id=None;t.history.append(False);t.missed+=1;t.state='LOST' if t.missed>=c.max_missed else 'AMBIGUOUS';t.reason='OBSERVATION_MISSING_TIMEOUT' if t.state=='LOST' else 'COMPETING_ASSOCIATIONS' if i in disputed_t else 'CURRENT_OBSERVATION_MISSING'
  for j,o in enumerate(observations):
   if j in assigned_o or j in disputed_o:continue
   near=[t for t in active if self.boxes_overlap(t.box,o.box) and np.linalg.norm(self.center(t.box)-self.center(o.box))<=c.max_image_center_shift]
   if near:
    for t in near:t.state='AMBIGUOUS';t.reason='ASSOCIATION_GATE_CONFLICT';t.obs_id=None
    continue
   id=f'T-{self.next_id:04d}';self.next_id+=1;t=Track(id,o.cls,o.channel,o.box,history=deque(maxlen=c.window));t.obs_id=o.id
   if j in blocked:t.history.append(False);t.state='AMBIGUOUS';t.reason='DUPLICATE_POINTS' if j in collision else 'SPATIAL_IDENTITY_UNRESOLVED'
   else:
    valid=o.position is not None
    if valid:self.update(t,o)
    t.history.append(valid);t.state='TENTATIVE_3D' if valid else 'VISUAL_ONLY';t.reason='INSUFFICIENT_TEMPORAL_EVIDENCE' if valid else 'NO_CURRENT_3D'
   self.tracks[id]=t
  self.last_frame=frame;self.last_time=timestamp;out=[]
  for t in self.tracks.values():
   current=next((o for o in observations if o.id==t.obs_id),None);usable=current is not None and current.position is not None and t.state in ('TENTATIVE_3D','CONFIRMED_TRACK') and t.mean is not None
   out.append({'track_id':t.id,'class':t.cls,'channel':t.channel,'state':t.state,'reason':t.reason,'observation_id':t.obs_id,'valid_3d_in_last_5':sum(t.history),'migrations':t.migrations,'position_world_surface_proxy':t.mean[:3].tolist() if usable else None,'velocity_world_surface_proxy':t.mean[3:].tolist() if usable and t.velocity_measurements>=2 else None,'velocity_measurement_count':t.velocity_measurements,'position_std_xyz_m':np.sqrt(np.maximum(0,np.diag(t.covariance)[:3])).tolist() if usable else None,'may_enter_follow':False})
  return out
