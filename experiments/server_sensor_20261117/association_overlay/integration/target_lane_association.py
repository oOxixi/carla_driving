"""Experimental sensor-position to CARLA lane association; no control authority.

Inputs are already-associated sensor positions in world coordinates. No CARLA
actor state is consulted. Stop at junctions, forks and uncertain lane boundaries.
"""
from __future__ import annotations
import math
from typing import Any

def _xy(location: Any) -> tuple[float,float]:
    return float(location.x), float(location.y)

def _distance(a: Any,b: Any) -> float:
    x,y=_xy(a);u,v=_xy(b)
    return math.hypot(x-u,y-v)

def _aligned(a: Any,b: Any) -> bool:
    x=a.transform.get_forward_vector();y=b.transform.get_forward_vector()
    return float(x.x*y.x+x.y*y.y)>0.8

def _walk(start: Any,direction: str,limit_m: float,step_m: float) -> list[tuple[float,Any]]:
    result=[];current=start;distance=0.0
    while distance+step_m<=limit_m:
        nxt=getattr(current,direction)(step_m)
        if len(nxt)!=1 or nxt[0].is_junction or not _aligned(current,nxt[0]):
            break
        segment=_distance(current.transform.location,nxt[0].transform.location)
        if segment<0.1 or segment>step_m*2.0:break
        distance+=segment;current=nxt[0]
        result.append((distance,current))
    return result

def _reference(ego: Any, forward_m: float=80.0, backward_m: float=20.0,
               step_m: float=2.0) -> list[tuple[float,Any]]:
    back=_walk(ego,'previous',backward_m,step_m)
    return [(-s,w) for s,w in reversed(back)]+[(0.0,ego)]+_walk(ego,'next',forward_m,step_m)

def _adjacent(wp: Any, side: str) -> Any:
    if side=='CURRENT':return wp
    n=getattr(wp, 'get_left_lane' if side=='LEFT' else 'get_right_lane')()
    if n is None or n.is_junction or not _aligned(wp,n):return None
    if str(n.lane_type).split('.')[-1]!='Driving':return None
    return n

def _closest(location: Any,reference: list[tuple[float,Any]],side: str) -> dict|None:
    px,py=_xy(location);best=None
    for index,((sa,wa),(sb,wb)) in enumerate(zip(reference,reference[1:])):
        a=_adjacent(wa,side);b=_adjacent(wb,side)
        if a is None or b is None:continue
        ax,ay=_xy(a.transform.location);bx,by=_xy(b.transform.location)
        dx,dy=bx-ax,by-ay;denom=dx*dx+dy*dy
        if denom<0.01:continue
        raw=((px-ax)*dx+(py-ay)*dy)/denom;t=max(0.,min(1.,raw))
        off=math.hypot(px-(ax+t*dx),py-(ay+t*dy))
        item={'offset_m':off,'delta_s_m':sa+t*(sb-sa),'raw_t':raw,
              'lane_width':min(float(a.lane_width),float(b.lane_width)),
              'waypoints':(a,b),'segment_index':index}
        if best is None or item['offset_m']<best['offset_m']:best=item
    return best

def associate(world_map: Any,ego_location: Any,target_location: Any,*, boundary_margin_m: float=.4) -> dict:
    unknown={'lane_relation':'UNKNOWN','longitudinal_relation':'UNKNOWN','same_lane':None,'delta_s_m':None}
    try:
        import carla
        ego=world_map.get_waypoint(ego_location,project_to_road=True,lane_type=carla.LaneType.Driving)
        target=world_map.get_waypoint(target_location,project_to_road=True,lane_type=carla.LaneType.Driving)
        if not ego or not target:return {**unknown,'reason':'NO_DRIVING_WAYPOINT'}
        if ego.is_junction or target.is_junction:return {**unknown,'reason':'JUNCTION'}
        if _distance(ego_location,ego.transform.location)>float(ego.lane_width)/2-boundary_margin_m:
            return {**unknown,'reason':'EGO_NEAR_LANE_BOUNDARY'}
        ref=_reference(ego)
        if len(ref)<2:return {**unknown,'reason':'NO_UNAMBIGUOUS_ROAD_PATH'}
        choices=[(side,x) for side in ('CURRENT','LEFT','RIGHT') if (x:=_closest(target_location,ref,side))]
        if not choices:return {**unknown,'reason':'NO_REACHABLE_LANES'}
        choices.sort(key=lambda p:p[1]['offset_m']);side,best=choices[0]
        if (best['segment_index']==0 and best['raw_t']<0) or (best['segment_index']==len(ref)-2 and best['raw_t']>1):
            return {**unknown,'reason':'OUTSIDE_UNAMBIGUOUS_PATH'}
        if best['offset_m']>=best['lane_width']/2-boundary_margin_m:
            return {**unknown,'reason':'TARGET_NEAR_LANE_BOUNDARY_OR_OFF_ROAD'}
        if len(choices)>1 and choices[1][1]['offset_m']-best['offset_m']<2*boundary_margin_m:
            return {**unknown,'reason':'AMBIGUOUS_LANE'}
        matches=any((target.road_id,target.lane_id)==(w.road_id,w.lane_id) and _aligned(target,w) for w in best['waypoints'])
        if not matches:return {**unknown,'reason':'MAP_LANE_OR_DIRECTION_MISMATCH'}
        delta=float(best['delta_s_m'])
        longitudinal='AHEAD' if delta>1.0 else 'BEHIND' if delta < -1.0 else 'UNKNOWN'
        return {'lane_relation':side,'longitudinal_relation':longitudinal,
                'same_lane':side=='CURRENT','delta_s_m':round(delta,3),
                'lateral_offset_m':round(best['offset_m'],3),
                'target_road_id':target.road_id,'target_lane_id':target.lane_id,
                'ego_road_id':ego.road_id,'ego_lane_id':ego.lane_id,
                'reason':'MATCHED' if longitudinal!='UNKNOWN' else 'LONGITUDINAL_TOO_CLOSE'}
    except (AttributeError,TypeError,ValueError,RuntimeError,ImportError) as e:
        return {**unknown,'reason':'MAP_ERROR:'+type(e).__name__}

def build_follow_candidates(targets: list[dict]) -> list[str]:
    """Only include confidently located vehicles in the current lane ahead."""
    return [str(t['id']) for t in targets
            if t.get('class') in {'car','truck','bus'}
            and isinstance(t.get('distance_m'),(int,float))
            and not isinstance(t.get('distance_m'),bool)
            and math.isfinite(t['distance_m']) and t['distance_m'] >= 0
            and t.get('lane_relation')=='CURRENT'
            and t.get('longitudinal_relation')=='AHEAD'
            and t.get('same_lane') is True]
