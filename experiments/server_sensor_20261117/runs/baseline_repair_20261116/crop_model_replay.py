"""Real model replay with same RGB detections, no link to vehicle control."""
import copy,glob,json,time,sys
from pathlib import Path
from types import SimpleNamespace as NS
from PIL import Image
from integration.qwen_image_stager import QwenImageStager
from qwen_service.client import QwenServiceClient
root=Path('/home/tiaozhansai/carla-driving-target-and-provement');base=root/'artifacts/runtime/baseline_repair_20261116';client=QwenServiceClient('http://127.0.0.1:18161',timeout_s=30)
p=root/'artifacts/runtime/live_demo_20261116/40m';source=glob.glob(str(p/'EXPERIMENT*.jsonl'))[0]
req=next(x['payload']['orchestration']['model_request'] for l in open(source) if (x:=json.loads(l)).get('record_type')=='canonical_routing' and x.get('phase')=='SUBMIT')
results=[]
for case in ('40','60'):
 capture=root/f'artifacts/runtime/command_frame_diagnostics_20261112/{case}/capture';meta=json.load(open(capture/'metadata.json'));compare=json.load(open(capture/'center_crop_comparison.json'));detections=compare['detections'];source_image=Image.open(capture/'camera_rgb.png').convert('RGBA')
 for mode in ('full','crop'):
  current=copy.deepcopy(req);current['request_id']=f'baseline-crop-{case}-{mode}';current['command_id']=f'crop-{case}-{mode}';current['created_at_ns']=time.monotonic_ns();current['deadline_ns']=current['created_at_ns']+20_000_000_000;current['scene_summary']['frame_id']=meta['frame'];current['targets']=[];current['target_grounding']={'candidate_ids':[],'reason':'GEOMETRY_UNCERTAIN','resolved_id':None,'status':'AMBIGUOUS','visual_candidates':[]}
  crop=(0,0,source_image.width,source_image.height) if mode=='full' else tuple(compare['crop_xyxy_px']);img=source_image.crop(crop);w,h=img.size
  for i,d in enumerate(detections):
   target=f'P-{i+1:04d}';x1,y1,x2,y2=d['bbox_original_px'];box=[(x1-crop[0])/w,(y1-crop[1])/h,(x2-crop[0])/w,(y2-crop[1])/h]
   current['targets'].append({'class':'vehicle','confidence':d['confidence'],'distance_m':None,'relation':'unknown','relative_speed_mps':None,'target_id':target});current['target_grounding']['candidate_ids'].append(target);current['target_grounding']['visual_candidates'].append({'bbox_xyxy_norm':box,'label':f'T{i+1}','target_id':target})
  m=NS(width=w,height=h,raw_data=img.tobytes('raw','BGRA'));stager=QwenImageStager(root,ref_prefix='artifacts/runtime/baseline_repair_20261116/crop_images');current['rgb_ref']=stager.stage(current['command_id'],m,frame_id=meta['frame']);current=stager.prepare_request(current)
  try: result=client.infer(current)
  except Exception as e: result={'error':str(e)}
  results.append({'case':case,'mode':mode,'image_ref':current['rgb_ref'],'detections':detections,'result':result});print(case,mode,json.dumps(result,ensure_ascii=False)[:1500],flush=True)
(base/'crop_model_replay.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
