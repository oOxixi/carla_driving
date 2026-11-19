"""Repeat the color-output test with T1/T2 removed from the actual image."""
from pathlib import Path
import base64, hashlib, json, time, urllib.request
from datetime import datetime,timezone
from PIL import Image, ImageDraw
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'artifacts/runtime/target_live'
prior=json.loads((RUN/'color_choice/result.json').read_text(encoding='utf-8'))
OUT=RUN/'color_no_labels';(OUT/'images').mkdir(parents=True,exist_ok=True)
scenes=[]
for scene in prior['scenes']:
    old_path=ROOT/scene['image_ref']
    assert hashlib.sha256(old_path.read_bytes()).hexdigest()==scene['image_sha256']
    original=Image.open(old_path).convert('RGB')
    assert original.size==(224,224)
    new=original.copy();ImageDraw.Draw(new).rectangle((0,0,111,15),fill=(0,0,0))
    new_path=OUT/'images'/f"scene-{scene['scene']}.png";new.save(new_path,format='PNG')
    a=np.array(original);b=np.array(Image.open(new_path).convert('RGB'))
    assert np.array_equal(a[16:,:,:],b[16:,:,:])
    assert np.array_equal(a[:16,112:,:],b[:16,112:,:])
    assert not np.array_equal(a,b)
    scenes.append({**scene,'no_label_ref':str(new_path.relative_to(ROOT)),
                   'no_label_sha256':hashlib.sha256(new_path.read_bytes()).hexdigest()})
old_sentence='The labels are in the top black band; each label and its unfilled target box have the same color.'
new_sentence='The unfilled target boxes are green and orange.'
base_prompt=prior['prompt_example']
assert base_prompt.count(old_sentence)==1
last_instruction=prior['cases'][-1]['instruction']
assert base_prompt.count(last_instruction)==1
results=[]
for previous in prior['cases']:
    scene=next(s for s in scenes if s['scene']==previous['scene'])
    prompt=base_prompt.replace(last_instruction,previous['instruction'],1).replace(old_sentence,new_sentence,1)
    green='\u7eff\u8272';orange='\u6a59\u8272';unsure='\u4e0d\u786e\u5b9a'
    image_url='data:image/png;base64,'+base64.b64encode((ROOT/scene['no_label_ref']).read_bytes()).decode('ascii')
    body={'model':prior['model'],'messages':[{'role':'user','content':[
          {'type':'image_url','image_url':{'url':image_url}},{'type':'text','text':prompt}]}],
          'temperature':0.0,'max_tokens':8,'structured_outputs':{'choice':[green,orange,unsure]},
          'chat_template_kwargs':{'enable_thinking':False}}
    row={'case':previous['case'],'scene':scene['scene'],'instruction':previous['instruction'],
         'expected_label':previous['expected_label'],'expected_color':previous['expected_color'],
         'previous_color':previous.get('raw_color'),'previous_correct':previous.get('correct'),
         'original_image_sha256':scene['image_sha256'],'image_sha256':scene['no_label_sha256']}
    start=time.perf_counter()
    try:
        request=urllib.request.Request('http://127.0.0.1:8000/v1/chat/completions',
           data=json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(request,timeout=30) as response:data=json.load(response)
        raw=data['choices'][0]['message']['content'].strip()
        if raw not in (green,orange,unsure):raise ValueError('unexpected raw response: '+repr(raw))
        row.update({'raw_color':raw,'selected_label':'T1' if raw==green else 'T2' if raw==orange else None,
                    'correct':raw==row['expected_color'],'abstained':raw==unsure,'model_response':data})
    except Exception as error:row['error']=str(error)
    row['elapsed_ms']=round((time.perf_counter()-start)*1000)
    results.append(row)
    print(json.dumps({k:v for k,v in row.items() if k!='model_response'},ensure_ascii=False),flush=True)
    output={'model':prior['model'],'temperature':0,'max_tokens':8,'run_time_utc':datetime.now(timezone.utc).isoformat(),
            'scenes':scenes,'cases':results,'prompt_example':prompt,
            'method':'Original image decoded and top-left 112x16 pixels blacked out, saved losslessly as PNG; every other pixel identical. Prompt sentence describing visible labels changed; remaining candidate T1/T2 IDs remain in text.',
            'pixel_check':'outside first 112x16 pixels exactly identical in decoded RGB'}
    tmp=OUT/'result.tmp';tmp.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(OUT/'result.json')
