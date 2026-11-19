"""One command using V14's documented semantic prompt, offline only."""
import json,time
from pathlib import Path
from openai import OpenAI
prompt=Path('/home/tiaozhansai/carla-driving-qwen-semantic-adaptation/artifacts/semantic_sft/frozen_v14_public11_epoch6_20261109/dataset_system_prompt.txt').read_text(encoding='utf8')
text='跟随最近的同车道正前方车辆，不要跟相邻车道或远处车辆'
client=OpenAI(base_url='http://127.0.0.1:28760/v1',api_key='local',timeout=90,max_retries=0);out=[]
for m in ('Qwen/Qwen3.5-2B','semantic-v14'):
 t=time.monotonic()
 try:
  result=client.chat.completions.create(model=m,messages=[{'role':'system','content':prompt},{'role':'user','content':text}],temperature=0,max_tokens=512,extra_body={'chat_template_kwargs':{'enable_thinking':False}})
  raw=result.choices[0].message.content
  try:parsed=json.loads(raw);valid=True
  except (ValueError,TypeError):parsed=None;valid=False
  record={'model':m,'command':text,'raw':raw,'json_parse_ok':valid,'parsed':parsed,'finish_reason':result.choices[0].finish_reason,'elapsed_ms':round((time.monotonic()-t)*1000)}
 except Exception as e:record={'model':m,'error':f'{type(e).__name__}: {e}'}
 out.append(record);print(json.dumps(record,ensure_ascii=False),flush=True)
Path('artifacts/runtime/lora_compare_20261116/native_semantic_probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
