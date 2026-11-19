"""Re-run the screenshot's exact model request; zoom is offline, never control."""
import copy,glob,json,time,hashlib
from pathlib import Path
from PIL import Image,ImageOps
from qwen_service.client import QwenServiceClient
root=Path('/home/tiaozhansai/carla-driving-target-and-provement');out=root/'artifacts/runtime/baseline_repair_20261116/exact_zoom';images=root/'artifacts/runtime/live_demo_20261116/images';p=glob.glob(str(root/'artifacts/runtime/live_demo_20261116/40m/EXPERIMENT*.jsonl'))[0]
records=[json.loads(l) for l in open(p,encoding='utf8')];submit=next(x for x in records if x.get('record_type')=='canonical_routing' and x.get('phase')=='SUBMIT');req=submit['payload']['orchestration']['model_request']; original=root/req['rgb_ref'];im=Image.open(original).convert('RGB');assert im.size==(224,224)
header=16*((len(req['target_grounding']['visual_candidates'])+3)//4);scale=224/800;offset_y=header+(224-header-450*scale)/2; crop=(64,80,160,134)
for target in req['target_grounding']['visual_candidates']:
 x1,y1,x2,y2=target['bbox_xyxy_norm'];left,right=x1*224,x2*224;top,bottom=offset_y+y1*450*scale,offset_y+y2*450*scale
 assert crop[0]<=left<=right<=crop[2] and crop[1]<=top<=bottom<=crop[3],(target,crop,(left,top,right,bottom))
zoom=Image.new('RGB',(224,224),(0,0,0));zoom.paste(im.crop((0,0,224,header)),(0,0));region=im.crop(crop);res=Image.Resampling.LANCZOS;fitted=ImageOps.contain(region,(224,224-header),method=res);zoom.paste(fitted,((224-fitted.width)//2,header+(224-header-fitted.height)//2));zoompath=images/'frame_00008807_zoom224.jpg';zoom.save(zoompath,quality=95,subsampling=0)
client=QwenServiceClient('http://127.0.0.1:18161',timeout_s=30);results=[]
for i,mode in enumerate(['original','zoom','zoom','original','original','zoom'],1):
 request=copy.deepcopy(req);request['request_id']=f'exact-8807-{mode}-{i}';request['created_at_ns']=time.monotonic_ns();request['deadline_ns']=request['created_at_ns']+20_000_000_000
 request['rgb_ref']=req['rgb_ref'] if mode=='original' else str(zoompath.relative_to(root));start=time.perf_counter()
 try:
  plan=client.infer(request);r={'mode':mode,'choice':plan.get('model_grounding'),'model_id':plan.get('model_id'),'latency_ms':round((time.perf_counter()-start)*1000),'reason':plan.get('reason_code')}
 except Exception as e:r={'mode':mode,'error':str(e)}
 results.append(r);print(json.dumps(r,ensure_ascii=False),flush=True)
result={'source_frame':req['scene_summary']['frame_id'],'original_ref':req['rgb_ref'],'zoom_ref':str(zoompath.relative_to(root)),'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'zoom_sha256':hashlib.sha256(zoompath.read_bytes()).hexdigest(),'crop_xyxy_on_224':crop,'zoom_scale':round(224/(crop[2]-crop[0]),3),'details':'The exact 224px model input was cropped and enlarged; source pixels were not recovered. Same request and candidate order, no control execution.','results':results}
(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
