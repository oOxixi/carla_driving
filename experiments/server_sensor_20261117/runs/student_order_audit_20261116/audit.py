import copy,glob,itertools,json,math,os,time,traceback,urllib.request
from pathlib import Path
import numpy as np,torch
from challenge.planner.student_backend import StudentBackend
from challenge.student.contract import BEHAVIORS
from request_guard import adapt_or_block
ROOT=Path('/home/tiaozhansai/carla-driving-target-and-provement')
PREV=ROOT/'artifacts/runtime/student_teacher_20261116'
OUT=Path(__file__).resolve().parent
student=StudentBackend(weights='/home/tiaozhansai/carla-driving-challenge/artifacts/challenge/distillation/a3_b1_closeout_robust_fp32_v3/student_v0_fp32_candidate.pt')
data={'mode':'offline_saved_frame_diagnostic','status':'RUNNING','cases':{}}
def save():
 tmp=OUT/'results.tmp';tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));tmp.replace(OUT/'results.json')
def teacher(request):
 body=json.dumps(request,ensure_ascii=False).encode()
 r=urllib.request.Request('http://127.0.0.1:28781/infer',data=body,headers={'Content-Type':'application/json'})
 return json.loads(urllib.request.urlopen(r,timeout=35).read())
def associations(req,obs):
 cam=np.linalg.inv(np.asarray(obs['camera_world_matrix']));w,h=obs['camera_width'],obs['camera_height']
 f=w/(2*math.tan(math.radians(obs['camera_fov'])/2))
 result={}
 for item in req['target_grounding']['visual_candidates']:
  box=[v*[w,h,w,h][i] for i,v in enumerate(item['bbox_xyxy_norm'])]
  scores={}
  for a in obs['truth_for_evaluation_only']:
   if a['role_name'].endswith(':ego'):continue
   v=np.asarray(a['vertices_world']);q=np.column_stack((v,np.ones(len(v))))@cam.T
   if (q[:,0]<=0).any():continue
   u=f*q[:,1]/q[:,0]+w/2;z=-f*q[:,2]/q[:,0]+h/2;b=[min(u),min(z),max(u),max(z)]
   inter=max(0,min(box[2],b[2])-max(box[0],b[0]))*max(0,min(box[3],b[3])-max(box[1],b[1]))
   union=(box[2]-box[0])*(box[3]-box[1])+(b[2]-b[0])*(b[3]-b[1])-inter
   scores[a['role_name'].split(':')[-1]]=round(float(inter/max(union,1e-9)),3)
  result[item['target_id']]=scores
 return result
def verdict(target,all_iou,expected):
 if not target:return 'ABSTAIN'
 scores=all_iou.get(target,{})
 hits=[k for k,v in scores.items() if v>=0.3]
 if len(hits)!=1:return 'INDETERMINATE'
 return 'EXPECTED' if hits[0]==expected else 'OTHER_VEHICLE'
events=[json.loads(l) for l in (PREV/'student_inferences.jsonl').open()]
for case in ('40m','60m','occlusion'):
 d=PREV/(case+'_student')
 logfile=next(d.glob('EXPERIMENT*.jsonl'))
 sub=next(x for l in logfile.open() if (x:=json.loads(l)).get('record_type')=='canonical_routing' and x.get('phase')=='SUBMIT')
 initial=sub['payload']['orchestration']['model_request'];rid=initial['request_id']
 event=next(e for e in events if e['input_original']['request_id']==rid)
 original=event['input_original'];frame=original['scene_summary']['frame_id']
 obs=next(x for l in (d/'evaluation/shadow_and_evaluation_truth.jsonl').open() if (x:=json.loads(l)).get('frame')==frame)
 overlap=associations(original,obs)
 expected='occluder_near' if case=='occlusion' else 'lead_target'
 _,guard=adapt_or_block(original)
 ids=[t['target_id'] for t in original['targets']]
 section={'frame':frame,'original_targets':original['targets'],'input_image_ref':original['rgb_ref'],'expected_role':expected,'projection_iou':overlap,'guard':guard,'permutations':[]}
 data['cases'][case]=section;save()
 for order in itertools.permutations(ids):
  req=copy.deepcopy(original)
  req['targets']=[next(t for t in original['targets'] if t['target_id']==i) for i in order]
  visual=original['target_grounding']['visual_candidates']
  req['target_grounding']['visual_candidates']=[next(v for v in visual if v['target_id']==i) for i in order]
  req['target_grounding']['candidate_ids']=list(order)
  for t in req['targets']:
   if t['distance_m'] is None:t['distance_m']=0.0
  req['created_at_ns']=time.monotonic_ns();req['deadline_ns']=req['created_at_ns']+30_000_000_000
  row={'order':list(order),'actual_unknown_distances_imputed_zero':True,'teacher':None,'student':None}
  try:
   r=copy.deepcopy(req);r.pop('target_grounding',None);r['rgb_ref']=str(ROOT/r['rgb_ref'])
   tens=student._preprocess(r)
   with torch.inference_mode():outs=student.model(*tens.as_tuple())
   raw=outs['target_pointer_logits'][0,0];raw_index=int(raw.argmax())
   p=student.infer(r);step=p['steps'][0];target=(step.get('target') or {}).get('target_id')
   row['student']={'target_id':target,'raw_pointer_index':raw_index,'raw_scores':[round(float(x),4) for x in raw],
      'raw_behavior':BEHAVIORS[int(outs['behavior_logits'][0,0].argmax())],'decoded_behavior':step['behavior'],
      'confidence':p['confidence'],'is_first':target==order[0] if target else False,
      'verdict':verdict(target,overlap,expected)}
  except Exception as e:row['student']={'error':str(e)}
  try:
   p=teacher(req);g=p.get('model_grounding') or {};target=g.get('target_id')
   row['teacher']={'target_id':target,'raw_choice':g.get('raw_choice'),'abstained':g.get('abstained'),
      'is_first':target==order[0] if target else False,'verdict':verdict(target,overlap,expected)}
  except Exception as e:row['teacher']={'error':f'{type(e).__name__}: {e}'}
  section['permutations'].append(row);save()
  print(case,list(order),row['student'],row['teacher'],flush=True)
data['status']='COMPLETED';save()
