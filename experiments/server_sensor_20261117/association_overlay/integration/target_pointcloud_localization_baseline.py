"""Experimental RGB/LiDAR/radar geometry. Never consumes simulator actor truth."""
from __future__ import annotations
import math
import numpy as np
from .camera_lidar_association import _rigid_matrix

def _transform(points,matrix):
    return (np.column_stack((points,np.ones(len(points))))@matrix.T)[:,:3]

def _ground_plane(points):
    """Deterministic RANSAC plane in ego coordinates; fail closed if unsupported."""
    q=points[(points[:,0]>2)&(points[:,0]<35)&(abs(points[:,1])<14)&(points[:,2]>-2.5)&(points[:,2]<0.5)]
    if len(q)<80:return None
    rng=np.random.default_rng(20261117)
    if len(q)>4000:q=q[rng.choice(len(q),4000,replace=False)]
    best=None
    for _ in range(70):
        sample=q[rng.choice(len(q),3,replace=False)]
        mat=np.column_stack((sample[:,:2],np.ones(3)))
        try:a,b,c=np.linalg.solve(mat,sample[:,2])
        except np.linalg.LinAlgError:continue
        if abs(a)>.2 or abs(b)>.2:continue
        residual=np.abs(q[:,2]-(a*q[:,0]+b*q[:,1]+c))
        inliers=residual<.12;count=int(inliers.sum())
        if best is None or count>best[0]:best=(count,inliers)
    if best is None or best[0]<max(50,len(q)//20):return None
    good=q[best[1]]
    if np.ptp(good[:,0])<4 or np.ptp(good[:,1])<3:return None
    coeff=np.linalg.lstsq(np.column_stack((good[:,:2],np.ones(len(good)))),good[:,2],rcond=None)[0]
    resid=np.abs(good[:,2]-(good[:,:2]@coeff[:2]+coeff[2]))
    return {'a':float(coeff[0]),'b':float(coeff[1]),'c':float(coeff[2]),
            'support':len(good),'median_residual_m':float(np.median(resid))}

def _clusters(points,eps,min_points=3):
    if len(points)<min_points:return []
    adj=np.sum((points[:,None,:]-points[None,:,:])**2,axis=2)<=eps**2
    seen=set();groups=[]
    for i in range(len(points)):
        if i in seen:continue
        stack=[i];seen.add(i);group=[]
        while stack:
            k=stack.pop();group.append(k)
            for j in np.flatnonzero(adj[k]):
                jj=int(j)
                if jj not in seen:seen.add(jj);stack.append(jj)
        if len(group)>=min_points:groups.append(np.asarray(group,dtype=int))
    return groups

def localize(objects,lidar,rgb,radar,ego_transform,camera_fov=100):
    frame=getattr(rgb,'frame',None)
    if frame is None or getattr(lidar,'frame',None)!=frame or getattr(radar,'frame',None)!=frame:
        raise ValueError('sensor frame mismatch')
    timestamps=[float(getattr(x,'timestamp')) for x in (rgb,lidar,radar)]
    if any(not math.isfinite(x) for x in timestamps) or max(timestamps)-min(timestamps)>.001:
        raise ValueError('sensor timestamp mismatch')
    raw=np.frombuffer(lidar.raw_data,dtype=np.float32).reshape(-1,4)[:,:3]
    li_world=_transform(raw,_rigid_matrix(lidar.transform,'get_matrix'))
    ego_inv=_rigid_matrix(ego_transform,'get_inverse_matrix')
    ego=_transform(li_world,ego_inv)
    cam=_transform(li_world,_rigid_matrix(rgb.transform,'get_inverse_matrix'))
    radar_xyz=[]
    for d in radar:
        depth,azi,alt=map(float,(d.depth,d.azimuth,d.altitude))
        if math.isfinite(depth) and math.isfinite(azi) and math.isfinite(alt) and depth>0:
            radar_xyz.append((depth*math.cos(alt)*math.cos(azi),depth*math.cos(alt)*math.sin(azi),depth*math.sin(alt)))
    radar_xyz=np.asarray(radar_xyz,dtype=float).reshape(-1,3)
    radar_world=_transform(radar_xyz,_rigid_matrix(radar.transform,'get_matrix'))
    radar_ego=_transform(radar_world,ego_inv)
    f=rgb.width/(2*math.tan(math.radians(camera_fov)/2))
    safe=np.maximum(cam[:,0],1e-6)
    u=(f*cam[:,1]/safe+rgb.width/2)/rgb.width
    v=(-f*cam[:,2]/safe+rgb.height/2)/rgb.height
    valid=(cam[:,0]>1)&(ego[:,0]>0)&np.isfinite(ego).all(axis=1)
    masks=[]
    for obj in objects:
        x1,y1,x2,y2=obj.bbox_xyxy_norm
        masks.append(valid&(u>=x1)&(u<=x2)&(v>=y1)&(v<=y2))
    counts=np.sum(masks,axis=0) if masks else np.zeros(len(raw),dtype=int)
    plane=_ground_plane(ego)
    output=[]
    for obj,boxmask in zip(objects,masks):
        in_box=np.flatnonzero(boxmask);exclusive=np.flatnonzero(boxmask&(counts==1))
        result={'id':obj.track_id,'class':obj.class_name,'confidence':float(obj.confidence),
          'bbox':list(obj.bbox_xyxy_norm),'status':'UNKNOWN','reason':'GROUND_UNRELIABLE',
          'box_point_indices':in_box.tolist(),'exclusive_point_indices':exclusive.tolist(),
          'nonground_point_indices':[],'selected_point_indices':[],'clusters':[]}
        if plane is None:output.append(result);continue
        ht=ego[exclusive,2]-(plane['a']*ego[exclusive,0]+plane['b']*ego[exclusive,1]+plane['c'])
        nonground=exclusive[(ht>.22)&(ht<3.5)]
        result['nonground_point_indices']=nonground.tolist()
        if len(nonground)<3:
            result['reason']='INSUFFICIENT_LIDAR_POINTS';output.append(result);continue
        if len(nonground)>2500:
            result['reason']='TOO_MANY_POINTS_AMBIGUOUS';output.append(result);continue
        p=ego[nonground];med_dist=float(np.median(np.linalg.norm(p[:,:2],axis=1)))
        eps=min(1.0,max(.38,.018*med_dist));groups=_clusters(p,eps)
        options=[]
        for g in groups:
            xyz=p[g];span=np.ptp(xyz,axis=0)
            if span[0]>6.5 or span[1]>3.5 or span[2]>3.0:continue
            if len(radar_ego):
                delta=np.sum((xyz[:,None,:]-radar_ego[None,:,:])**2,axis=2)
                radar_indices=np.flatnonzero(np.min(delta,axis=0)<=1.25**2);radar_hits=len(radar_indices)
            else:radar_hits=0;radar_indices=np.array([],dtype=int)
            options.append({'indices':nonground[g],'radar_indices':radar_indices,'count':len(g),'radar_hits':radar_hits,
                            'span_m':[round(float(z),3) for z in span],
                            'median_forward_m':round(float(np.median(xyz[:,0])),3)})
        options.sort(key=lambda x:(x['radar_hits']>0,x['count']),reverse=True)
        result['clusters']=[{k:v for k,v in o.items() if k not in {'indices','radar_indices'}} for o in options]
        if not options:
            result['reason']='NO_PLAUSIBLE_CLUSTER';output.append(result);continue
        if len(options)>1 and options[1]['count']>=.67*options[0]['count'] and bool(options[0]['radar_hits'])==bool(options[1]['radar_hits']):
            result['reason']='MULTIPLE_PLAUSIBLE_CLUSTERS';output.append(result);continue
        selected=options[0]['indices'];xyz=ego[selected]
        med=np.median(xyz,axis=0);ranges=np.linalg.norm(xyz[:,:2],axis=1)
        q10,q90=np.percentile(xyz,[10,90],axis=0)
        result.update(status='LOCATED_UNVALIDATED',reason='ONE_SELECTED_CLUSTER',
          selected_point_indices=selected.tolist(),cluster_count=len(selected),
          cluster_center_ego=[float(med[0]),float(-med[1]),float(med[2])],
          nearest_surface_distance_m=float(ranges.min()),surface_distance_p10_m=float(np.percentile(ranges,10)),
          longitudinal_surface_min_m=float(xyz[:,0].min()),
          xyz_min_ego=np.min(xyz,axis=0).tolist(),xyz_max_ego=np.max(xyz,axis=0).tolist(),
          spread_q10_q90_m=(q90-q10).tolist(),radar_support=options[0]['radar_hits'],
          cluster_epsilon_m=eps,radar_point_indices=options[0]['radar_indices'].tolist())
        output.append(result)
    return {'frame':frame,'plane':plane,'objects':output,'_lidar_ego':ego,'_lidar_world':li_world,'_radar_world':radar_world,'_uv':np.column_stack((u,v))}
