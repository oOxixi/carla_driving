"""Offline replay to the real model, never connected to control."""
import copy,glob,json,time,urllib.request
from pathlib import Path
root=Path('artifacts/runtime/multisensor_follow_20261112')
for case in ('40','60','occlusion'):
 p=root/case;status=json.loads((p/'evaluation/observer_status.json').read_text());command=status['commands'][0];row=next(json.loads(l) for l in (p/'evaluation/shadow_and_evaluation_truth.jsonl').open() if json.loads(l)['frame']==command['frame']); shadow={o['track_id']:o for o in row['shadow']}
 routing=next(x for l in open(glob.glob(str(p/'*.jsonl'))[0]) if (x:=json.loads(l)).get('record_type')=='canonical_routing' and x['payload']['orchestration'].get('model_request'))
 original=routing['payload']['orchestration']['model_request'];results=[]
 for mode in ('baseline','shadow_sensor_information'):
  req=copy.deepcopy(original);now=time.monotonic_ns();req['request_id']='shadow-replay-'+case+'-'+mode;req['created_at_ns']=now;req['deadline_ns']=now+12_000_000_000
  if mode=='shadow_sensor_information':
   for target in req['targets']:
    s=shadow.get(target['target_id'])
    if s and s['status']=='FUSED_UNVALIDATED':
     target['distance_m']=s['distance_m']
     target['relation']='center_ahead' if s['lane_relation']=='SAME' else 'other_lane' if s['lane_relation']=='OTHER' else 'unknown'
     # Radar provides radial speed, not a confirmed per-object longitudinal velocity.
     target['relative_speed_mps']=None
  try:
   http=urllib.request.Request('http://127.0.0.1:18131/infer',data=json.dumps(req,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(http,timeout=15) as response:result=json.load(response)
  except Exception as error:result={'error':f'{type(error).__name__}: {error}'}
  results.append({'mode':mode,'targets':req['targets'],'response':result})
 (p/'evaluation/shadow_model_replay.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 for r in results:
  o=r['response']; plan=o.get('plan',o.get('decision_plan',o)); print(case,r['mode'],'targets',[(t['target_id'],t['distance_m'],t['relation']) for t in r['targets']],'response',json.dumps(plan,ensure_ascii=False)[:1500],flush=True)
