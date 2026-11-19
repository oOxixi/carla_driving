"""Compare constrained color output with prior letter outputs on identical frames.

This sends the same pre-existing JPEG bytes to the same Qwen vLLM endpoint.
Only output format/option wording and allowed output length are changed.
No decision is sent to any vehicle controller.
"""
from pathlib import Path
import base64, copy, hashlib, json, sys, time, urllib.request
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from qwen_service.service import VllmQwenPlannerBackend

source=ROOT/'artifacts/runtime/target_live/left_right/result.json'
original=json.loads(source.read_text(encoding='utf-8'))
log=ROOT/'artifacts/runtime/target_live/logs/P0_REAL_TARGET_DEMO_20261103_215505_560214.jsonl'
with log.open(encoding='utf-8') as f:
    template=next(v['payload']['orchestration']['model_request'] for line in f
                  if (v:=json.loads(line)).get('record_type')=='canonical_routing' and v.get('phase')=='SUBMIT')
backend=VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
results=[]
for previous in original['cases']:
    scene=next(s for s in original['scenes'] if s['scene']==previous['scene'])
    candidates=sorted([scene['left'],scene['right']],key=lambda x:x['label'])
    visual=[{'bbox_xyxy_norm':x['bbox'],'label':x['label'],'target_id':x['target_id']} for x in candidates]
    req=copy.deepcopy(template)
    req['source_text']=previous['instruction']
    req['target_grounding']={'candidate_ids':['C-0001','C-0002'],'reason':'TEST_SPATIAL_RELATION',
                             'resolved_id':None,'status':'AMBIGUOUS','visual_candidates':visual}
    req['targets']=[{'class':'vehicle','confidence':1.0,'distance_m':None,'relation':'unknown',
                     'relative_speed_mps':None,'target_id':v['target_id']} for v in visual]
    req['scene_capabilities']={'available_lanes':['CURRENT'],'current_lane':'unknown','intersection_ahead':False,
        'left_gap_safe':False,'left_lane_exists':False,'right_gap_safe':False,'right_lane_exists':False,
        'route_available':True,'stop_line_clear':True}
    req['scene_summary'].update({'frame_id':scene['frame'],'min_gap_m':None,'risk_level':'LOW','traffic_light':'UNKNOWN','ttc_s':None})
    req['command_hint']={'direction':None,'intent':'FOLLOW','target':None,'target_speed_mps':5.0}
    req['rgb_ref']=scene['image_ref']
    assert hashlib.sha256((ROOT/req['rgb_ref']).read_bytes()).hexdigest()==scene['image_sha256']
    action_codes=backend._choice_codes(req)
    assert action_codes==['F']
    prompt=backend._choice_prompt(req,choice_codes=action_codes)
    old_legend=' '.join(f'{code}={backend._CHOICES[code]}' for code in action_codes)
    green='\u7eff\u8272';orange='\u6a59\u8272';unsure='\u4e0d\u786e\u5b9a'
    new_legend=f'{green}=FOLLOW target=T1 id=C-0001 color=green\n{orange}=FOLLOW target=T2 id=C-0002 color=orange\n{unsure}=UNSURE, hold and ask for confirmation'
    assert old_legend in prompt
    prompt=prompt.replace(old_legend,new_legend,1)
    old_heading='Choose exactly one safe high-level driving action code.'
    heading=('Choose exactly one safe action AND target option by outputting its color: '
             f'{green} or {orange}; if uncertain output {unsure}. '
             'The labels are in the top black band; each label and its unfilled target box have the same color. '
             'Box colors are annotations and do not describe the vehicle color. '
             f'If the instruction or image does not uniquely identify the requested target, choose {unsure} rather than guess.')
    assert old_heading in prompt;prompt=prompt.replace(old_heading,heading,1)
    image_url='data:image/jpeg;base64,'+base64.b64encode((ROOT/req['rgb_ref']).read_bytes()).decode('ascii')
    body={'model':'Qwen/Qwen3.5-2B','messages':[{'role':'user','content':[
          {'type':'image_url','image_url':{'url':image_url}},{'type':'text','text':prompt}]}],
          'temperature':0.0,'max_tokens':8,'structured_outputs':{'choice':[green,orange,unsure]},
          'chat_template_kwargs':{'enable_thinking':False}}
    row={'case':previous['case'],'scene':scene['scene'],'side':previous['side'],
         'instruction':previous['instruction'],'expected_id':previous['expected_target_id'],
         'expected_label':previous['expected_label'],'expected_color':green if previous['expected_label']=='T1' else orange,
         'previous_label':previous.get('selected_label'),'previous_raw_choice':previous.get('raw_choice'),
         'previous_correct':previous.get('correct'),'image_sha256':scene['image_sha256']}
    started=time.perf_counter()
    try:
        request=urllib.request.Request('http://127.0.0.1:8000/v1/chat/completions',
            data=json.dumps(body,ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(request,timeout=30) as response: data=json.load(response)
        raw=data['choices'][0]['message']['content'].strip()
        if raw not in (green,orange,unsure): raise ValueError('unexpected raw output: '+repr(raw))
        row.update({'raw_color':raw,'selected_label': 'T1' if raw==green else 'T2' if raw==orange else None,
                    'correct':raw==row['expected_color'],'abstained':raw==unsure,
                    'model_response':data})
    except Exception as exc: row['error']=str(exc)
    row['elapsed_ms']=round((time.perf_counter()-started)*1000)
    results.append(row)
    print(json.dumps({k:v for k,v in row.items() if k!='model_response'},ensure_ascii=False),flush=True)
    output={'model':'Qwen/Qwen3.5-2B','temperature':0,'max_tokens_color':8,'max_tokens_letter':1,
            'run_time_utc':datetime.now(timezone.utc).isoformat(),'scenes':original['scenes'],'cases':results,
            'method':'same frame and prompt context; option codes/wording changed from A B Z to color names; token limit 8 for multi-token choices',
            'prompt_example':prompt}
    destination=ROOT/'artifacts/runtime/target_live/color_choice';destination.mkdir(parents=True,exist_ok=True)
    temp=destination/'result.tmp';temp.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(destination/'result.json')
