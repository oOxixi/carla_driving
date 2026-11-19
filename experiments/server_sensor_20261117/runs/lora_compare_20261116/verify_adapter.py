import json
from openai import OpenAI
c=OpenAI(base_url='http://127.0.0.1:28760/v1',api_key='local',timeout=30)
prompt='驾驶指令：前方路口右转，然后减速停车。请选择主要动作。'
out=[]
for model in ('Qwen/Qwen3.5-2B','semantic-v14'):
 try:
  r=c.chat.completions.create(model=model,messages=[{'role':'user','content':prompt}],temperature=0,max_tokens=1,logprobs=True,top_logprobs=5,extra_body={'chat_template_kwargs':{'enable_thinking':False}})
  lp=r.choices[0].logprobs.content[0];out.append({'model':model,'token':lp.token,'logprob':lp.logprob,'top':[(x.token,x.logprob) for x in lp.top_logprobs]})
 except Exception as e:out.append({'model':model,'error':str(e)})
print(json.dumps(out,ensure_ascii=False,indent=2))
