import json,copy,torch
from pathlib import Path
from challenge.planner.student_backend import StudentBackend
from order_adapter import canonical_request
ROOT=Path('/home/tiaozhansai/carla-driving-target-and-provement')
p=Path('results.json');data=json.loads(p.read_text())
b=StudentBackend(weights='/home/tiaozhansai/carla-driving-challenge/artifacts/challenge/distillation/a3_b1_closeout_robust_fp32_v3/student_v0_fp32_candidate.pt')
for sample in data['samples']:
 path='student_teacher_20261116/40m_student' if sample['name']=='40_standard' else 'baseline_repair_20261116/40_dense'
 d=ROOT/'artifacts/runtime'/path
 sub=next(x for l in open(next(d.glob('EXPERIMENT*.jsonl'))) if (x:=json.loads(l)).get('record_type')=='canonical_routing' and x.get('phase')=='SUBMIT')
 req=copy.deepcopy(sub['payload']['orchestration']['model_request'])
 req['targets']=copy.deepcopy(sample['candidates'])
 ids=[x['target_id'] for x in req['targets']];swap={ids[0]:ids[1],ids[1]:ids[0]}
 for target in req['targets']:target['target_id']=swap[target['target_id']]
 req['rgb_ref']=str(ROOT/req['rgb_ref']);fixed=canonical_request(req)
 with torch.inference_mode():p2=b.infer(fixed)
 selected=p2['steps'][0]['target']['target_id'];original=swap[selected]
 sample['id_swap_stress']={'remapping':swap,'selected_new_id':selected,'selected_original_candidate':original,'matches':sample['observations'][original]['joint_matches'],'original_selected_candidate':sample['rows'][0]['after']['target_id'],'canonical_order':[x['target_id'] for x in fixed['targets']]}
 print(sample['name'],sample['id_swap_stress'])
p.write_text(json.dumps(data,ensure_ascii=False,indent=2))
