import json,urllib.request,urllib.error,copy
from pathlib import Path
p=Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime')
events=[json.loads(x) for x in (p/'student_teacher_20261116/student_inferences.jsonl').open()]
audit=Path('results.json');data=json.loads(audit.read_text())
def call(req):
 try:
  r=urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:28782/infer',json.dumps(req).encode(),{'Content-Type':'application/json'}),timeout=30)
  return r.status,json.load(r)
 except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
for case,e in zip(('40m','60m','occlusion'),events):
 code,out=call(e['input_original']);data['cases'][case]['guard_service_response']={'http_status':code,'result':out}
 print(case,code,out)
req=copy.deepcopy(events[0]['input_original'])
for t in req['targets']:t['distance_m']=10.0
code,out=call(req)
data['known_distance_synthetic_check']={'http_status':code,'model_invoked':out.get('model_invoked'),'note':'synthetic 10 m, connectivity check only, not real perception'}
print('synthetic_known_distance',code,out.get('model_invoked'))
audit.write_text(json.dumps(data,ensure_ascii=False,indent=2))
