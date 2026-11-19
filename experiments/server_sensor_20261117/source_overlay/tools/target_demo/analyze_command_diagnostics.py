"""Offline frame diagnosis; actor truth is used only for evaluation."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from integration.rgb_detector import OnnxYoloDetector, _Letterbox

ROOT = Path('artifacts/runtime/command_frame_diagnostics_20261112')
def h(points):
    return np.column_stack((np.asarray(points)[:, :3], np.ones(len(points))))
def transform(points, mat):
    return (h(points) @ np.asarray(mat).T)[:, :3]
def iou(box, boxes):
    x1=np.maximum(box[0], boxes[:,0]); y1=np.maximum(box[1],boxes[:,1])
    x2=np.minimum(box[2], boxes[:,2]); y2=np.minimum(box[3],boxes[:,3])
    inter=np.maximum(x2-x1,0)*np.maximum(y2-y1,0)
    area=np.maximum(box[2]-box[0],0)*np.maximum(box[3]-box[1],0)
    areas=np.maximum(boxes[:,2]-boxes[:,0],0)*np.maximum(boxes[:,3]-boxes[:,1],0)
    return inter/np.maximum(area+areas-inter,1e-9)
for distance in (40,60):
    p=ROOT/str(distance)/'capture'; m=json.loads((p/'metadata.json').read_text()); image=Image.open(p/'camera_rgb.png').convert('RGB')
    assert m['frame']==m['detector_frame']==m['world_snapshot_frame']
    rgb=m['rgb']; lidar=m['lidar']; radar=m['radar']; cam_inv=np.linalg.inv(np.asarray(rgb['world_matrix']))
    f=rgb['width']/(2*math.tan(math.radians(rgb['fov'])/2))
    def project(world):
        c=transform(world,cam_inv); return np.column_stack((f*c[:,1]/c[:,0]+rgb['width']/2, -f*c[:,2]/c[:,0]+rgb['height']/2,c[:,0]))
    lidar_world=transform(np.load(p/'lidar_xyzi.npy'),lidar['world_matrix']); projected=project(lidar_world)
    raw=np.load(p/'yolo_raw.npy'); rows=np.squeeze(raw).T; t=m['detector_letterbox']; xywh=rows[:,:4]
    boxes=np.column_stack((xywh[:,0]-xywh[:,2]/2,xywh[:,1]-xywh[:,3]/2,xywh[:,0]+xywh[:,2]/2,xywh[:,1]+xywh[:,3]/2))
    boxes[:,[0,2]]=(boxes[:,[0,2]]-t['pad_x'])/t['scale']; boxes[:,[1,3]]=(boxes[:,[1,3]]-t['pad_y'])/t['scale']
    scores=rows[:,4:]; best_classes=np.argmax(scores,axis=1)
    detector=OnnxYoloDetector.__new__(OnnxYoloDetector); detector.iou_threshold=.45
    decoded={}
    for threshold in (.05,.1,.2,.35):
        detector.confidence_threshold=threshold
        ds=detector._decode(raw,_Letterbox(**t))
        decoded[str(threshold)]=[{'class':x.class_name,'confidence':round(x.confidence,5),'box_px':[round(v*s,2) for v,s in zip(x.bbox_xyxy_norm,[rgb['width'],rgb['height'],rgb['width'],rgb['height']])]} for x in ds]
    returns=radar['returns']; rp=[]
    for r in returns:
        dep,azi,alt=r['depth'],r['azimuth'],r['altitude']
        rp.append([dep*math.cos(alt)*math.cos(azi),dep*math.cos(alt)*math.sin(azi),dep*math.sin(alt)])
    radar_world=transform(rp,radar['world_matrix']) if rp and radar['world_matrix'] else np.empty((0,3))
    result={'frame':m['frame'],'rgb_lidar_dt':abs(rgb['timestamp']-lidar['timestamp']),'raw_shape':list(raw.shape),'lidar_count':len(lidar_world),'radar_count':len(returns),'detections_at_thresholds':decoded,'actors':[]}
    draw=ImageDraw.Draw(image); colors=['red','yellow','cyan','magenta']
    for ai,a in enumerate(m['evaluation_only_ground_truth_actors']):
        if a['role_name'].endswith('ego'): continue
        verts=np.asarray(a['vertices_world']); proj=project(verts)
        if np.any(proj[:,2]<=0): continue
        bb=np.array([proj[:,0].min(),proj[:,1].min(),proj[:,0].max(),proj[:,1].max()]); ious=iou(bb,boxes)
        actor_inv=np.linalg.inv(np.asarray(a['world_matrix'])); av=transform(verts,actor_inv); lo=av.min(axis=0); hi=av.max(axis=0)
        lp=transform(lidar_world,actor_inv); inside=np.all((lp>=lo)&(lp<=hi),axis=1); expand=np.all((lp>=lo-.25)&(lp<=hi+.25),axis=1)
        inproj=(projected[:,2]>0)&(projected[:,0]>=bb[0])&(projected[:,0]<=bb[2])&(projected[:,1]>=bb[1])&(projected[:,1]<=bb[3])
        ra=transform(radar_world,actor_inv) if len(radar_world) else radar_world
        rinside=np.all((ra>=lo-.25)&(ra<=hi+.25),axis=1) if len(ra) else []
        mask=ious>=.1
        best=None
        if np.any(mask):
            idxs=np.where(mask)[0]; idx=idxs[np.argmax(scores[idxs,2])]
            best={'car_score':float(scores[idx,2]),'best_class':int(best_classes[idx]),'best_class_score':float(scores[idx,best_classes[idx]]),'iou':float(ious[idx]),'box':[round(float(x),1) for x in boxes[idx]]}
        actor={'role':a['role_name'],'type':a['type_id'],'gt_projected_bbox_px':[round(float(x),1) for x in bb], 'camera_forward_m':round(float(np.mean(proj[:,2])),2),'bbox_size_px':[round(float(bb[2]-bb[0]),1),round(float(bb[3]-bb[1]),1)],'lidar_inside_3d_box':int(inside.sum()),'lidar_inside_3d_box_plus_025m':int(expand.sum()),'lidar_in_projected_bbox':int(inproj.sum()),'radar_inside_box_plus_025m':int(np.sum(rinside)),'best_car_score_with_iou_ge_01':best}
        result['actors'].append(actor); draw.rectangle(tuple(bb),outline=colors[ai%len(colors)],width=2); draw.text((bb[0],max(0,bb[1]-11)),a['role_name'].split(':')[-1],fill=colors[ai%len(colors)])
    image.save(p/'evaluation_overlay.png'); (p/'analysis.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps(result,ensure_ascii=False))
