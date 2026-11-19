import copy,json,time,traceback
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from challenge.planner.student_backend import StudentBackend
root=Path('/home/tiaozhansai/carla-driving-target-and-provement')
out=root/'artifacts/runtime/student_teacher_20261116'
weights=Path('/home/tiaozhansai/carla-driving-challenge/artifacts/challenge/distillation/a3_b1_closeout_robust_fp32_v3/student_v0_fp32_candidate.pt')
student=StudentBackend(weights=weights)
print('LOADED',student.health(),flush=True)
class Handler(BaseHTTPRequestHandler):
 def do_POST(self):
  if self.path!='/infer': self.send_error(404); return
  try:
   original=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
   req=copy.deepcopy(original)
   removed=req.pop('target_grounding',None)
   imputed=[]
   for target in req.get('targets',[]):
    if target.get('distance_m') is None:
     imputed.append(target['target_id']); target['distance_m']=0.0
   rgb=req.get('rgb_ref')
   if rgb and not Path(rgb).is_absolute(): req['rgb_ref']=str(root/rgb)
   started=time.perf_counter()
   result=student.infer(req)
   event={'input_original':original,'compatibility':{'removed_target_grounding':removed,'unknown_distance_imputed_zero_ids':imputed,'warning':'0 is a placeholder, not a measured distance; student result is diagnostic only'},'student_request':req,'student_plan':result,'latency_ms':(time.perf_counter()-started)*1000}
   with (out/'student_inferences.jsonl').open('a') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
   body=json.dumps(result,ensure_ascii=False).encode()
   self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  except Exception as e:
   traceback.print_exc()
   body=json.dumps({'error_code':'STUDENT_INFER_ERROR','message':str(e)}).encode()
   self.send_response(500);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args): pass
ThreadingHTTPServer(('127.0.0.1',28771),Handler).serve_forever()
