from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,os,threading,urllib.request
from urllib.parse import urlsplit, parse_qs

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'artifacts/runtime/target_live'
LOCK=threading.Lock()
CACHE={'path':None,'offset':0,'submit':None,'resolve':None,'frame':None}

def snapshot(requested_name=None):
    with LOCK:
        logs=sorted((RUN/'logs').glob('P0_REAL_TARGET_DEMO_*.jsonl'),key=lambda p:p.stat().st_mtime)
        if logs:
            path=next((p for p in logs if p.name==requested_name),logs[-1])
            if str(path)!=CACHE['path']:
                CACHE.update(path=str(path),offset=0,submit=None,resolve=None,frame=None)
            with path.open(encoding='utf-8') as f:
                f.seek(CACHE['offset'])
                while True:
                    pos=f.tell();line=f.readline()
                    if not line or not line.endswith('\n'):
                        f.seek(pos);break
                    try: item=json.loads(line)
                    except json.JSONDecodeError:continue
                    if item.get('record_type')=='canonical_routing':
                        if item.get('phase')=='SUBMIT':CACHE['submit']=item['payload']
                        if item.get('phase')=='RESOLVE':CACHE['resolve']=item['payload']
                    elif item.get('record_type')=='frame':CACHE['frame']=item
                CACHE['offset']=f.tell()
        submit=CACHE['submit'] or {};resolve=CACHE['resolve'] or {};frame=CACHE['frame'] or {}
        request=(submit.get('orchestration') or {}).get('model_request') or {}
        perception=submit.get('perception_state') or {}
        geometry={v['track_id']:v for v in perception.get('objects',[])}
        enriched=[]
        for item in request.get('targets',[]):
            detail=geometry.get(item.get('target_id'),{})
            enriched.append({**item,'position_m':detail.get('position_m'),
                'geometry_source':detail.get('geometry_source','UNKNOWN'),
                'lane_relation':detail.get('lane_relation','UNKNOWN')})
        orchestration=resolve.get('orchestration') or {}
        plan=orchestration.get('decision_plan') or {}
        grounding=plan.get('model_grounding') or {}
        candidates=request.get('target_grounding') or {}
        selected=grounding.get('target_id')
        target_labels={x['target_id']:x['label'] for x in candidates.get('visual_candidates',[])}
        try:
            pid=int((RUN/'runner.pid').read_text()); os.kill(pid,0); active=bool(logs and CACHE['path']==str(logs[-1]))
        except (OSError,ValueError,FileNotFoundError):active=False
        control=frame.get('final_control') or {}
        audit=None
        if CACHE['path']:
            summary=Path(CACHE['path']).with_suffix('.summary.json')
            if summary.is_file():
                try:
                    data=json.loads(summary.read_text(encoding='utf-8'))
                    extension=data.get('acceptance',{}).get('metrics',{}).get('extension_acceptance',{})
                    check=next((v for v in extension.get('checks',[]) if v.get('key')=='target_binding_correct'),None)
                    target=next((v for v in extension.get('checks',[]) if v.get('key')=='expected_target_actor_id'),None)
                    if check is not None:
                        audit={'correct':check.get('actual'),'association':target.get('actual') if target else None,
                               'expected':target.get('required') if target else None}
                except (ValueError,OSError,AttributeError):pass
        return {'audit':audit,'active':active,'source_text':request.get('source_text'),'model_id':plan.get('model_id'),
          'frame_id':request.get('scene_summary',{}).get('frame_id'),'request_id':request.get('request_id'),
          'target_grounding':candidates,'targets':enriched,'model_grounding':grounding,
          'selected_label':target_labels.get(selected),'steps':plan.get('steps',[]),
          'decision_reason':orchestration.get('reason_code'),'disposition':orchestration.get('disposition'),
          'feedback':orchestration.get('feedback'),'timing':orchestration.get('model_timing'),
          'speed_mps':frame.get('speed_mps'),'control':control,'live_frame':frame.get('frame'),
          'image_ref':request.get('rgb_ref'),'log_path':CACHE['path'],
          'replay_count':len(list((RUN/'replay').glob('*.jpg'))) if CACHE['path'] and '203554_180707' in CACHE['path'] else 0,
          'run_name':Path(CACHE['path']).name if CACHE['path'] else None,
          'run_names':[p.name for p in logs]}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send_bytes(self,body,ctype):
        self.send_response(200);self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        parts=urlsplit(self.path);path=parts.path;run=parse_qs(parts.query).get('run',[None])[0]
        if path=='/':return self.send_bytes((Path(__file__).parent/'index.html').read_bytes(),'text/html; charset=utf-8')
        if path=='/api/status':return self.send_bytes(json.dumps(snapshot(run),ensure_ascii=False).encode(),'application/json; charset=utf-8')
        if path=='/api/model-comparison':
            base=RUN/'color_no_labels'/'result.json'
            if not base.is_file():return self.send_error(404)
            result={'baseline':json.loads(base.read_text(encoding='utf-8')),'models':{}}
            for name in ('Qwen3.5-9B','Qwen3-VL-8B-Instruct','Qwen3-VL-8B-Q4-5880','Qwen3.8-27B-Q4-5880'):
                file=RUN/'model_comparison'/(name+'.json')
                if file.is_file():result['models'][name]=json.loads(file.read_text(encoding='utf-8'))
            return self.send_bytes(json.dumps(result,ensure_ascii=False).encode(),'application/json; charset=utf-8')
        if path=='/api/color-no-labels':
            result=RUN/'color_no_labels'/'result.json'
            if not result.is_file():return self.send_error(404)
            return self.send_bytes(result.read_bytes(),'application/json; charset=utf-8')
        if path.startswith('/color-no-labels/scene-') and path.endswith('.png'):
            name=path.removeprefix('/color-no-labels/scene-').removesuffix('.png')
            if not name.isdigit():return self.send_error(404)
            image=RUN/'color_no_labels'/'images'/('scene-'+name+'.png')
            if not image.is_file():return self.send_error(404)
            return self.send_bytes(image.read_bytes(),'image/png')
        if path=='/api/color-choice':
            result=RUN/'color_choice'/'result.json'
            if not result.is_file():return self.send_error(404)
            return self.send_bytes(result.read_bytes(),'application/json; charset=utf-8')
        if path.startswith('/color-choice/scene-') and path.endswith('.jpg'):
            name=path.removeprefix('/color-choice/scene-').removesuffix('.jpg')
            if not name.isdigit():return self.send_error(404)
            result=RUN/'color_choice'/'result.json'
            if not result.is_file():return self.send_error(404)
            data=json.loads(result.read_text(encoding='utf-8'))
            scene=next((item for item in data.get('scenes',[]) if item.get('scene')==int(name)),None)
            if not scene:return self.send_error(404)
            image=(ROOT/scene['image_ref']).resolve();base=(RUN/'left_right'/'images').resolve()
            if base not in image.parents or not image.is_file():return self.send_error(404)
            return self.send_bytes(image.read_bytes(),'image/jpeg')
        if path=='/api/left-right':
            result=RUN/'left_right'/'result.json'
            if not result.is_file():return self.send_error(404)
            return self.send_bytes(result.read_bytes(),'application/json; charset=utf-8')
        if path.startswith('/left-right/scene-') and path.endswith('.jpg'):
            name=path.removeprefix('/left-right/scene-').removesuffix('.jpg')
            if not name.isdigit():return self.send_error(404)
            result=RUN/'left_right'/'result.json'
            if not result.is_file():return self.send_error(404)
            data=json.loads(result.read_text(encoding='utf-8'))
            scene=next((item for item in data.get('scenes',[]) if item.get('scene')==int(name)),None)
            if not scene:return self.send_error(404)
            img=(ROOT/scene['image_ref']).resolve();base=(RUN/'left_right'/'images').resolve()
            if base not in img.parents or not img.is_file():return self.send_error(404)
            return self.send_bytes(img.read_bytes(),'image/jpeg')
        if path=='/api/label-ab':
            result=RUN/'label_ab'/'result.json'
            if not result.is_file():return self.send_error(404)
            return self.send_bytes(result.read_bytes(),'application/json; charset=utf-8')
        if path in ('/label-ab/a.jpg','/label-ab/b.jpg'):
            image=RUN/'label_ab'/path.rsplit('/',1)[-1]
            if not image.is_file():return self.send_error(404)
            return self.send_bytes(image.read_bytes(),'image/jpeg')
        if path=='/model-image':
            ref=snapshot(run).get('image_ref')
            if not ref:return self.send_error(404)
            img=(ROOT/ref).resolve();base=(RUN/'images').resolve()
            if base not in img.parents or not img.is_file():return self.send_error(404)
            return self.send_bytes(img.read_bytes(),'image/jpeg')
        if path.startswith('/replay/'):
            name=path.removeprefix('/replay/')
            if not (name.endswith('.jpg') and len(name)==8 and name[:4].isdigit()):return self.send_error(404)
            image=RUN/'replay'/name
            if not image.is_file():return self.send_error(404)
            return self.send_bytes(image.read_bytes(),'image/jpeg')
        if path=='/live.mjpg':
            try:
                source=urllib.request.urlopen('http://127.0.0.1:18081/stream.mjpg',timeout=8)
                self.send_response(200);self.send_header('Cache-Control','no-store');self.send_header('Content-Type',source.headers['Content-Type']);self.end_headers()
                while True:
                    chunk=source.read(8192)
                    if not chunk:break
                    self.wfile.write(chunk);self.wfile.flush()
            except (OSError,ConnectionError):pass
            return
        self.send_error(404)
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',18765),Handler).serve_forever()
