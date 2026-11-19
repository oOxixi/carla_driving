"""Offline model probes using only the sensor-generated candidate."""
import copy,json,time,traceback,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps
import torch
from challenge.planner.student_backend import StudentBackend
OUT=Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/lane_assoc_20261117')
d=json.loads((OUT/'result.json').read_text())
if d['status']!='PASS':raise RuntimeError('perception experiment must pass before model probe')
ids=d['evaluation']['candidates'];selected=[x for x in d['targets'] if x['id'] in ids]
if len(selected)!=1:raise RuntimeError('need exactly one sensor candidate')
x=selected[0]
image=Image.open(OUT/'camera.png').convert('RGB')
img=Image.new('RGB',(224,224),(0,0,0))
img.paste(ImageOps.pad(image,(224,208),method=Image.Resampling.BILINEAR,color=(0,0,0)),(0,16))
scale=min(224/image.width,208/image.height);ox=(224-image.width*scale)/2;oy=16+(208-image.height*scale)/2
x1,y1,x2,y2=x['bbox']
box=(round(ox+x1*image.width*scale),round(oy+y1*image.height*scale),round(ox+x2*image.width*scale),round(oy+y2*image.height*scale))
draw=ImageDraw.Draw(img);draw.text((3,3),'T1',fill=(0,255,80));draw.rectangle(box,outline=(0,255,80),width=1)
img.save(OUT/'model_input.jpg',format='JPEG',quality=75,subsampling=0)
now=time.monotonic_ns()
request={'schema_version':'1.0','request_id':'laneassoc-frame-'+str(d['frame']),'command_id':'laneassoc-follow',
 'created_at_ns':now,'deadline_ns':now+30_000_000_000,
 'source_text':'跟随最近的同车道正前方车辆，不要跟相邻车道或远处车辆',
 'rgb_ref':'artifacts/runtime/lane_assoc_20261117/model_input.jpg',
 'command_hint':{'intent':'FOLLOW','target_speed_mps':5.0,'direction':None,'target':None},
 'scene_summary':{'frame_id':d['frame'],'sim_time_s':d['sim_time_s'],'traffic_light':'UNKNOWN','risk_level':'UNKNOWN','min_gap_m':None,'ttc_s':None},
 'constraints':{'allowed_behaviors':['STOP','FOLLOW'],'speed_limit_mps':None,'max_target_speed_mps':5.0,'must_stop':False},
 'scene_capabilities':{'current_lane':str(d['ego_lane']),'available_lanes':['CURRENT','LEFT_ADJACENT','RIGHT_ADJACENT'],'left_lane_exists':True,'right_lane_exists':True,'left_gap_safe':False,'right_gap_safe':False,'route_available':False,'intersection_ahead':False,'stop_line_clear':False},
 'routing':{'disposition':'QWEN_PLAN','score':2,'reasons':['COMPLEX_MANEUVER'],'safe_wait_behavior':'STOP'},
 'targets':[{'target_id':x['id'],'class':'vehicle','confidence':x['confidence'],'distance_m':x['distance_m'],'relation':'center_ahead','relative_speed_mps':None}]}
output={'frame':d['frame'],'candidate_ids':ids,'note':'one sensor-generated candidate only; offline probe, no control; safety acceptance not checked','request_common':request}
try:
 student=StudentBackend(weights='/home/tiaozhansai/carla-driving-challenge/artifacts/challenge/distillation/a3_b1_closeout_robust_fp32_v3/student_v0_fp32_candidate.pt')
 req=copy.deepcopy(request);req['rgb_ref']=str(OUT/'model_input.jpg')
 tensors=student._preprocess(req)
 with torch.inference_mode():raw=student.model(*tensors.as_tuple())
 plan=student.infer(req);s=plan['steps'][0];target=(s.get('target') or {}).get('target_id')
 output['student']={'behavior':s['behavior'],'target_id':target,'confidence':plan['confidence'],'requires_confirmation':plan['requires_confirmation'],'raw_pointer_top':int(raw['target_pointer_logits'][0,0].argmax()),'raw_pointer_scores':[round(float(v),4) for v in raw['target_pointer_logits'][0,0]],'pass':s['behavior']=='FOLLOW' and target==ids[0],'production_ready':student.production_ready,'plan':plan}
except Exception as e:output['student']={'error':type(e).__name__+': '+str(e),'pass':False};traceback.print_exc()
try:
 req=copy.deepcopy(request);req['target_grounding']={'status':'RESOLVED','reason':'sensor_lane_candidate','candidate_ids':ids,'resolved_id':ids[0],'visual_candidates':[{'target_id':ids[0],'label':'T1','bbox_xyxy_norm':x['bbox']}]}
 body=json.dumps(req,ensure_ascii=False).encode()
 res=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18161/infer',body,{'Content-Type':'application/json'}),timeout=30))
 s=res['steps'][0];g=res.get('model_grounding') or {};target=g.get('target_id') or (s.get('target') or {}).get('target_id')
 output['teacher']={'behavior':s['behavior'],'target_id':target,'raw_choice':g.get('raw_choice'),'abstained':g.get('abstained'),'pass':s['behavior']=='FOLLOW' and target==ids[0],'plan':res}
except Exception as e:output['teacher']={'error':type(e).__name__+': '+str(e),'pass':False};traceback.print_exc()
(OUT/'model_result.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
print(json.dumps({k:output[k] for k in ('frame','candidate_ids','student','teacher')},ensure_ascii=False))
