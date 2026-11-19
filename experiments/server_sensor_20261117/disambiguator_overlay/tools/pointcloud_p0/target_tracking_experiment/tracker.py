"""Experimental sensor-only lifecycle and constant-velocity Kalman tracking.

The numeric gates are provisional offline values, not validated safety limits.
No simulator truth, semantic LiDAR or control interfaces are consumed here.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass,field
import math
import numpy as np

STATES={'VISUAL_ONLY','TENTATIVE_3D','CONFIRMED_TRACK','AMBIGUOUS','LOST'}
@dataclass(frozen=True)
class Config:
    window_frames: int=5
    required_valid_3d: int=3
    max_missing_frames: int=3
    max_gap_s: float=.20
    max_2d_center_shift: float=.10
    max_3d_shift_m: float=2.0
    mahalanobis_gate: float=16.27
    max_relative_speed_mps: float=25.0
    observation_std_m: float=.40
    acceleration_std_mps2: float=2.0
    min_pairwise_gap_m: float=1.0
    min_radial_gap_m: float=.50

@dataclass(frozen=True)
class Observation:
    observation_id: str
    channel: str
    class_name: str
    confidence: float
    bbox: tuple[float,float,float,float]
    timestamp_s: float
    position_world: tuple[float,float,float] | None
    lidar_point_ids: tuple[int,...]=()
    cross_target_unresolved: bool=False

@dataclass
class Track:
    track_id: str
    channel: str
    class_name: str
    bbox: tuple[float,float,float,float]
    last_detection_timestamp_s: float
    last_3d_timestamp_s: float | None=None
    last_3d_position: np.ndarray | None=None
    mean: np.ndarray | None=None
    covariance: np.ndarray | None=None
    history: deque=field(default_factory=lambda:deque(maxlen=5))
    missed: int=0
    state: str='VISUAL_ONLY'
    last_observation_id: str | None=None
    reasons: list[str]=field(default_factory=list)

class TargetTracker:
    def __init__(self,config:Config=Config()):
        if config.window_frames!=5 or config.required_valid_3d!=3 or config.max_missing_frames<1:raise ValueError('invalid provisional lifecycle configuration')
        self.config=config;self.tracks={};self._next=1;self._last_frame=None;self._last_timestamp=None

    @staticmethod
    def _center(b):return np.array([(b[0]+b[2])/2,(b[1]+b[3])/2])

    @staticmethod
    def _validate(o):
        b=np.asarray(o.bbox,float)
        if not o.observation_id or o.channel not in ('formal','auxiliary') or not o.class_name or not math.isfinite(o.timestamp_s) or not math.isfinite(o.confidence) or b.shape!=(4,) or not np.isfinite(b).all() or b[0]>=b[2] or b[1]>=b[3]:raise ValueError('invalid observation')
        if len(set(o.lidar_point_ids))!=len(o.lidar_point_ids):raise ValueError('repeated point ID in observation')
        if o.position_world is not None and (np.asarray(o.position_world).shape!=(3,) or not np.isfinite(o.position_world).all() or len(o.lidar_point_ids)<3):raise ValueError('3D evidence requires finite position and >=3 unique points')

    def _predict(self,t,dt):
        if t.mean is None:return
        f=np.eye(6);f[:3,3:]=np.eye(3)*dt;g=np.vstack((np.eye(3)*(.5*dt**2),np.eye(3)*dt));q=g@g.T*self.config.acceleration_std_mps2**2
        t.mean=f@t.mean;t.covariance=f@t.covariance@f.T+q

    def _innovation(self,t,o):
        if t.mean is None or o.position_world is None:return None
        delta=np.asarray(o.position_world)-t.mean[:3];s=t.covariance[:3,:3]+np.eye(3)*self.config.observation_std_m**2
        return float(np.linalg.norm(delta)),float(delta@np.linalg.solve(s,delta))

    def _match(self,t,o,dt):
        c=self.config
        if t.channel!=o.channel or t.class_name!=o.class_name:return False
        if float(np.linalg.norm(self._center(t.bbox)-self._center(o.bbox)))>c.max_2d_center_shift:return False
        if dt>c.max_gap_s:return False
        gate=self._innovation(t,o)
        if gate is not None and (gate[0]>c.max_3d_shift_m or gate[1]>c.mahalanobis_gate):return False
        if t.mean is not None and o.position_world is not None and t.last_3d_timestamp_s is not None:
            dt3=o.timestamp_s-t.last_3d_timestamp_s
            if dt3<=0:return False
            if float(np.linalg.norm(np.asarray(o.position_world)-t.last_3d_position))/dt3>c.max_relative_speed_mps:return False
        return True

    def _update(self,t,o):
        if o.position_world is None:return
        z=np.asarray(o.position_world,dtype=float);r=np.eye(3)*self.config.observation_std_m**2
        if t.mean is None:
            t.mean=np.r_[z,np.zeros(3)];t.covariance=np.diag([.64,.64,.64,25.,25.,25.])
        else:
            h=np.hstack((np.eye(3),np.zeros((3,3))));s=h@t.covariance@h.T+r;k=t.covariance@h.T@np.linalg.inv(s);t.mean=t.mean+k@(z-h@t.mean);i=np.eye(6)-k@h;t.covariance=i@t.covariance@i.T+k@r@k.T
        t.last_3d_timestamp_s=o.timestamp_s;t.last_3d_position=z.copy()

    def step(self,frame_id:int,timestamp_s:float,observations:list[Observation]):
        if not isinstance(frame_id,int) or not math.isfinite(timestamp_s):raise ValueError('invalid frame/time')
        if self._last_frame is not None and (frame_id<=self._last_frame or timestamp_s<=self._last_timestamp):raise ValueError('frame and timestamp must strictly increase')
        for o in observations:
            self._validate(o)
            if abs(o.timestamp_s-timestamp_s)>.001:raise ValueError('measurement timestamp mismatch')
        ids=[o.observation_id for o in observations]
        if len(ids)!=len(set(ids)):raise ValueError('duplicate observation ID')
        c=self.config;dt=0. if self._last_timestamp is None else timestamp_s-self._last_timestamp;skipped=0 if self._last_frame is None else frame_id-self._last_frame-1
        active=[t for t in self.tracks.values() if t.state!='LOST']
        for t in active:
            for _ in range(min(skipped,c.window_frames)):
                t.history.append(False);t.missed+=1
            if t.missed>=c.max_missing_frames or dt>c.max_gap_s:
                t.state='LOST';t.reasons=['FRAME_GAP_OR_TIMEOUT'];t.last_observation_id=None
            else:self._predict(t,dt)
        active=[t for t in active if t.state!='LOST'];used_by_point={};blocked={i for i,o in enumerate(observations) if o.cross_target_unresolved}
        for i,o in enumerate(observations):
            for pid in o.lidar_point_ids:used_by_point.setdefault(pid,[]).append(i)
        collisions={i for indexes in used_by_point.values() if len(indexes)>1 for i in indexes};blocked|=collisions
        edges=[]
        for ti,t in enumerate(active):
            for oi,o in enumerate(observations):
                if self._match(t,o,dt):edges.append((ti,oi))
        track_degrees={ti:sum(a==ti for a,b in edges) for ti in range(len(active))};obs_degrees={oi:sum(b==oi for a,b in edges) for oi in range(len(observations))}
        contested_tracks={ti for ti,oi in edges if track_degrees[ti]>1 or obs_degrees[oi]>1};contested_obs={oi for ti,oi in edges if track_degrees[ti]>1 or obs_degrees[oi]>1}
        assigned_tracks=set();assigned_obs=set()
        for ti,oi in edges:
            if ti in contested_tracks or oi in contested_obs:continue
            t,o=active[ti],observations[oi];assigned_tracks.add(ti);assigned_obs.add(oi);t.bbox=o.bbox;t.last_detection_timestamp_s=timestamp_s;t.last_observation_id=o.observation_id;t.missed=0
            if oi in blocked:
                t.history.append(False);t.state='AMBIGUOUS';t.reasons=['POINT_ID_CONFLICT' if oi in collisions else 'CROSS_TARGET_IDENTITY_UNRESOLVED'];continue
            is3d=o.position_world is not None
            if is3d:self._update(t,o)
            t.history.append(is3d);t.reasons=[]
            if not is3d:t.state='VISUAL_ONLY';t.reasons=['NO_3D_MEASUREMENT']
            elif sum(t.history)>=c.required_valid_3d:t.state='CONFIRMED_TRACK';t.reasons=['THREE_VALID_3D_OBSERVATIONS_IN_FIVE']
            else:t.state='TENTATIVE_3D';t.reasons=['MORE_CONSISTENT_3D_OBSERVATIONS_REQUIRED']
        for ti,t in enumerate(active):
            if ti in assigned_tracks:continue
            t.last_observation_id=None;t.history.append(False);t.missed+=1
            if t.missed>=c.max_missing_frames:t.state='LOST';t.reasons=['OBSERVATION_MISSING_TIMEOUT']
            else:t.state='AMBIGUOUS';t.reasons=['COMPETING_ASSOCIATIONS' if ti in contested_tracks else 'CURRENT_OBSERVATION_MISSING']
        for oi,o in enumerate(observations):
            if oi in assigned_obs or oi in contested_obs:continue
            # An image-near existing track that failed a 3-D/class gate is not
            # silently reintroduced as a distinct target.
            conflict=any(t.channel==o.channel and np.linalg.norm(self._center(t.bbox)-self._center(o.bbox))<=c.max_2d_center_shift for t in active)
            if conflict:
                for t in active:
                    if t.channel==o.channel and np.linalg.norm(self._center(t.bbox)-self._center(o.bbox))<=c.max_2d_center_shift:
                        t.state='AMBIGUOUS';t.reasons=['ASSOCIATION_GATE_CONFLICT'];t.last_observation_id=None
                continue
            tid=('F-' if o.channel=='formal' else 'A-')+f'{self._next:04d}';self._next+=1;t=Track(tid,o.channel,o.class_name,o.bbox,timestamp_s,history=deque(maxlen=c.window_frames));t.last_observation_id=o.observation_id
            if oi in blocked or conflict:
                t.history.append(False);t.state='AMBIGUOUS';t.reasons=['POINT_ID_CONFLICT' if oi in collisions else 'CROSS_TARGET_IDENTITY_UNRESOLVED' if oi in blocked else 'ASSOCIATION_GATE_CONFLICT']
            else:
                is3d=o.position_world is not None
                if is3d:self._update(t,o)
                t.history.append(is3d);t.state='TENTATIVE_3D' if is3d else 'VISUAL_ONLY';t.reasons=['MORE_CONSISTENT_3D_OBSERVATIONS_REQUIRED' if is3d else 'NO_3D_MEASUREMENT']
            self.tracks[tid]=t
        self._last_frame=frame_id;self._last_timestamp=timestamp_s
        out=[]
        for t in self.tracks.values():
            # Never expose predicted/stale positions as current observations.
            current=next((o for o in observations if o.observation_id==t.last_observation_id),None)
            position=t.mean[:3].tolist() if current is not None and current.position_world is not None and t.state in ('TENTATIVE_3D','CONFIRMED_TRACK') and t.mean is not None else None
            out.append({'track_id':t.track_id,'channel':t.channel,'class_name':t.class_name,'state':t.state,'reason_codes':t.reasons,'matched_observation_id':t.last_observation_id,'valid_3d_in_last_5':int(sum(t.history)),'observed_in_current_frame':current is not None,'position_world_surface_proxy':position,'speed_world_mps':float(np.linalg.norm(t.mean[3:])) if position is not None and t.mean is not None else None,'position_std_xyz_m':np.sqrt(np.maximum(0.,np.diag(t.covariance)[:3])).tolist() if position is not None and t.covariance is not None else None,'may_enter_follow':False})
        return out
