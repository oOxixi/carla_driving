import copy,itertools,json,math,time,urllib.request
from pathlib import Path
import numpy as np,torch
from challenge.planner.student_backend import StudentBackend
from challenge.student.contract import BEHAVIORS
from order_adapter import canonical_request
ROOT=Path('/home/tiaozhansai/carla-driving-target-and-provement')
OUT=Path(__file__).resolve().parent
src=(ROOT/'artifacts/runtime/student_order_audit_20261116/audit.py').read_text()
exec(src[src.index('def associations('):src.index('def verdict(')])
student=StudentBackend(weights='/home/tiaozhansai/carla-driving-challenge/artifacts/challenge/distillation/a3_b1_closeout_robust_fp32_v3/student_v0_fp32_candidate.pt')
def infer(req):
 tensors=student._preprocess(req)
 with torch.inference_mode(): raw=student.model(*tensors.as_tuple())
 plan=student.infer(req);step=plan['steps'][0]
 return {'raw_top_index':int(raw['target_pointer_logits'][0,0].argmax()),'candidate_scores':[round(float(z),4) for z in raw['target_pointer_logits'][0,0][:len(req['targets'])]],'behavior':step['behavior'],'target_id':(step.get('target') or {}).get('target_id'),'confidence':round(plan['confidence'],4)}
def teacher(req):
 b=json.dumps(req,ensure_ascii=False).encode()
 return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:28781/infer',b,{'Content-Type':'application/json'}),timeout=30))
out={'status':'RUNNING','samples':[]}
def save():
 p=OUT/'results.json.tmp';p.write_text(json.dumps(out,ensure_ascii=False,indent=2));p.replace(OUT/'results.json')
for name,path in [('40_standard','student_teacher_20261116/40m_student'),('40_dense','baseline_repair_20261116/40_dense')]:
 d=ROOT/'artifacts/runtime'/path
 sub=next(x for l in open(next(d.glob('EXPERIMENT*.jsonl'))) if (x:=json.loads(l)).get('record_type')=='canonical_routing' and x.get('phase')=='SUBMIT')
 source=sub['payload']['orchestration']['model_request'];frame=source['scene_summary']['frame_id']
 obs=next(x for l in open(d/'evaluation/shadow_and_evaluation_truth.jsonl') if (x:=json.loads(l))['frame']==frame)
 fused={x['track_id']:x for x in obs['shadow'] if x.get('status')=='FUSED_UNVALIDATED' and x.get('distance_m') is not None}
 req=copy.deepcopy(source)
 for t in req['targets']:
  if t['target_id'] not in fused:raise RuntimeError('missing measured distance')
  t['distance_m']=float(fused[t['target_id']]['distance_m'])
 all_iou=associations(source,obs)
 ego=np.asarray([obs['ego_world_matrix'][i][3] for i in range(3)])
 center={}
 for a in obs['truth_for_evaluation_only']:
  if a['role_name'].endswith(':ego'):continue
  v=np.asarray(a['vertices_world']);center[a['role_name'].split(':')[-1]]=float(np.linalg.norm(v.mean(axis=0)-ego))
 observations={}
 for t in req['targets']:
  ident=t['target_id'];dist=t['distance_m'];ious=all_iou[ident]
  hits=[role for role,iou in ious.items() if iou>=0.3 and abs(center[role]-dist)<=5.0]
  observations[ident]={'measured_distance_m':round(dist,3),'source_status':'FUSED_UNVALIDATED','iou':ious,'truth_center_distance_m':{k:round(v,3) for k,v in center.items()},'joint_matches':hits}
 sample={'name':name,'frame':frame,'image_ref':source['rgb_ref'],'input_text':source['source_text'],'candidates':req['targets'],'observations':observations,'rows':[]}
 out['samples'].append(sample);save()
 for order in itertools.permutations([t['target_id'] for t in req['targets']]):
  q=copy.deepcopy(req);q['targets']=[next(t for t in req['targets'] if t['target_id']==i) for i in order]
  v=source['target_grounding']['visual_candidates'];q['target_grounding']['visual_candidates']=[next(x for x in v if x['target_id']==i) for i in order]
  q['target_grounding']['candidate_ids']=list(order);q['created_at_ns']=time.monotonic_ns();q['deadline_ns']=q['created_at_ns']+30_000_000_000
  plain=copy.deepcopy(q);plain.pop('target_grounding',None);plain['rgb_ref']=str(ROOT/plain['rgb_ref'])
  fixed=canonical_request(plain)
  before=infer(plain);after=infer(fixed)
  try:
   response=teacher(q);g=response.get('model_grounding') or {};t={'target_id':g.get('target_id'),'raw_choice':g.get('raw_choice'),'abstained':g.get('abstained')}
  except Exception as e:t={'error':str(e)}
  sample['rows'].append({'input_order':list(order),'canonical_order':[x['target_id'] for x in fixed['targets']],'before':before,'after':after,'teacher':t})
  save();print(name,order,before,after,t,flush=True)
out['status']='COMPLETED';save()
