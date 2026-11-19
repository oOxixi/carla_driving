"""Offline replay A/B/C on existing frames; never changes inference or uses truth for assignment."""
import json,math,pathlib,types,hashlib
import numpy as np
from PIL import Image,ImageDraw
from integration.target_pointcloud_localization import localize
ROOT=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_p0_rear_final_20261117')
OUT=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_overlap_study_20261117');OUT.mkdir(exist_ok=True)
SEM=np.dtype([('x','<f4'),('y','<f4'),('z','<f4'),('cos','<f4'),('id','<u4'),('tag','<u4')])
class TF:
 def __init__(self,m):self.m=np.array(m,dtype=float)
 def get_matrix(self):return self.m
 def get_inverse_matrix(self):return np.linalg.inv(self.m)
class Radar:
 def __init__(self,d,tf,frame):
  self.transform=tf;self.frame=frame;self.timestamp=0.;a=np.frombuffer(d,dtype=np.float32).reshape(-1,4)
  self.points=[types.SimpleNamespace(velocity=float(v),azimuth=float(z),altitude=float(t),depth=float(r)) for v,z,t,r in a]
 def __iter__(self):return iter(self.points)
def read(case,run):
 p=ROOT/case/str(run);d=json.loads((p/'result.json').read_text());frame=d['frame'];lid=types.SimpleNamespace(raw_data=(p/'lidar.bin').read_bytes(),transform=TF(d['lidar_transform']),frame=frame,timestamp=0.);rgb=types.SimpleNamespace(transform=TF(d['camera_transform']),width=800,height=450,frame=frame,timestamp=0.);rad=Radar((p/'radar.bin').read_bytes(),TF(d['radar_transform']),frame);ego=TF(d['ego_transform']);objs=[types.SimpleNamespace(track_id=o['id'],class_name=o['class'],confidence=o['confidence'],bbox_xyxy_norm=o['bbox']) for o in d['predictions']];return p,d,lid,rgb,rad,ego,objs
src=pathlib.Path('integration/target_pointcloud_localization.py').read_text();assert src.count('exclusive=np.flatnonzero(boxmask&(counts==1))')==1
scores='''    score=np.full((len(objects),len(raw)),np.inf)
    for j,obj in enumerate(objects):
        x1,y1,x2,y2=obj.bbox_xyxy_norm
        score[j]=np.where(masks[j],((u-(x1+x2)/2)/((x2-x1)/2))**2+((v-(y1+y2)/2)/((y2-y1)/2))**2,np.inf)
    winner=np.argmin(score,axis=0) if objects else np.zeros(len(raw),dtype=int)
    owners=np.asarray([o.track_id for o in objects],dtype=object)[winner] if objects else np.array([],dtype=object)
'''
def patched_localize(mode):
 code=src
 if mode=='B':code=code.replace('    plane=_ground_plane(ego)',scores+'    plane=_ground_plane(ego)').replace('exclusive=np.flatnonzero(boxmask&(counts==1))','exclusive=np.flatnonzero(boxmask&((counts==1)|(owners==obj.track_id)))')
 if mode=='C':
  needle='    counts=np.sum(masks,axis=0) if masks else np.zeros(len(raw),dtype=int)'
  inject='''    if grouped_bbox is not None:
        gx1,gy1,gx2,gy2=grouped_bbox
        for j,obj in enumerate(objects):
            if obj.track_id==grouped_id:
                masks[j] |= valid&(u>=gx1)&(u<=gx2)&(v>=gy1)&(v<=gy2)
'''
  code=code.replace(needle,inject+needle)
  cscore='''    score=np.full((len(objects),len(raw)),np.inf)
    distance=np.full((len(objects),len(raw)),np.inf)
    for j,obj in enumerate(objects):
        x1,y1,x2,y2=obj.bbox_xyxy_norm
        score[j]=np.where(masks[j],((u-(x1+x2)/2)/((x2-x1)/2))**2+((v-(y1+y2)/2)/((y2-y1)/2))**2,np.inf)
        if obj.track_id in c_anchors:
            distance[j]=np.where(masks[j],np.linalg.norm(ego-np.asarray(c_anchors[obj.track_id]),axis=1),np.inf)
    order=np.argsort(distance,axis=0)
    best=order[0] if len(objects) else np.zeros(len(raw),dtype=int)
    col=np.arange(len(raw))
    d1=distance[best,col] if len(objects) else np.full(len(raw),np.inf)
    d2=distance[order[1],col] if len(objects)>1 else np.full(len(raw),np.inf)
    img_best=np.argmin(score,axis=0) if len(objects) else np.zeros(len(raw),dtype=int)
    all_anchors=np.sum(np.isfinite(distance),axis=0)==counts
    admissible=(counts>1)&all_anchors&(img_best==best)&(d1<=1.25)&((d2-d1)>=.35)
    owners=np.asarray([o.track_id for o in objects],dtype=object)[best] if len(objects) else np.array([],dtype=object)
'''
  code=code.replace('    plane=_ground_plane(ego)',cscore+'    plane=_ground_plane(ego)').replace('exclusive=np.flatnonzero(boxmask&(counts==1))','exclusive=np.flatnonzero(boxmask&((counts==1)|(admissible&(owners==obj.track_id))))')
 # Original exclusive ownership is preserved. Overlaps without consistent evidence remain ambiguous.
 env={'__name__':'integration.overlap_replay_'+mode,'__package__':'integration','grouped_bbox':None,'grouped_id':None,'c_anchors':{}};exec(compile(code,'<offline-replay-'+mode+'>','exec'),env);return env
benv=patched_localize('B');cenv=patched_localize('C')
def short(x):
 return {k:x.get(k) for k in ('id','status','reason','cluster_count','cluster_center_ego','nearest_surface_distance_m','clusters')}
def jaccard(a,b):return len(a&b)/len(a|b) if a|b else 0
def iou(a,b):
 x1,y1,x2,y2=a;u1,v1,u2,v2=b;i=max(0,min(x2,u2)-max(x1,u1))*max(0,min(y2,v2)-max(y1,v1));return i/((x2-x1)*(y2-y1)+(u2-u1)*(v2-v1)-i)
p,d,lid,rgb,rad,ego,objs=read('night',0)
a=localize(objs,lid,rgb,rad,ego);b=benv['localize'](objs,lid,rgb,rad,ego)
for old,now in zip(d['predictions'],a['objects']):
 assert old['id']==now['id'] and old['reason']==now['reason'] and old['box_point_indices']==now['box_point_indices'] and old['exclusive_point_indices']==now['exclusive_point_indices'] and old['selected_point_indices']==now['selected_point_indices'],old['id']
isolated=[localize([o],lid,rgb,rad,ego)['objects'][0] for o in objs[1:3]]
print('ORIGINAL REPRODUCED');print('A',json.dumps([short(x) for x in a['objects']],ensure_ascii=False));print('B',json.dumps([short(x) for x in b['objects']],ensure_ascii=False));print('ISOLATED',json.dumps([short(x) for x in isolated],ensure_ascii=False));print('isolated_selected_overlap',jaccard(set(isolated[0]['selected_point_indices']),set(isolated[1]['selected_point_indices'])))
x,y=isolated;overlap=jaccard(set(x['selected_point_indices']),set(y['selected_point_indices']));dx=abs(x['cluster_center_ego'][0]-y['cluster_center_ego'][0]) if x.get('cluster_center_ego') and y.get('cluster_center_ego') else float('inf');box_iou=iou(objs[1].bbox_xyxy_norm,objs[2].bbox_xyxy_norm)
can_group=box_iou>=.90 and all(q['status']=='LOCATED_UNVALIDATED' and q['cluster_count']>=5 for q in isolated) and overlap>=.8 and dx<.5
assert can_group
# Create a physical-object group, preserving both IDs as aliases. Higher detector confidence is a display representative, not a truth label.
rep=max(objs[1:3],key=lambda o:o.confidence);alias=min(objs[1:3],key=lambda o:o.confidence);cenv['grouped_id']=rep.track_id;cenv['grouped_bbox']=alias.bbox_xyxy_norm;cobjs=[o for o in objs if o.track_id!=alias.track_id];c=cenv['localize'](cobjs,lid,rgb,rad,ego)
assert all(next(q for q in a['objects'] if q['id']==z['id'])['selected_point_indices']==z['selected_point_indices'] for z in c['objects'] if z['id']!=rep.track_id)
# Make a truth-independent decision above; only now audit individual points against semantic LiDAR.
raw=np.frombuffer(lid.raw_data,dtype=np.float32).reshape(-1,4)[:,:3];sem=np.fromfile(p/'semantic_lidar.bin',dtype=SEM);sp=np.column_stack((sem['x'],sem['y'],sem['z']));lw=np.c_[raw,np.ones(len(raw))]@np.array(d['lidar_transform']).T;sw=np.c_[sp,np.ones(len(sp))]@np.array(d['semantic_transform']).T
aw={z['id']:z for z in a['objects']};bw={z['id']:z for z in b['objects']};cw={z['id']:z for z in c['objects']};common=sorted(set(aw['C-0002']['box_point_indices'])&set(aw['C-0003']['box_point_indices']));assert len(common)==53
role_by_id={v:k for k,v in d['evaluation']['gt_actor_ids'].items()};cam=lw@np.linalg.inv(np.array(d['camera_transform'])).T;f=800/(2*math.tan(math.radians(50)));px=f*cam[:,1]/np.maximum(cam[:,0],1e-9)+400;py=-f*cam[:,2]/np.maximum(cam[:,0],1e-9)+225
rows=[]
for idx in common:
 ds=np.linalg.norm(sw[:,:3]-lw[idx,:3],axis=1);j=int(np.argmin(ds));actor=int(sem['id'][j]) if ds[j]<=.08 else None;tag=int(sem['tag'][j]) if actor is not None else None;truth=role_by_id.get(actor,'environment' if actor is not None else 'unmatched');bo=next((z['id'] for z in b['objects'] if idx in z['exclusive_point_indices']),'AMBIGUOUS');co='GROUP(C-0002,C-0003)' if idx in cw[rep.track_id]['exclusive_point_indices'] else 'AMBIGUOUS'
 rows.append({'point_index':idx,'pixel_x':float(px[idx]),'pixel_y':float(py[idx]),'depth_camera_m':float(cam[idx,0]),'ego_xyz_carla':(lw[idx]@ego.get_inverse_matrix().T)[:3].tolist(),'truth_role':truth,'semantic_tag':tag,'semantic_match_error_m':float(ds[j]) if actor is not None else None,'A':'EXCLUDED_OVERLAP','B':bo,'C':co,'B_selected':bool(any(idx in z['selected_point_indices'] for z in b['objects'])),'C_stage':'SELECTED' if idx in cw[rep.track_id]['selected_point_indices'] else ('GROUND_OR_HEIGHT_FILTERED' if idx not in cw[rep.track_id]['nonground_point_indices'] else 'AMBIGUOUS_NOT_SELECTED_CLUSTER')})
assert len(rows)==53 and all(z['B']!='AMBIGUOUS' for z in rows)
def sem_truth(indices):
 counts={'C':0,'other_vehicle':0,'environment':0,'unmatched':0}
 for i in indices:
  ds=np.linalg.norm(sw[:,:3]-lw[i,:3],axis=1);j=int(np.argmin(ds));actor=int(sem['id'][j]) if ds[j]<=.08 else None
  k='C' if actor==d['evaluation']['gt_actor_ids']['C'] else ('unmatched' if actor is None else ('other_vehicle' if actor in role_by_id else 'environment'));counts[k]+=1
 return counts
results={}
for name,pred,ids in [('A',a['objects'],['C-0002','C-0003']),('B',b['objects'],['C-0002','C-0003']),('C',c['objects'],[rep.track_id])]:
 picks=[z for z in pred if z['id'] in ids];selected=sorted(set(i for z in picks for i in z['selected_point_indices']));results[name]={'objects':[short(z) for z in picks],'selected_point_count':len(selected),'selected_truth':sem_truth(selected),'assigned_53':sum(1 for z in rows if (z[name]!='EXCLUDED_OVERLAP' and z[name]!='AMBIGUOUS'))}
# Review both physical IDs on the five independently recorded partial-occlusion frames.
controls=[]
for n in range(5):
 q,od,ol,og,orr,oe,oo=read('occlusion',n);aa=localize(oo,ol,og,orr,oe);bb=benv['localize'](oo,ol,og,orr,oe)
 for prev,new in zip(od['predictions'],aa['objects']):assert prev['reason']==new['reason'] and prev['selected_point_indices']==new['selected_point_indices']
 boxes=[set(z['box_point_indices']) for z in aa['objects']];shared=set(i for k,a0 in enumerate(boxes) for b0 in boxes[k+1:] for i in a0&b0)
 controls.append({'repeat':n,'shared_points':len(shared),'A_accepted':sum(len(z['selected_point_indices']) for z in aa['objects']),'B_accepted':sum(len(z['selected_point_indices']) for z in bb['objects']),'changed_status':[(q['id'],q['reason'],z['reason']) for q,z in zip(aa['objects'],bb['objects']) if q['reason']!=z['reason']],'C_policy':'different overlapping detections: retain A and mark shared points AMBIGUOUS; no group was proposed'})
# Preserve additional four points only present in one original detector box.
other_idx=sorted((set(aw['C-0002']['box_point_indices'])|set(aw['C-0003']['box_point_indices']))-set(common))
extras=[{'point_index':int(i),'pixel_x':float(px[i]),'pixel_y':float(py[i]),'A_owner':next((q['id'] for q in a['objects'] if i in q['exclusive_point_indices']),'AMBIGUOUS'),'C_owner':'GROUP(C-0002,C-0003)' if i in cw[rep.track_id]['exclusive_point_indices'] else 'AMBIGUOUS'} for i in other_idx]
assert len(extras)==4 and all(z['C_owner']!='AMBIGUOUS' for z in extras)
# Additional localized vehicles should retain their original selected clusters.
for zz in c['objects']:
 if zz['id']!=rep.track_id:assert zz['selected_point_indices']==aw[zz['id']]['selected_point_indices']
report={'case':'night','run':0,'frame':d['frame'],'original_algorithm_sha256':hashlib.sha256(src.encode()).hexdigest(),'timestamps':'replay uses recorded equal frame IDs and placeholder equal timestamps because original timestamps were not saved; checks only, not measurement of timing','boxes':{q.track_id:{'bbox':q.bbox_xyxy_norm,'class':q.class_name,'confidence':q.confidence} for q in objs},'pair_iou':box_iou,'cluster_overlap_jaccard':overlap,'isolated_cluster_depth_difference_m':dx,'group_representative':rep.track_id,'group_alias':alias.track_id,'group_policy':'IoU >= .90, each single-box run finds >= 5 points in accepted cluster, selected-point Jaccard >= .80, forward center difference < .5 m; values are exploratory heuristics, no history and not validated deployment rules.','ground_truth_use':'Semantic actor IDs are read only after A/B/C decisions; matching <=0.08m.','overlap_points':rows,'exclusive_points':extras,'results':results,'control_occlusion':controls,'original_unaffected_selected_clusters_preserved':True,'limitations':['Near-identical boxes can still conceal multiple vehicles; evidence is insufficient for general validation.','C groups two detection IDs; no unique physical ownership between those labels is claimed. For other overlapping boxes C requires 2D and 3D winners to agree, closest cluster <=1.25m, gap >=0.35m and each box with a >=5-point reference cluster; otherwise AMBIGUOUS.','The arbitrary thresholds are provisional and need independent cases.','No original point-level timestamps or moving-target history was saved.','Nearest surface in the target failed original sample lacks stored actor geometry, so no precise distance error is computed.']}
(OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');Image.open(p/'camera.png').save(OUT/'scene.png')
print('SUMMARY',json.dumps({k:report[k] for k in ('pair_iou','cluster_overlap_jaccard','isolated_cluster_depth_difference_m','group_representative','results','control_occlusion')},ensure_ascii=False))
# Counter-check the proposal on the five distinct overlap/occlusion test frames.
controls=[]
for n in range(5):
 cp,cd,cl,cr,crad,ce,co=read('occlusion',n);aa=localize(co,cl,cr,crad,ce);bb=benv['localize'](co,cl,cr,crad,ce);cenv['grouped_bbox']=None;cenv['grouped_id']=None
 anchors={}
 for ob in co:
  isolated0=localize([ob],cl,cr,crad,ce)['objects'][0]
  if isolated0['status']=='LOCATED_UNVALIDATED' and isolated0['cluster_count']>=5:
   x,y,z=isolated0['cluster_center_ego'];anchors[ob.track_id]=[x,-y,z]
 cenv['c_anchors']=anchors;cc=cenv['localize'](co,cl,cr,crad,ce)
 groups=[];pairs=[]
 for j in range(len(co)):
  for k in range(j+1,len(co)):
   shared=set(aa['objects'][j]['box_point_indices'])&set(aa['objects'][k]['box_point_indices'])
   if not shared:continue
   iou0=iou(co[j].bbox_xyxy_norm,co[k].bbox_xyxy_norm);pairs.append({'a':co[j].track_id,'b':co[k].track_id,'shared':len(shared),'iou':iou0})
   if iou0>=.9:
    pa=localize([co[j]],cl,cr,crad,ce)['objects'][0];pb=localize([co[k]],cl,cr,crad,ce)['objects'][0];jj=jaccard(set(pa['selected_point_indices']),set(pb['selected_point_indices']));dd=abs(pa['cluster_center_ego'][0]-pb['cluster_center_ego'][0]) if pa.get('cluster_center_ego') and pb.get('cluster_center_ego') else float('inf')
    if all(z['status']=='LOCATED_UNVALIDATED' and z['cluster_count']>=5 for z in (pa,pb)) and jj>=.8 and dd<.5:groups.append([co[j].track_id,co[k].track_id])
 assert not groups,'Control frame triggered duplicate grouping and needs explicit review'
 semc=np.fromfile(cp/'semantic_lidar.bin',dtype=SEM);spc=np.column_stack((semc['x'],semc['y'],semc['z']));swc=np.c_[spc,np.ones(len(spc))]@np.asarray(cd['semantic_transform']).T;lp=np.frombuffer(cl.raw_data,dtype=np.float32).reshape(-1,4)[:,:3];lwc=np.c_[lp,np.ones(len(lp))]@np.asarray(cd['lidar_transform']).T
 gt_by_det={e['id']:e['gt_match']['role'] if e['gt_match'] else None for e in cd['evaluation']['detections']};ids=cd['evaluation']['gt_actor_ids'];actor_ids=set(ids.values())
 def audit(indices,role):
  out={'target':0,'other_vehicle':0,'environment':0,'unmatched_semantic':0,'unmatched_detection':0}
  for ix in indices:
   if role is None:out['unmatched_detection']+=1;continue
   ds=np.linalg.norm(swc[:,:3]-lwc[ix,:3],axis=1);jj=int(np.argmin(ds));v=int(semc['id'][jj]) if ds[jj]<=.08 else None
   category='unmatched_semantic' if v is None else ('target' if v==ids[role] else ('other_vehicle' if v in actor_ids else 'environment'));out[category]+=1
  return out
 auditing={}
 for label,rr in [('A',aa),('B',bb),('C',cc)]:
  totals={'target':0,'other_vehicle':0,'environment':0,'unmatched_semantic':0,'unmatched_detection':0}
  for obj in rr['objects']:
   out=audit(obj['selected_point_indices'],gt_by_det[obj['id']])
   for key,val in out.items():totals[key]+=val
  auditing[label]=totals
 same_owners=all(set(o['exclusive_point_indices']).issubset(set(next(z for z in bb['objects'] if z['id']==o['id'])['exclusive_point_indices'])) for o in aa['objects'])
 controls.append({'repeat':n,'pairs':pairs,'grouped_pairs':groups,'selected_truth':auditing,'B_preserves_A_exclusive_ownership':same_owners,'B_original_selected_preserved':all(set(o['selected_point_indices']).issubset(set(next(z for z in bb['objects'] if z['id']==o['id'])['selected_point_indices'])) for o in aa['objects']),'C_original_selected_preserved':all(set(o['selected_point_indices']).issubset(set(next(z for z in cc['objects'] if z['id']==o['id'])['selected_point_indices'])) for o in aa['objects']),'C_preserves_A_exclusive_ownership':all(set(o['exclusive_point_indices']).issubset(set(next(z for z in cc['objects'] if z['id']==o['id'])['exclusive_point_indices'])) for o in aa['objects']),'C_ambiguous_shared':len(set(i for k,a0 in enumerate([set(z['box_point_indices']) for z in aa['objects']]) for b0 in [set(z['box_point_indices']) for z in aa['objects']][k+1:] for i in a0&b0)-set(i for z in cc['objects'] for i in z['exclusive_point_indices']))})
report['control_occlusion']=controls;(OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('CONTROL_AUDIT',json.dumps(controls,ensure_ascii=False))
