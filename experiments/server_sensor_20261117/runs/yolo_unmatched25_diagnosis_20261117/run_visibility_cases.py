import json,os,pathlib,subprocess,sys
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/yolo_unmatched25_diagnosis_20261117');data=json.loads((P/'diagnosis.json').read_text());cases=sorted({r['case'] for r in data['rows']});log=P/'visibility_run.log';py=sys.executable
for i,case in enumerate(cases):
 if (P/'visibility_cases'/f'{case}.json').exists():print('EXISTS',i+1,case,flush=True);continue
 for attempt in range(2):
  env=os.environ.copy();env['VIS_CASE']=case
  with log.open('a') as f:result=subprocess.run([py,str(P/'reconstruct_visibility.py')],env=env,stdout=f,stderr=subprocess.STDOUT)
  if (P/'visibility_cases'/f'{case}.json').exists():print('DONE',i+1,case,'attempt',attempt+1,'exit',result.returncode,flush=True);break
  print('RETRY',case,'exit',result.returncode,flush=True);subprocess.run([py,str(P/'reset_visibility_world.py')],check=False)
 else:print('FAILED',case,flush=True)
print('cases saved',len(list((P/'visibility_cases').glob('*.json'))),'/',len(cases),flush=True)
