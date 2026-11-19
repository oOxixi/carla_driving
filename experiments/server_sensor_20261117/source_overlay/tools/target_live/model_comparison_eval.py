"""Compare new real VLMs to existing 2B outputs on the same eight CARLA cases."""
from pathlib import Path
import base64,hashlib,json,sys,time,urllib.request
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'artifacts/runtime/target_live'
source=json.loads((RUN/'color_no_labels/result.json').read_text(encoding='utf-8'))
name=sys.argv[1];port=int(sys.argv[2]); assert name in ('Qwen3.5-9B','Qwen3-VL-8B-Instruct')
green='\u7eff\u8272';orange='\u6a59\u8272';unsure='\u4e0d\u786e\u5b9a'
base_prompt=source['prompt_example'];last=source['cases'][-1]['instruction']
assert base_prompt.count(last)==1
rows=[]
for sample in source['cases']:
 scene=next(s for s in source['scenes'] if s['scene']==sample['scene'])
 path=ROOT/scene['no_label_ref'];img=path.read_bytes()
 assert hashlib.sha256(img).hexdigest()==scene['no_label_sha256']
 prompt=base_prompt.replace(last,sample['instruction'],1)
 body={'model':name,'messages':[{'role':'user','content':[
  {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(img).decode('ascii')}},
  {'type':'text','text':prompt}]}], 'temperature':0.0,'max_tokens':8,
  'structured_outputs':{'choice':[green,orange,unsure]},'chat_template_kwargs':{'enable_thinking':False}}
 row={'case':sample['case'],'scene':sample['scene'],'instruction':sample['instruction'],
      'expected_color':sample['expected_color'],'baseline_color':sample.get('raw_color'),
      'baseline_correct':sample.get('correct'),'image_sha256':scene['no_label_sha256']}
 start=time.perf_counter()
 try:
  request=urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',data=json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'},method='POST')
  with urllib.request.urlopen(request,timeout=90) as response:data=json.load(response)
  answer=data['choices'][0]['message']['content'].strip()
  if answer not in (green,orange,unsure):raise ValueError('unexpected response: '+repr(answer))
  row.update({'raw_color':answer,'correct':answer==row['expected_color'],'abstained':answer==unsure,'response':data})
 except Exception as error: row['error']=str(error)
 row['elapsed_ms']=round((time.perf_counter()-start)*1000); rows.append(row)
 print(json.dumps({k:v for k,v in row.items() if k!='response'},ensure_ascii=False),flush=True)
 out=RUN/'model_comparison';out.mkdir(parents=True,exist_ok=True)
 data={'model':name,'source':'color_no_labels','temperature':0,'max_tokens':8,'scenes':source['scenes'],
       'cases':rows,'at_utc':datetime.now(timezone.utc).isoformat(),
       'note':'same PNG bytes and same prompt as 2B experiment; model preprocessing may differ'}
 temp=out/(name+'.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(out/(name+'.json'))
print('COMPLETE',name,len(rows),sum(r.get('correct',False) for r in rows),flush=True)
