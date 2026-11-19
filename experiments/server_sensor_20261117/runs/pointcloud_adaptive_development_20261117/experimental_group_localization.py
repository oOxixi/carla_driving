"""Single-frame target grouping and auditable point ownership, no simulator truth."""
from __future__ import annotations
import math
import numpy as np
from integration.camera_lidar_association import _rigid_matrix
from integration.target_pointcloud_localization import localize as single_localize,_transform,_ground_plane,_clusters
from integration.duplicate_detection_grouper import DuplicateDetectionGrouper
AMBIGUOUS=0
ASSIGNED=1
ENVIRONMENT=2
# Reason codes: no measurement discarded; 0 outside boxes, 1 ambiguous overlap,
# 2 ground-like, 3 eligible but not selected, 4 accepted, 5 height filtered, 6 no plane.

def _limit(profile,r):
    if profile is None:return None
    for item in profile['bins']:
        if r<item['upper_m']:return float(item['limit_m'])
    return float(profile['fallback_m'])

def _depth_components(points,eps,tau):
    if tau is None:return _clusters(points,eps)
    if len(points)<3:return []
    radial=np.linalg.norm(points,axis=1)
    adjacency=(np.sum((points[:,None,:]-points[None,:,:])**2,axis=2)<=eps**2)&(np.abs(radial[:,None]-radial[None,:])<=tau)
    seen=set();components=[]
    for i in range(len(points)):
        if i in seen:continue
        todo=[i];seen.add(i);comp=[]
        while todo:
            j=todo.pop();comp.append(j)
            for k in np.flatnonzero(adjacency[j]):
                k=int(k)
                if k not in seen:seen.add(k);todo.append(k)
        if len(comp)>=3:components.append(np.asarray(comp,dtype=int))
    return components

def localize_groups(objects,lidar,rgb,radar,ego_transform,camera_fov=100,history=None,alpha=1.0,fixed_radius=None,depth_profile=None,geometry_profile=None):
    frame=getattr(rgb,'frame',None)
    if frame is None or any(getattr(x,'frame',None)!=frame for x in (lidar,radar)):raise ValueError('sensor frame mismatch')
    ts=[float(x.timestamp) for x in (rgb,lidar,radar)]
    if any(not math.isfinite(x) for x in ts) or max(ts)-min(ts)>.001:raise ValueError('sensor timestamp mismatch')
    ids=[o.track_id for o in objects]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate detection ID')
    singles={o.track_id:single_localize([o],lidar,rgb,radar,ego_transform,camera_fov)['objects'][0] for o in objects}
    raw=np.frombuffer(lidar.raw_data,dtype=np.float32).reshape(-1,4)[:,:3]
    world=_transform(raw,_rigid_matrix(lidar.transform,'get_matrix'));ego=_transform(world,_rigid_matrix(ego_transform,'get_inverse_matrix'));cam=_transform(world,_rigid_matrix(rgb.transform,'get_inverse_matrix'))
    groups,evidence=DuplicateDetectionGrouper().group(objects,singles,history,lidar_ego=ego)
    f=rgb.width/(2*math.tan(math.radians(camera_fov)/2));depth=np.maximum(cam[:,0],1e-6);u=(f*cam[:,1]/depth+rgb.width/2)/rgb.width;v=(-f*cam[:,2]/depth+rgb.height/2)/rgb.height
    valid=(cam[:,0]>1)&(ego[:,0]>0)&np.isfinite(ego).all(axis=1)
    masks=[];scores=[]
    for group in groups:
        mask=np.zeros(len(raw),dtype=bool);score=np.full(len(raw),np.inf)
        for obj in group.members:
            x1,y1,x2,y2=obj.bbox_xyxy_norm
            if x2<=x1 or y2<=y1:continue
            m=valid&(u>=x1)&(u<=x2)&(v>=y1)&(v<=y2);mask|=m
            r=((u-(x1+x2)/2)/((x2-x1)/2))**2+((v-(y1+y2)/2)/((y2-y1)/2))**2
            score=np.minimum(score,np.where(m,r,np.inf))
        masks.append(mask);scores.append(score)
    count=np.sum(masks,axis=0) if masks else np.zeros(len(raw),dtype=int)
    owners=np.full(len(raw),-1,dtype=np.int32)
    for i,mask in enumerate(masks):owners[mask&(count==1)]=i
    # For overlapping distinct groups, require the best 2D and 3D hypotheses to agree.
    if groups and np.any(count>1):
        score=np.asarray(scores);dist=np.full(score.shape,np.inf)
        for i,g in enumerate(groups):
            s=singles[g.representative.track_id]
            if s['status']=='LOCATED_UNVALIDATED' and s.get('cluster_count',0)>=5:
                x,y,z=s['cluster_center_ego'];dist[i]=np.where(masks[i],np.linalg.norm(ego-np.array([x,-y,z]),axis=1),np.inf)
        order=np.argsort(dist,axis=0);cols=np.arange(len(raw));best=order[0];d1=dist[best,cols];d2=dist[order[1],cols] if len(groups)>1 else np.full(len(raw),np.inf)
        image_best=np.argmin(score,axis=0);all_anchors=np.sum(np.isfinite(dist),axis=0)==count
        gap=np.zeros(len(raw));finite=np.isfinite(d1)&np.isfinite(d2);gap[finite]=d2[finite]-d1[finite]
        reliable=(count>1)&all_anchors&(image_best==best)&(d1<=1.25)&(gap>=.35)
        owners[reliable]=best[reliable]
    plane=_ground_plane(ego);point_state=np.full(len(raw),AMBIGUOUS,dtype=np.uint8);reason=np.zeros(len(raw),dtype=np.uint8);reason[count>1]=1
    heights=np.full(len(raw),np.nan)
    if plane is not None:
        heights=ego[:,2]-(plane['a']*ego[:,0]+plane['b']*ego[:,1]+plane['c'])
        ground=(count>0)&(abs(heights)<=.08);reason[ground]=2;owners[ground]=-1  # ground-like stays AMBIGUOUS without independent confirmation
    # Radar detections are used only as support after the same-camera unique-group test.
    rd=[]
    for det in radar:
        r,a,z=map(float,(det.depth,det.azimuth,det.altitude))
        if math.isfinite(r) and math.isfinite(a) and math.isfinite(z) and r>0:rd.append((r*math.cos(z)*math.cos(a),r*math.cos(z)*math.sin(a),r*math.sin(z)))
    radar_world=_transform(np.asarray(rd,dtype=float).reshape(-1,3),_rigid_matrix(radar.transform,'get_matrix'));radar_ego=_transform(radar_world,_rigid_matrix(ego_transform,'get_inverse_matrix'));radar_cam=_transform(radar_world,_rigid_matrix(rgb.transform,'get_inverse_matrix'))
    safe=np.maximum(radar_cam[:,0],1e-6);ru=(f*radar_cam[:,1]/safe+rgb.width/2)/rgb.width;rv=(-f*radar_cam[:,2]/safe+rgb.height/2)/rgb.height
    radar_masks=[]
    for group in groups:
        mask=np.zeros(len(rd),dtype=bool)
        for obj in group.members:
            x1,y1,x2,y2=obj.bbox_xyxy_norm;mask|=(radar_cam[:,0]>1)&(ru>=x1)&(ru<=x2)&(rv>=y1)&(rv<=y2)
        radar_masks.append(mask)
    radar_count=np.sum(radar_masks,axis=0) if radar_masks else np.zeros(len(rd),dtype=int)
    result=[]
    for i,g in enumerate(groups):
        member_points=np.flatnonzero(masks[i]);eligible=np.flatnonzero((owners==i)&(point_state!=ENVIRONMENT));reason[eligible]=3
        nonground=eligible[(heights[eligible]>.22)&(heights[eligible]<3.5)] if plane is not None else np.array([],dtype=int)
        if plane is None:reason[eligible]=6
        else:reason[eligible[(heights[eligible]<=.22)|(heights[eligible]>=3.5)]]=5
        row={'group_id':g.group_id,'members':[{'id':o.track_id,'class':o.class_name,'confidence':float(o.confidence),'bbox':list(o.bbox_xyxy_norm)} for o in g.members],'representative':g.representative.track_id,'group_evidence':list(g.evidence),'status':'UNKNOWN','reason':'GROUND_UNRELIABLE' if plane is None else 'INSUFFICIENT_LIDAR_POINTS','box_point_indices':member_points.tolist(),'candidate_point_indices':eligible.tolist(),'nonground_point_indices':nonground.tolist(),'selected_point_indices':[],'clusters':[]}
        if plane is None or len(nonground)<3:result.append(row);continue
        if len(nonground)>2500:row['reason']='TOO_MANY_POINTS_AMBIGUOUS';result.append(row);continue
        p=ego[nonground];med_dist=float(np.median(np.linalg.norm(p[:,:2],axis=1)));base_eps=min(1.0,max(.38,.018*med_dist));eps=float(fixed_radius) if fixed_radius is not None else min(1.20,max(.38,alpha*base_eps));tau=_limit(depth_profile,med_dist);connected=_depth_components(p,eps,tau);options=[];rejected_geometry=[];row['experimental_epsilon_m']=eps;row['experimental_depth_limit_m']=tau
        for component in connected:
            pts=p[component];span=np.ptp(pts,axis=0)
            if span[0]>6.5 or span[1]>3.5 or span[2]>3.0:continue
            radial=np.linalg.norm(pts,axis=1);depth_spread=float(np.ptp(radial));geo_limit=_limit(geometry_profile,med_dist)
            if geo_limit is not None and depth_spread>geo_limit:
                rejected_geometry.append({'count':len(component),'radial_spread_m':depth_spread,'limit_m':geo_limit});continue
            eligible_radar=np.flatnonzero(radar_masks[i]&(radar_count==1))
            if len(eligible_radar):
                delta=np.sum((pts[:,None,:]-radar_ego[eligible_radar][None,:,:])**2,axis=2);ri=eligible_radar[np.min(delta,axis=0)<=1.25**2]
            else:ri=np.array([],dtype=int)
            options.append({'indices':nonground[component],'radar_indices':ri,'count':len(component),'radar_hits':len(ri),'span_m':[float(v) for v in span],'median_forward_m':float(np.median(pts[:,0]))})
        options.sort(key=lambda x:(x['radar_hits']>0,x['count']),reverse=True);row['clusters']=[{k:v for k,v in opt.items() if k not in ('indices','radar_indices')} for opt in options]
        if geometry_profile is not None:
            row['geometry_rejected']=rejected_geometry
            if rejected_geometry:
                row['reason']='GEOMETRY_REJECTED_OR_AMBIGUOUS';result.append(row);continue
        if not options:row['reason']='NO_PLAUSIBLE_CLUSTER';result.append(row);continue
        if len(options)>1 and options[1]['count']>=.67*options[0]['count'] and bool(options[0]['radar_hits'])==bool(options[1]['radar_hits']):
            row['reason']='MULTIPLE_PLAUSIBLE_CLUSTERS';result.append(row);continue
        selected=options[0]['indices'];pts=ego[selected];ranges=np.linalg.norm(pts[:,:2],axis=1);center=np.median(pts,axis=0);spans=np.ptp(pts,axis=0);quant=np.percentile(pts,[10,90],axis=0)
        point_state[selected]=ASSIGNED;reason[selected]=4
        row.update(status='LOCATED_UNVALIDATED',reason='ONE_SELECTED_CLUSTER',selected_point_indices=selected.tolist(),radar_point_indices=options[0]['radar_indices'].tolist(),cluster_count=len(selected),cluster_center_ego=[float(center[0]),float(-center[1]),float(center[2])],nearest_surface_distance_m=float(ranges.min()),surface_distance_p10_m=float(np.percentile(ranges,10)),quality={'span_forward_left_up_m':[float(spans[0]),float(spans[1]),float(spans[2])],'range_iqr_m':float(np.percentile(ranges,75)-np.percentile(ranges,25)),'range_std_m':float(np.std(ranges)),'q10_q90_spread_m':[float(x) for x in quant[1]-quant[0]],'selected_inside_member_boxes_fraction':float(np.mean(masks[i][selected])),'surface_support':'EVIDENCE_ONLY' if len(selected)>=5 and float(np.percentile(ranges,90)-np.percentile(ranges,10))<=1.2 else 'LIMITED', 'geometry_warnings':(['FEW_POINTS'] if len(selected)<5 else [])+(['NARROW_LATERAL_SPREAD'] if spans[1]<.2 else [])+(['NARROW_VERTICAL_SPREAD'] if spans[2]<.1 else [])+(['RANGE_DISPERSED'] if float(np.percentile(ranges,90)-np.percentile(ranges,10))>1.2 else []),'vehicle_center_supported':False,'vehicle_occupancy_supported':False,'temporal_consistency':'NOT_AVAILABLE' if not history else 'NOT_EVALUATED'})
        result.append(row)
    # Only ASSIGNED points have an owner. AMBIGUOUS points remain in raw data for future review.
    final_owner=np.where(point_state==ASSIGNED,owners,-1).astype(np.int32)
    assert np.all((point_state!=ASSIGNED)|(final_owner>=0)) and all(len(r['selected_point_indices'])==len(set(r['selected_point_indices'])) for r in result)
    for row in result:
        if row['status']=='LOCATED_UNVALIDATED':row['diagnostic_outcome']='CANDIDATE_UNVALIDATED'
        elif row['reason'] in ('MULTIPLE_PLAUSIBLE_CLUSTERS','GEOMETRY_REJECTED_OR_AMBIGUOUS'):row['diagnostic_outcome']='AMBIGUOUS'
        else:row['diagnostic_outcome']='FAILED'
    return {'frame':frame,'groups':result,'pair_evidence':evidence,'ground_plane':plane,'point_state':point_state,'point_owner':final_owner,'point_reason':reason,'lidar_ego':ego,'lidar_world':world,'radar_world':radar_world,'uv':np.column_stack((u,v))}
