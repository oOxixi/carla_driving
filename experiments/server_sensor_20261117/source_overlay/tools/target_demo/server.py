from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from runtime.scene_evidence import build_evidence, select_targets, verify_evidence

def obj(name,x,y,kind='vehicle',visual='普通车辆'):
    return {'track_id':name,'class':kind,'position_m':[x,y,0],'distance_m':round((x*x+y*y)**.5,1),'confidence':.94,'velocity_mps':[0,0,0],'sources':['RGB','LIDAR'],'visual':visual}
SCENARIOS={
 'side':{'title':'左右关系与动作方向','text':'从左边绕过右侧那辆车辆','intent':'AVOID_OBSTACLE','direction':'LEFT','note':'右侧车辆是语言目标；左侧是绕行动作方向。','objects':[obj('V01',12,-3.2),obj('V02',17,3.1),obj('P01',9,1.8,'pedestrian','行人')]},
 'nearest':{'title':'明确指定最近目标','text':'跟随最近的车辆','intent':'FOLLOW','direction':None,'note':'只有“最近”触发确定性距离选择；“较近”不会自动等同于最近。','objects':[obj('V01',11,-2),obj('V02',20,2),obj('V03',27,-3)]},
 'visual':{'title':'多车辆视觉消歧','text':'跟随右侧那辆公交车','intent':'FOLLOW','direction':None,'note':'公交车仅是画面中的示意标签。验证器能检查方向和 ID，不能独立证明车型。','objects':[obj('V01',12,-3),obj('V02',20,-3.6,'vehicle','公交车')]},
 'missing':{'title':'指定目标缺失','text':'跟随右侧车辆','intent':'FOLLOW','direction':None,'note':'目标不存在和不可见在此合并为“无法找到或看见”，不会强行绑定。','objects':[obj('V01',12,3),obj('P01',9,-2,'pedestrian','行人')]},
 'approx':{'title':'图像估计位置','text':'跟随右侧车辆','intent':'FOLLOW','direction':None,'approximate':True,'note':'当前兼容桥使用图像框估计横向位置，无法把它当成可靠的三维几何硬证据。','objects':[obj('V01',12,-3),obj('V02',18,3)]}}

def evaluate(key,target,latest,rgb):
    spec=SCENARIOS[key]
    scene={'frame_id':120,'captured_at_ns':1100000000,'objects':spec['objects'],'stale':False,'sync':{'within_tolerance':True},'modality_valid':{'rgb':rgb}}
    command={'source_text':spec['text'],'intent':spec['intent'],'parameters':{'direction':spec['direction']}}
    evidence=build_evidence(command,scene,'demo-0001',geometry_trusted=not spec.get('approximate',False))
    current={**scene,'frame_id':121,'captured_at_ns':1130000000,'objects':list(scene['objects'])}
    if latest=='lost': current['objects']=[o for o in current['objects'] if o['track_id']!=target]
    if latest=='stale': current['stale']=True
    action='AVOID_OBSTACLE' if spec['intent']=='AVOID_OBSTACLE' else 'FOLLOW'
    plan={'steps':[{'behavior':action,'target':{'target_id':target or None,'target_lane':'LEFT_ADJACENT' if action=='AVOID_OBSTACLE' else None}}]}
    status,reason=verify_evidence(evidence,plan,current,now_ns=1150000000,rgb_available=rgb,command=command)
    return {'scenario':spec,'evidence':evidence.to_dict(),'verdict':status,'reason':reason,'request_targets':[o['track_id'] for o in select_targets(scene,evidence,8)]}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path!='/': return self.send_error(404)
        body=(Path(__file__).parent/'index.html').read_bytes(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        if self.path!='/api/evaluate': return self.send_error(404)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size>4096:return self.send_error(413)
            p=json.loads(self.rfile.read(size)); result=evaluate(p.get('scenario','side'),p.get('target',''),p.get('latest','normal'),bool(p.get('rgb',True)))
            body=json.dumps(result,ensure_ascii=False).encode(); self.send_response(200); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        except (KeyError,ValueError,TypeError):self.send_error(400)
    def log_message(self,fmt,*args):pass
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',18765),Handler).serve_forever()
