"""Conservative same-object hypotheses; inputs are detections and sensor geometry only."""
from __future__ import annotations
import math
from dataclasses import dataclass
VEHICLE_CLASSES={'car','truck','bus'}
@dataclass(frozen=True)
class DetectionGroup:
    group_id:str
    members:tuple
    representative:object
    evidence:tuple

def box_iou(a,b):
    x1,y1,x2,y2=a;u1,v1,u2,v2=b
    intersection=max(0,min(x2,u2)-max(x1,u1))*max(0,min(y2,v2)-max(y1,v1))
    return intersection/max(1e-12,(x2-x1)*(y2-y1)+(u2-u1)*(v2-v1)-intersection)

def assess_pair(a,b,sa,sb,history=None,lidar_ego=None):
    evidence={'ids':[a.track_id,b.track_id],'iou':box_iou(a.bbox_xyxy_norm,b.bbox_xyxy_norm),'decision':'SEPARATE','reason':None}
    if a.class_name.lower() not in VEHICLE_CLASSES or b.class_name.lower() not in VEHICLE_CLASSES:
        evidence['reason']='INCOMPATIBLE_SUPERCLASS';return evidence
    if evidence['iou']<.90:evidence['reason']='BOX_OVERLAP_NOT_STRONG';return evidence
    ba,bb=a.bbox_xyxy_norm,b.bbox_xyxy_norm
    wa,ha=ba[2]-ba[0],ba[3]-ba[1];wb,hb=bb[2]-bb[0],bb[3]-bb[1]
    if min(wa,ha,wb,hb)<=0:evidence['reason']='INVALID_BOX';return evidence
    size_ratio=min(wa/wb,wb/wa,ha/hb,hb/ha)
    center_delta=math.hypot(((ba[0]+ba[2])-(bb[0]+bb[2]))/(wa+wb),((ba[1]+ba[3])-(bb[1]+bb[3]))/(ha+hb))
    evidence.update(size_ratio=size_ratio,normalized_center_delta=center_delta)
    if size_ratio<.85 or center_delta>.12:evidence['reason']='BOX_SHAPE_INCONSISTENT';return evidence
    if history:
        h1=history.get(a.track_id);h2=history.get(b.track_id)
        if h1 and h2 and h1.get('stable') and h2.get('stable') and h1.get('track_id')!=h2.get('track_id'):
            evidence['reason']='CONTRADICTORY_STABLE_TRACKS';return evidence
    if not all(s and s['status']=='LOCATED_UNVALIDATED' and s.get('cluster_count',0)>=5 for s in (sa,sb)):
        evidence['reason']='INSUFFICIENT_3D_EVIDENCE';return evidence
    pa,pb=set(sa['selected_point_indices']),set(sb['selected_point_indices'])
    jac=len(pa&pb)/len(pa|pb) if pa|pb else 0
    depth_delta=abs(sa['cluster_center_ego'][0]-sb['cluster_center_ego'][0])
    evidence.update(cluster_point_jaccard=jac,forward_delta_m=depth_delta)
    if jac<.8 or depth_delta>=.5:evidence['reason']='3D_CLUSTER_MISMATCH';return evidence
    # Two plausible depth-separated clusters are evidence against an automatic merge.
    for s in (sa,sb):
        main=s['cluster_center_ego'][0]
        if any(c['count']>=3 and abs(c['median_forward_m']-main)>1.5 for c in s.get('clusters',[])):
            evidence['reason']='COMPETING_DEPTH_CLUSTERS';return evidence
    # Even a few points at a second plausible foreground depth make the merge unsafe.
    # This is a conservative heuristic, not proof that background points are vehicles.
    if lidar_ego is None:
        evidence['reason']='MISSING_DEPTH_SCAN';return evidence
    suspicious=set()
    for item in (sa,sb):
        center=item['cluster_center_ego'][0]
        for ix in item.get('nonground_point_indices',[]):
            delta=abs(float(lidar_ego[ix,0])-center)
            if 4.5<=delta<=15.0:suspicious.add(ix)
    evidence['other_plausible_depth_points']=len(suspicious)
    if suspicious:
        evidence['reason']='POSSIBLE_SECOND_DEPTH';return evidence
    evidence['decision']='GROUP';evidence['reason']='CONSISTENT_BOX_AND_CLUSTER';return evidence

class DuplicateDetectionGrouper:
    def group(self,objects,single_results,history=None,lidar_ego=None):
        # Complete-link grouping: every pair must pass, avoiding transitive chain merges.
        pairs={};records=[]
        for i,a in enumerate(objects):
            for b in objects[i+1:]:
                e=assess_pair(a,b,single_results.get(a.track_id),single_results.get(b.track_id),history,lidar_ego)
                pairs[frozenset((a.track_id,b.track_id))]=e;records.append(e)
        clusters=[[o] for o in objects]
        while True:
            options=[]
            for i,left in enumerate(clusters):
                for j in range(i+1,len(clusters)):
                    right=clusters[j];ev=[pairs[frozenset((a.track_id,b.track_id))] for a in left for b in right]
                    if ev and all(q['decision']=='GROUP' for q in ev):options.append((min(q['iou'] for q in ev),i,j))
            if not options:break
            _,i,j=max(options);clusters[i]+=clusters[j];clusters.pop(j)
        groups=[]
        for n,members in enumerate(clusters):
            members=tuple(members);rep=max(members,key=lambda x:(x.confidence,x.track_id));ev=tuple(pairs[frozenset((a.track_id,b.track_id))] for i,a in enumerate(members) for b in members[i+1:]);groups.append(DetectionGroup(f'G-{n+1:04d}',members,rep,ev))
        return groups,records
