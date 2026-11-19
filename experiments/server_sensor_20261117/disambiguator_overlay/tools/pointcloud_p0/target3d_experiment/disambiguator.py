"""Sensor-only experimental 3-D identity evidence, never driving authority.

IDs identify original returns within a single LiDAR frame. Neither actor truth
nor semantic LiDAR appears in this module. Configuration is intentionally
required: numbers tuned on evaluation samples must not become production gates.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import math
import numpy as np

@dataclass(frozen=True)
class TargetObservation:
    target_id: str
    frame_id: int
    timestamp_s: float
    sensor_id: str
    detection_box_xyxy: tuple[float, float, float, float]
    point_ids: np.ndarray
    points_lidar_xyz: np.ndarray
    cluster_ids: np.ndarray

@dataclass(frozen=True)
class PairObservation:
    formal: TargetObservation | None
    auxiliary: TargetObservation

@dataclass(frozen=True)
class ResearchPolicy:
    min_cluster_points: int
    min_3d_distance_m: float
    min_radial_gap_m: float
    min_observations: int
    max_inter_frame_gap_s: float
    max_frame_gap: int
    max_sensor_skew_s: float = 0.001

    def validate(self) -> None:
        if self.min_cluster_points < 3 or self.min_observations < 2 or not isinstance(self.max_frame_gap, int) or self.max_frame_gap < 1:
            raise ValueError('need >=3 points and >=2 observations')
        values=(self.min_3d_distance_m,self.min_radial_gap_m,self.max_inter_frame_gap_s,self.max_sensor_skew_s)
        if not all(math.isfinite(x) and x > 0 for x in values):
            raise ValueError('research thresholds must be finite and positive')

def _validate_target(t: TargetObservation) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not t.target_id or not t.sensor_id or not isinstance(t.frame_id,int) or not math.isfinite(t.timestamp_s):
        raise ValueError('invalid identity, frame or timestamp')
    b=np.asarray(t.detection_box_xyxy,dtype=float)
    if b.shape!=(4,) or not np.isfinite(b).all() or b[0]>=b[2] or b[1]>=b[3]:
        raise ValueError('invalid detection box')
    ids=np.asarray(t.point_ids);pts=np.asarray(t.points_lidar_xyz,dtype=float);cluster=np.asarray(t.cluster_ids)
    if ids.ndim!=1 or cluster.ndim!=1 or not np.issubdtype(ids.dtype,np.integer) or not np.issubdtype(cluster.dtype,np.integer):
        raise ValueError('point IDs must be integer vectors')
    if pts.shape!=(len(ids),3) or not np.isfinite(pts).all():
        raise ValueError('points must be finite Nx3')
    if len(np.unique(ids))!=len(ids) or len(np.unique(cluster))!=len(cluster):
        raise ValueError('duplicate point ID within observation')
    if not set(cluster.tolist()).issubset(set(ids.tolist())):
        raise ValueError('cluster is not a subset of assigned candidate points')
    return ids,pts,cluster

def _interval_gap(a: np.ndarray,b: np.ndarray) -> float:
    return max(0.,float(np.min(a)-np.max(b)),float(np.min(b)-np.max(a)))

def _metrics(pair: PairObservation, skew: float) -> dict:
    f=pair.formal;a=pair.auxiliary;ai,ap,ac=_validate_target(a)
    out={'frame_id':a.frame_id,'auxiliary_id':a.target_id,'auxiliary_point_count':len(ai),'auxiliary_cluster_count':len(ac),'reasons':[]}
    if not len(ac):out['reasons'].append('NO_AUXILIARY_CLUSTER')
    if f is None:out['reasons'].append('NO_FORMAL_TARGET');return out
    fi,fp,fc=_validate_target(f);out.update(formal_id=f.target_id,formal_point_count=len(fi),formal_cluster_count=len(fc))
    if f.target_id==a.target_id:out['reasons'].append('SAME_TARGET_IDENTIFIER')
    if f.sensor_id!=a.sensor_id or f.frame_id!=a.frame_id:out['reasons'].append('FRAME_OR_SENSOR_MISMATCH')
    delta=abs(f.timestamp_s-a.timestamp_s);out['timestamp_skew_s']=delta
    if delta>skew:out['reasons'].append('TIMESTAMP_MISMATCH')
    overlap=np.intersect1d(fi,ai);out['duplicate_point_ids']=[int(x) for x in overlap]
    if len(overlap):out['reasons'].append('DUPLICATE_POINT_OWNERSHIP')
    if not len(fc):out['reasons'].append('NO_FORMAL_CLUSTER')
    if len(out['reasons']):return out
    fxyz=fp[np.isin(fi,fc)];axyz=ap[np.isin(ai,ac)];unclustered=ap[~np.isin(ai,ac)];fd=np.linalg.norm(fxyz,axis=1);ad=np.linalg.norm(axyz,axis=1)
    delta_xyz=fxyz[:,None,:]-axyz[None,:,:];dist=np.linalg.norm(delta_xyz,axis=2)
    axis_gap=np.maximum(0.,np.maximum(np.min(fxyz,axis=0)-np.max(axyz,axis=0),np.min(axyz,axis=0)-np.max(fxyz,axis=0)))
    x1,y1,x2,y2=f.detection_box_xyxy;u1,v1,u2,v2=a.detection_box_xyxy;inter=max(0.,min(x2,u2)-max(x1,u1))*max(0.,min(y2,v2)-max(y1,v1));union=(x2-x1)*(y2-y1)+(u2-u1)*(v2-v1)-inter
    out.update({'bbox_iou':inter/union if union else None,'formal_radial_range_m':[float(fd.min()),float(fd.max())],'auxiliary_radial_range_m':[float(ad.min()),float(ad.max())],'radial_interval_gap_m':_interval_gap(fd,ad),'nearest_3d_points_m':float(np.min(dist)),'median_pairwise_3d_distance_m':float(np.median(dist)),'axis_aligned_gap_xyz_m':axis_gap.tolist(),'formal_centroid_xyz':np.median(fxyz,axis=0).tolist(),'auxiliary_centroid_xyz':np.median(axyz,axis=0).tolist(),'formal_cluster_span_xyz_m':np.ptp(fxyz,axis=0).tolist(),'auxiliary_cluster_span_xyz_m':np.ptp(axyz,axis=0).tolist(),'auxiliary_unclustered_points':len(ai)-len(ac),'auxiliary_largest_radial_gap_m':float(np.max(np.diff(np.sort(ad)))) if len(ad)>1 else None,'unclustered_nearest_to_aux_m':float(np.min(np.linalg.norm(unclustered[:,None,:]-axyz[None,:,:],axis=2))) if len(unclustered) else None,'unclustered_nearest_to_formal_m':float(np.min(np.linalg.norm(unclustered[:,None,:]-fxyz[None,:,:],axis=2))) if len(unclustered) else None,'multi_object_mixture':'CANNOT_EXCLUDE_WITH_AVAILABLE_SENSOR_EVIDENCE'})
    return out

def disambiguate(current: PairObservation, *, history: Sequence[PairObservation]=(), policy: ResearchPolicy | None=None) -> dict:
    """Return geometry and a fail-closed research decision; never promote a target.

    All history entries must contain real prior observations of the same sensor
    tracks. Timestamps and frame IDs are checked; point IDs are frame-local.
    Explicit thresholds are *experimental* and must be independently calibrated.
    """
    if policy is not None:policy.validate()
    try:
        current_metrics=_metrics(current, policy.max_sensor_skew_s if policy else 0.001)
    except (TypeError,ValueError,AttributeError) as exc:
        return {'status':'UNKNOWN','reasons':['INVALID_OBSERVATION'],'detail':str(exc),'formal_control_authority':False}
    reasons=list(current_metrics['reasons']);observations=[]
    try:
        for pair in history:
            observations.append(_metrics(pair,policy.max_sensor_skew_s if policy else 0.001))
    except (TypeError,ValueError,AttributeError) as exc:
        return {'status':'UNKNOWN','reasons':['INVALID_HISTORY'],'detail':str(exc),'current':current_metrics,'formal_control_authority':False}
    observations.append(current_metrics)
    if not history:reasons.append('TEMPORAL_EVIDENCE_MISSING')
    if policy is None:reasons.append('THRESHOLDS_NOT_CALIBRATED')
    if policy is not None:
        if len(observations)<policy.min_observations:reasons.append('INSUFFICIENT_TEMPORAL_OBSERVATIONS')
        if current.formal is not None:
            target_ids=(current.formal.target_id,current.auxiliary.target_id,current.auxiliary.sensor_id)
            timestamps=[];frames=[]
            for pair,metrics in zip([*history,current],observations):
                if pair.formal is None or (pair.formal.target_id,pair.auxiliary.target_id,pair.auxiliary.sensor_id)!=target_ids:
                    reasons.append('INCONSISTENT_TRACK_IDENTITY');continue
                if metrics['reasons']:reasons.append('INVALID_PAIR_IN_HISTORY')
                if metrics.get('formal_cluster_count',0)<policy.min_cluster_points or metrics.get('auxiliary_cluster_count',0)<policy.min_cluster_points:
                    reasons.append('INSUFFICIENT_CLUSTER_POINTS')
                if metrics.get('nearest_3d_points_m',-1)<policy.min_3d_distance_m:reasons.append('SPATIAL_SEPARATION_UNCERTAIN')
                if metrics.get('radial_interval_gap_m',-1)<policy.min_radial_gap_m:reasons.append('DEPTH_SEPARATION_UNCERTAIN')
                timestamps.append(pair.auxiliary.timestamp_s);frames.append(pair.auxiliary.frame_id)
            if any(b<=a or b-a>policy.max_frame_gap for a,b in zip(frames,frames[1:])) or any(b<=a or b-a>policy.max_inter_frame_gap_s for a,b in zip(timestamps,timestamps[1:])):
                reasons.append('HISTORY_NOT_CONSECUTIVE')
    reasons=list(dict.fromkeys(reasons))
    status='UNKNOWN' if reasons else 'INDEPENDENT_3D_HYPOTHESES_SUPPORTED_UNVALIDATED'
    return {'status':status,'reasons':reasons,'current':current_metrics,'temporal_observations':len(observations),'temporal_support':'NOT_AVAILABLE' if not history else 'EVALUATED_WITH_RESEARCH_POLICY' if policy else 'NOT_EVALUATED_NO_POLICY','formal_control_authority':False,'vehicle_center_or_extent_established':False}

class Target3DDisambiguator:
    """Reusable, sensor-only facade; its results carry no control authority."""
    def __init__(self, policy: ResearchPolicy | None = None):
        if policy is not None:
            policy.validate()
        self._policy = policy

    def evaluate(self, current: PairObservation, *, history: Sequence[PairObservation] = ()) -> dict:
        return disambiguate(current, history=history, policy=self._policy)
