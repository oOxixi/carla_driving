import json,sys,traceback
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from request_guard import adapt_or_block
from challenge.planner.student_backend import StudentBackend
ROOT=Path('/home/tiaozhansai/carla-driving-target-and-provement')
backend=StudentBackend(weights='/home/tiaozhansai/carla-driving-challenge/artifacts/challenge/distillation/a3_b1_closeout_robust_fp32_v3/student_v0_fp32_candidate.pt')
class Handler(BaseHTTPRequestHandler):
 def do_POST(self):
  if self.path!='/infer':return self.send_error(404)
  try:
   req=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
   adapted,status=adapt_or_block(req)
   if adapted is None:
    code=422;result={'error_code':'STUDENT_UNKNOWN_DISTANCE','detail':status,'model_invoked':False,'plan':None}
   else:
    ref=adapted.get('rgb_ref')
    if ref and not Path(ref).is_absolute():adapted['rgb_ref']=str(ROOT/ref)
    result=backend.infer(adapted);code=200
   payload=json.dumps(result,ensure_ascii=False).encode()
   self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
  except Exception as e:
   traceback.print_exc();self.send_error(500,str(e))
 def log_message(self,*args):pass
print('guarded candidate loaded; no production gate',flush=True)
ThreadingHTTPServer(('127.0.0.1',28782),Handler).serve_forever()
