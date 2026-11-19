"""Evaluation-only RGB/LiDAR/radar association; no control authority."""
from __future__ import annotations
import math
import numpy as np
from .camera_lidar_association import _rigid_matrix

class ShadowSensorFusion:
    """Require exclusive image membership, cross-sensor proximity and persistence."""
    def __init__(self):
        self.history={}
        self.last_frame=None

    def update(self,objects,lidar,rgb,radar,ego_transform,fov,world_map=None):
        frame=getattr(rgb,'frame',None)
        if (frame is None or getattr(lidar,'frame',None)!=frame or radar is None
            or getattr(radar,'frame',None)!=frame):
            self.history={};self.last_frame=None
            return [{'track_id':o.track_id,'status':'UNSYNCED','position_m':None} for o in objects]
        times=[getattr(s,'timestamp',None) for s in (rgb,lidar,radar)]
        if any(t is None or not math.isfinite(float(t)) for t in times) or max(times)-min(times)>.001:
            self.history={};self.last_frame=None
            return [{'track_id':o.track_id,'status':'UNSYNCED','position_m':None} for o in objects]
        if self.last_frame is not None and frame!=self.last_frame+1:self.history={}
        self.last_frame=frame
        cam_inv=_rigid_matrix(rgb.transform,'get_inverse_matrix')
        ego_inv=_rigid_matrix(ego_transform,'get_inverse_matrix')
        ego_world=_rigid_matrix(ego_transform,'get_matrix')
        lidar_world=_rigid_matrix(lidar.transform,'get_matrix')
        radar_world=_rigid_matrix(radar.transform,'get_matrix')
        lp=np.frombuffer(lidar.raw_data,dtype=np.float32).reshape(-1,4)[:,:3]
        detections=list(radar)
        rp=[];vel=[]
        for d in detections:
            depth,azi,alt,velocity=(float(getattr(d,k)) for k in ('depth','azimuth','altitude','velocity'))
            if not all(math.isfinite(x) for x in (depth,azi,alt,velocity)) or depth<=0:continue
            rp.append((depth*math.cos(alt)*math.cos(azi),depth*math.cos(alt)*math.sin(azi),depth*math.sin(alt)));vel.append(velocity)
        rp=np.asarray(rp,dtype=float).reshape(-1,3);vel=np.asarray(vel)
        def transform(points,matrix):
            return (np.column_stack((points,np.ones(len(points))))@matrix.T)[:,:3]
        lw=transform(lp,lidar_world);rw=transform(rp,radar_world)
        def project(world):
            camera=transform(world,cam_inv);ego=transform(world,ego_inv)
            f=rgb.width/(2*math.tan(math.radians(float(fov))/2));depth=camera[:,0];safe=np.maximum(depth,.001)
            return np.column_stack(((f*camera[:,1]/safe+rgb.width/2)/rgb.width,(-f*camera[:,2]/safe+rgb.height/2)/rgb.height,depth)),ego
        li,le=project(lw);ri,re=project(rw)
        visual=[o for o in objects if o.class_name.lower() in {'car','truck','bus'} and o.track_id]
        def memberships(pix):
            masks=[]
            for o in visual:
                x1,y1,x2,y2=o.bbox_xyxy_norm
                masks.append((pix[:,2]>1)&(pix[:,0]>=x1)&(pix[:,0]<=x2)&(pix[:,1]>=y1)&(pix[:,1]<=y2))
            return np.asarray(masks,dtype=bool).reshape((len(visual),len(pix)))
        lmask=memberships(li);rmask=memberships(ri)
        lc=lmask.sum(axis=0);rc=rmask.sum(axis=0);new={};out=[]
        ids=[o.track_id for o in visual]
        for index,o in enumerate(visual):
            if ids.count(o.track_id)>1:
                out.append({'track_id':o.track_id,'status':'DUPLICATE_TRACK','position_m':None})
                continue
            ls=lmask[index]&(lc==1)&(le[:,0]>0)&(le[:,2]>-.25)&(le[:,2]<3)
            rs=rmask[index]&(rc==1)&(re[:,0]>0)&(re[:,2]>-.25)&(re[:,2]<3)
            aa=le[ls];bb=re[rs];rv=vel[rs]
            item={'track_id':o.track_id,'confidence':o.confidence,'bbox':o.bbox_xyxy_norm,'lidar_unique':len(aa),'radar_unique':len(bb),'radar_ambiguous':int((rmask[index]&(rc>1)).sum()),'position_m':None,'radial_velocity_mps':None,'lane_relation':'UNKNOWN','status':'NO_CROSS_SENSOR_PAIR','source':'UNVALIDATED_SHADOW_RGB_LIDAR_RADAR'}
            if len(aa) and len(bb):
                delta=np.linalg.norm(aa[:,None,:]-bb[None,:,:],axis=2);pairs=np.argwhere(delta<=1.25)
                if len(pairs):
                    # Require at least one nearby return from each independent sensor.
                    xy=np.concatenate((aa[np.unique(pairs[:,0])],bb[np.unique(pairs[:,1])]),axis=0)
                    pos=np.median(xy,axis=0);world=transform(pos.reshape(1,3),ego_world)[0]
                    old=self.history.get(o.track_id);streak=1
                    box=o.bbox_xyxy_norm
                    if old:
                        a=old['box'];inter=max(0,min(a[2],box[2])-max(a[0],box[0]))*max(0,min(a[3],box[3])-max(a[1],box[1]))
                        union=(a[2]-a[0])*(a[3]-a[1])+(box[2]-box[0])*(box[3]-box[1])-inter
                        if old['frame']==frame-1 and union>0 and inter/union>=.4 and np.linalg.norm(old['world'][:2]-world[:2])<=1.5:
                            streak=old['streak']+1
                    new[o.track_id]={'frame':frame,'world':world,'streak':streak,'box':box}
                    item.update(status='TEMPORAL_PENDING',streak=streak,pair_count=len(pairs))
                    if streak>=3:
                        item.update(status='FUSED_UNVALIDATED',position_m=[float(pos[0]),float(-pos[1]),float(pos[2])],distance_m=float(np.linalg.norm(pos[:2])),radial_velocity_mps=float(np.median(rv[np.unique(pairs[:,1])])),lane_relation=self._lane(pos,ego_transform,world_map))
            out.append(item)
        self.history=new
        return out

    @staticmethod
    def _lane(pos,ego_transform,world_map):
        if world_map is None:return 'UNKNOWN'
        try:
            import carla
            ego_wp=world_map.get_waypoint(ego_transform.location,project_to_road=True)
            loc=ego_transform.transform(carla.Location(x=float(pos[0]),y=float(pos[1]),z=0))
            wp=world_map.get_waypoint(loc,project_to_road=True)
            if not ego_wp or not wp or loc.distance(wp.transform.location)>=max(.5,float(wp.lane_width)/2-.5):return 'UNKNOWN'
            if wp.road_id==ego_wp.road_id:return 'SAME' if wp.lane_id==ego_wp.lane_id else 'OTHER'
            near=[w for w in ego_wp.next(max(.5,float(pos[0]))) if loc.distance(w.transform.location)<max(.5,float(w.lane_width)/2-.5)]
            return 'SAME' if len(near)==1 else 'UNKNOWN'
        except (ImportError,AttributeError,RuntimeError,TypeError):return 'UNKNOWN'
