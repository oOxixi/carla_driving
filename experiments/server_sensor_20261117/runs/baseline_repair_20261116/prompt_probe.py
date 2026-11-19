"""Offline prompt/ordering sensitivity: same recorded frames, no control authority."""
import json,base64,time
from pathlib import Path
from openai import OpenAI
base=Path('/home/tiaozhansai/carla-driving-target-and-provement');d=base/'artifacts/runtime/baseline_repair_20261116';client=OpenAI(base_url='http://127.0.0.1:18160/v1',api_key='local',timeout=30,max_retries=0)
prompts={'direct':'画面顶部 T1 和 T2 的颜色分别对应同色空心框。驾驶车辆要跟随最近的同车道正前方车辆，不跟相邻车道或远处车辆。请选择 T1、T2；无法分辨时选择 Z。只输出一个选项。','spatial':'T1 和 T2 是图像中的真实检测框，框位置只代表像素，不能假设距离或车道。指令：跟随最近的同车道正前方车辆，不跟相邻或远处车辆。分析车道线与目标位置：同车道车辆选择 T1 或 T2；无法确认选择 Z。只输出一个选项。'}
results=[]
for fn in ('crop_model_replay.json','crop_model_swap.json'):
 for row in json.load(open(d/fn)):
  if row['mode']!='crop':continue
  img=base/row['image_ref'];encoded=base64.b64encode(img.read_bytes()).decode('ascii')
  for kind,prompt in prompts.items():
   t=time.monotonic();response=client.chat.completions.create(model='Qwen/Qwen3.5-2B',messages=[{'role':'user','content':[{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+encoded}},{'type':'text','text':prompt}]}],temperature=0,max_tokens=3,extra_body={'structured_outputs':{'choice':['T1','T2','Z']},'chat_template_kwargs':{'enable_thinking':False}})
   r={'order':fn,'case':row['case'],'prompt':kind,'answer':response.choices[0].message.content,'elapsed_ms':round((time.monotonic()-t)*1000),'target_boxes':[x['bbox_original_px'] for x in row['detections']]};results.append(r);print(json.dumps(r,ensure_ascii=False),flush=True)
(d/'prompt_probe.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
