"""Generate an isolated experimental copy from the exact scheme-C source."""
from pathlib import Path
import hashlib
root=Path('/home/tiaozhansai/carla-lane-association-20261117');out=Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_adaptive_development_20261117');src=(root/'integration/target_group_localization.py').read_text()
s=src.replace('from .camera_lidar_association','from integration.camera_lidar_association').replace('from .target_pointcloud_localization','from integration.target_pointcloud_localization').replace('from .duplicate_detection_grouper','from integration.duplicate_detection_grouper')
s=s.replace('def localize_groups(objects,lidar,rgb,radar,ego_transform,camera_fov=100,history=None):','def localize_groups(objects,lidar,rgb,radar,ego_transform,camera_fov=100,history=None,alpha=1.0,fixed_radius=None,depth_profile=None,geometry_profile=None):')
old="p=ego[nonground];med_dist=float(np.median(np.linalg.norm(p[:,:2],axis=1)));eps=min(1.0,max(.38,.018*med_dist));connected=_clusters(p,eps);options=[]"
new="p=ego[nonground];med_dist=float(np.median(np.linalg.norm(p[:,:2],axis=1)));base_eps=min(1.0,max(.38,.018*med_dist));eps=float(fixed_radius) if fixed_radius is not None else min(1.20,max(.38,alpha*base_eps));tau=_limit(depth_profile,med_dist);connected=_depth_components(p,eps,tau);options=[];rejected_geometry=[];row['experimental_epsilon_m']=eps;row['experimental_depth_limit_m']=tau"
assert s.count(old)==1;s=s.replace(old,new)
old="            if span[0]>6.5 or span[1]>3.5 or span[2]>3.0:continue\n            eligible_radar="
new="""            if span[0]>6.5 or span[1]>3.5 or span[2]>3.0:continue
            radial=np.linalg.norm(pts,axis=1);depth_spread=float(np.ptp(radial));geo_limit=_limit(geometry_profile,med_dist)
            if geo_limit is not None and depth_spread>geo_limit:
                rejected_geometry.append({'count':len(component),'radial_spread_m':depth_spread,'limit_m':geo_limit});continue
            eligible_radar="""
assert s.count(old)==1;s=s.replace(old,new)
old="        options.sort(key=lambda x:(x['radar_hits']>0,x['count']),reverse=True);row['clusters']=[{k:v for k,v in opt.items() if k not in ('indices','radar_indices')} for opt in options]"
new="""        options.sort(key=lambda x:(x['radar_hits']>0,x['count']),reverse=True);row['clusters']=[{k:v for k,v in opt.items() if k not in ('indices','radar_indices')} for opt in options]
        if geometry_profile is not None:
            row['geometry_rejected']=rejected_geometry
            if rejected_geometry:
                row['reason']='GEOMETRY_REJECTED_OR_AMBIGUOUS';result.append(row);continue"""
assert s.count(old)==1;s=s.replace(old,new)
helper='''\ndef _limit(profile,r):
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
'''
s=s.replace('\ndef localize_groups(',helper+'\ndef localize_groups(',1)
needle="    return {'frame':frame,'groups':result,'pair_evidence':evidence,'ground_plane':plane,'point_state':point_state,'point_owner':final_owner,'point_reason':reason,'lidar_ego':ego,'lidar_world':world,'radar_world':radar_world,'uv':np.column_stack((u,v))}"
assert s.count(needle)==1
s=s.replace(needle,"""    for row in result:
        if row['status']=='LOCATED_UNVALIDATED':row['diagnostic_outcome']='CANDIDATE_UNVALIDATED'
        elif row['reason'] in ('MULTIPLE_PLAUSIBLE_CLUSTERS','GEOMETRY_REJECTED_OR_AMBIGUOUS'):row['diagnostic_outcome']='AMBIGUOUS'
        else:row['diagnostic_outcome']='FAILED'
"""+needle)
(out/'experimental_group_localization.py').write_text(s);(out/'source_sha256.txt').write_text(hashlib.sha256(src.encode()).hexdigest()+'  integration/target_group_localization.py\n');print('experimental copy created; source sha256',hashlib.sha256(src.encode()).hexdigest())
