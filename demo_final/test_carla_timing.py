#!/usr/bin/env python3
"""CARLA Integrated Demo: voice pipeline + LiDAR + Qwen-VL + D-Safety (multi-scene selectable)"""
import os, sys, time, threading, json, base64, math, random, datetime, socket
import numpy as np; import sounddevice as sd; from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(SCRIPT_DIR)  # 项目根目录 = 脚本所在目录的上一级
if not os.path.isdir(os.path.join(PROJECT, 'voice_group')):
    PROJECT = SCRIPT_DIR  # 兼容脚本直接放在项目根目录的情况
RESULTS = Path(SCRIPT_DIR) / 'results'; RESULTS.mkdir(parents=True, exist_ok=True)
IMG_DIR = RESULTS / 'snapshots'; IMG_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_KEEP = 5  # 只保留最近 N 条运行记录（run_*.json + 对应 summary）

def prune_old_results(results_dir, keep=RESULTS_KEEP):
    runs = sorted(results_dir.glob('run_*.json'), key=lambda p: p.name)
    for old in runs[:-keep] if len(runs) > keep else []:
        try: old.unlink()
        except Exception: pass
        s = results_dir / (old.stem + '_summary.txt')
        if s.exists():
            try: s.unlink()
            except Exception: pass
prune_old_results(RESULTS)

os.environ.setdefault('SENSEVOICE_MODEL_PATH', os.path.join(PROJECT, 'models', 'SenseVoiceSmall'))
os.environ.setdefault('FSMN_VAD_MODEL_PATH', os.path.join(PROJECT, 'models', 'FSMN_VAD', 'models', 'iic--speech_fsmn_vad_zh-cn-16k-common-pytorch', 'snapshots', 'master'))
os.environ.setdefault('VOICE_CASCADE_ENABLED', '0')
sys.path.insert(0, PROJECT); sys.path.insert(0, os.path.join(PROJECT, 'voice_group'))
from pipeline import audio_to_command
import carla
SAMPLE_RATE = 16000

# ---- scene selection ----
SCENE_DIR = Path(SCRIPT_DIR) / 'scenarios'
scene = None; scene_actors = []; sim_time_s = 0.0; scene_fixed_delta = 0.05

def list_scene_files():
    return sorted(SCENE_DIR.glob('*.json')) if SCENE_DIR.is_dir() else []

def load_scene(path):
    with open(path, 'r', encoding='utf-8') as f: return json.load(f)

def select_scene_file():
    files = list_scene_files()
    if not files:
        print('  [Scene] scenarios/ 下没有 JSON 场景文件'); return None
    if '--list-scenes' in sys.argv:
        print('  可用场景:')
        for i, f in enumerate(files):
            try:
                s = load_scene(f)
                print(f'    [{i+1}] {s.get("scenario_id", f.stem)}  ({s.get("map","?")}/{s.get("weather","?")})')
            except Exception as e:
                print(f'    [{i+1}] {f.name} (读取失败: {e})')
        sys.exit(0)
    arg = None
    for i, a in enumerate(sys.argv):
        if a == '--scene' and i + 1 < len(sys.argv): arg = sys.argv[i + 1]
    if arg is None: arg = os.environ.get('DEMO_SCENE', '')
    if arg:
        p = Path(arg)
        if p.is_file(): return p
        cand = SCENE_DIR / arg
        if cand.is_file(): return cand
        if arg.isdigit() and 1 <= int(arg) <= len(files): return files[int(arg) - 1]
        print(f'  [Scene] 未找到场景: {arg}，回退到菜单')
    print('\n  ============ 选择场景 ============')
    for i, f in enumerate(files):
        try:
            s = load_scene(f)
            print(f'    [{i+1}] {s.get("scenario_id", f.stem)}')
            print(f'        {s.get("map","?")}/{s.get("weather","?")} | {s.get("description","")[:80]}')
        except Exception as e:
            print(f'    [{i+1}] {f.name} (读取失败: {e})')
    print('  ==================================')
    while True:
        try: c = input(f'  选择场景 [1-{len(files)}, Enter=1, q=退出]: ').strip().lower()
        except (EOFError, KeyboardInterrupt): return None
        if c in ('q', 'quit'): return None
        if c == '': return files[0]
        if c.isdigit() and 1 <= int(c) <= len(files): return files[int(c) - 1]

QWEN_BASE = os.getenv('OPENAI_BASE_URL','https://api.siliconflow.cn/v1')
QWEN_KEY = os.getenv('OPENAI_API_KEY',''); QWEN_MODEL = os.getenv('QWEN_MODEL','Qwen/Qwen3-VL-32B-Instruct')
try:
    from openai import OpenAI; qwen_client = OpenAI(base_url=QWEN_BASE, api_key=QWEN_KEY, timeout=10)
    print(f'Qwen: {QWEN_MODEL} OK')
except Exception as e: qwen_client = None; print(f'Qwen error: {e}')

class SafetyCheck:
    LOW_TTC_S=1.5; CAUTION_TTC_S=2.5; MIN_FRONT_DIST_M=5.0
    def check(self,ttc_s=None,front_distance_m=None,collision=False):
        if collision: return 'EMERGENCY_STOP','COLLISION_DETECTED'
        if ttc_s is not None and ttc_s<=self.LOW_TTC_S: return 'EMERGENCY_STOP',f'LOW_TTC({ttc_s:.1f}s)'
        if front_distance_m is not None and front_distance_m<=self.MIN_FRONT_DIST_M: return 'EMERGENCY_STOP',f'FRONT_OBSTACLE({front_distance_m:.1f}m)'
        if ttc_s is not None and ttc_s<=self.CAUTION_TTC_S: return 'SLOW_DOWN',f'CAUTION_TTC({ttc_s:.1f}s)'
        return None,None
safety=SafetyCheck()

carla_world=None; carla_camera=None; camera_image=[None]; ego=None; lidar=None
collision_sensor=None; collision_flag=[False]; front_distance_m=[None]; lidar_alive=[False]
ego_speed_mps=0.0

def _cleanup_sensors():
    for _s in (carla_camera, collision_sensor, lidar):
        try:
            if _s is not None:
                _s.stop(); _s.destroy()
        except Exception: pass

def _apply_ego_speed():
    global ego_speed_mps
    if ego is None or ego_speed_mps<=0: return
    try:
        yaw=math.radians(ego.get_transform().rotation.yaw)
        ego.set_target_velocity(carla.Vector3D(ego_speed_mps*math.cos(yaw), ego_speed_mps*math.sin(yaw), 0))
    except Exception: pass

def local_to_world(ego_loc, ego_yaw, lx, ly):
    yaw=math.radians(ego_yaw); fx=math.cos(yaw); fy=math.sin(yaw)
    return ego_loc.x+fx*lx-fy*ly, ego_loc.y+fy*lx+fx*ly

def road_relative_pos(world, ego, rel_x_m, rel_y_m, yaw_deg=0):
    """沿自车所在车道向前 rel_x 米取道路点，再横向偏移 rel_y 米（适应弯道）。"""
    try:
        wpt=world.get_map().get_waypoint(ego.get_location(), project_to_road=True)
        if wpt is None: return None,None,None
        ahead=wpt.next(max(rel_x_m,1.0))
        if not ahead: return None,None,None
        base=ahead[0]
        ry=math.radians(base.transform.rotation.yaw)
        rx_vec=-math.sin(ry); ry_vec=math.cos(ry)  # 道路右向量
        x=base.transform.location.x+rx_vec*rel_y_m
        y=base.transform.location.y+ry_vec*rel_y_m
        return x,y,(base.transform.rotation.yaw+yaw_deg)
    except Exception:
        return None,None,None

def _actor_in_front_corridor(ego, actor, half_width=2.5):
    """判断 actor 是否位于自车前方 LiDAR 走廊内（弯道场景下直线走廊会漏检）。"""
    try:
        el=ego.get_location(); ey=ego.get_transform().rotation.yaw
        al=actor.get_location()
        yaw=math.radians(ey); fx=math.cos(yaw); fy=math.sin(yaw); rx=-fy; ry=fx
        dx=al.x-el.x; dy=al.y-el.y
        fwd=dx*fx+dy*fy; lat=dx*rx+dy*ry
        return 1.0<=fwd<=80.0 and abs(lat)<=half_width
    except Exception:
        return False

def spawn_scene_actors(world, sc, ego):
    ego_loc=ego.get_location(); ego_yaw=ego.get_transform().rotation.yaw
    for acfg in sc.get('actors', []):
        try:
            a_type=acfg.get('type',''); sp=acfg.get('spawn',{})
            if sp.get('use_relative'):
                x,y,yaw=road_relative_pos(world,ego,sp.get('rel_x_m',0),sp.get('rel_y_m',0),sp.get('yaw_deg',0))
                if x is None:
                    # 道路点不可用时退回直线偏移
                    x,y=local_to_world(ego_loc,ego_yaw,sp.get('rel_x_m',0),sp.get('rel_y_m',0))
                    yaw=ego_yaw+sp.get('yaw_deg',0)
            else:
                x,y=sp.get('x',ego_loc.x),sp.get('y',ego_loc.y)
                yaw=ego_yaw+sp.get('yaw_deg',0)
            bp=world.get_blueprint_library().find(a_type)
            actor=world.spawn_actor(bp,carla.Transform(carla.Location(x=x,y=y,z=sp.get('z',0.5)),carla.Rotation(yaw=yaw)))
            tgt=None; beh=acfg.get('behavior',{})
            if beh.get('mode')=='crossing' and beh.get('target_xy_m'):
                tgt=road_relative_pos(world,ego,beh['target_xy_m'][0],beh['target_xy_m'][1])
                if tgt[0] is None:
                    tgt=local_to_world(ego_loc,ego_yaw,beh['target_xy_m'][0],beh['target_xy_m'][1])
                else:
                    tgt=(tgt[0],tgt[1])
            scene_actors.append({'actor':actor,'cfg':acfg,'yaw':yaw,'spawn_xy':(x,y),'target_xy':tgt})
            print(f'  [Scene] {acfg.get("actor_id",a_type)} ({a_type}) @ ({x:.1f},{y:.1f}) mode={beh.get("mode","static")}')
        except Exception as ae:
            print(f'  [Scene] spawn {acfg.get("actor_id","?")} failed: {ae}')

def update_scene_actors():
    for ent in scene_actors:
        actor=ent['actor']; beh=ent['cfg'].get('behavior',{}); mode=beh.get('mode','static')
        try:
            if mode=='crossing' and ent['target_xy'] is not None:
                if sim_time_s < beh.get('start_time_s',0):
                    actor.apply_control(carla.WalkerControl()); continue
                loc=actor.get_location(); tx,ty=ent['target_xy']
                dx=tx-loc.x; dy=ty-loc.y; d=math.hypot(dx,dy)
                if d<0.8: actor.apply_control(carla.WalkerControl()); continue
                c=carla.WalkerControl(); c.speed=beh.get('speed_mps',1.2); c.direction=carla.Vector3D(dx/d,dy/d,0)
                actor.apply_control(c)
            elif mode=='forward':
                if sim_time_s < beh.get('start_time_s',0): continue
                loc=actor.get_location()
                moved=math.hypot(loc.x-ent['spawn_xy'][0],loc.y-ent['spawn_xy'][1])
                stop_m=beh.get('stop_after_m')
                if stop_m and moved>=stop_m:
                    actor.set_target_velocity(carla.Vector3D(0,0,0)); continue
                spd=beh.get('speed_mps',3.0); yaw=math.radians(ent['yaw'])
                actor.set_target_velocity(carla.Vector3D(spd*math.cos(yaw),spd*math.sin(yaw),0))
        except Exception:
            pass

try:
    scene_path=select_scene_file()
    if scene_path is None: sys.exit(0)
    scene=load_scene(scene_path)
    print(f'  [Scene] {scene.get("scenario_id","?")}: {scene.get("description","")}')
    print('  [Scene] 连接 CARLA (127.0.0.1:2000，最长等待30秒)...')
    conn_deadline=time.time()+30.0
    port_ok=False
    while time.time()<conn_deadline:
        try:
            _s=socket.create_connection(('127.0.0.1',2000),timeout=2.0); _s.close(); port_ok=True; break
        except OSError:
            time.sleep(2)
    if not port_ok:
        print('  [Scene] 错误: 30秒内未连接上 CARLA，请先启动 CARLA 再运行本脚本')
        sys.exit(1)
    client=carla.Client('127.0.0.1',2000); client.set_timeout(30.0)
    try:
        world=client.get_world()
    except Exception as ce:
        print(f'  [Scene] 错误: 连接 CARLA 失败: {ce}')
        sys.exit(1)
    cur_map=world.get_map().name.split('/')[-1]
    print('  [Scene] 等待 CARLA 世界就绪...')
    try:
        world.wait_for_tick(30.0)
        print(f'  [Scene] CARLA 世界就绪 (frame={world.get_snapshot().frame})')
    except Exception as we:
        print(f'  [Scene] 等待世界超时: {we}，继续执行同步预热')
    want_map=scene.get('map','Town03')
    if want_map and cur_map!=want_map:
        if os.environ.get('DEMO_FORCE_MAP','0')=='1':
            print(f'  [Scene] 强制加载地图 {want_map} (可能触发 shader 编译崩溃)...')
            try:
                world=client.load_world(want_map)
                try: world.wait_for_tick(30.0)
                except Exception: pass
            except Exception as le:
                print(f'  [Scene] 地图加载失败: {le}，继续使用当前地图 {cur_map}')
        else:
            print(f'  [Scene] 场景期望地图 {want_map}，当前 {cur_map}；默认使用当前地图'
                  '（本机加载新地图会触发 shader 编译崩溃），设 DEMO_FORCE_MAP=1 可强制')
    print(f'CARLA: {world.get_map().name}')
    try:
        world.set_weather(getattr(carla.WeatherParameters,scene.get('weather','ClearNoon'),carla.WeatherParameters.ClearNoon))
        print(f'  [Scene] weather={scene.get("weather","ClearNoon")}')
    except Exception as we: print(f'  [Scene] weather failed: {we}')
    settings=world.get_settings()
    scene_fixed_delta=scene.get('runtime',{}).get('fixed_delta_seconds',0.05)
    if not settings.synchronous_mode or abs(settings.fixed_delta_seconds-scene_fixed_delta)>1e-6:
        settings.synchronous_mode=True; settings.fixed_delta_seconds=scene_fixed_delta; world.apply_settings(settings)
    print('  [Scene] 同步预热 tick (40次, 先加载地图区块再生成自车)...')
    for _ in range(40):
        try: world.tick()
        except Exception as te:
            print(f'  [Scene] 预热 tick 失败，CARLA 可能无响应: {te}')
            break
    time.sleep(0.5)
    es=scene.get('ego_spawn',{})
    for _v in world.get_actors().filter('vehicle.*'):
        try: _v.destroy()
        except Exception: pass
    for _w in world.get_actors().filter('walker.*'):
        try: _w.destroy()
        except Exception: pass
    time.sleep(0.5)  # 等待销毁生效，避免生成时残留碰撞
    bp=world.get_blueprint_library().find('vehicle.tesla.model3')
    pts=world.get_map().get_spawn_points()
    n_actors=len(scene.get('actors',[]))
    ego=None
    base_idx=scene.get('seed',0)%len(pts) if pts else 0
    for off in range(30):
        idx=(base_idx+off)%len(pts)
        try:
            cand=world.spawn_actor(bp,pts[idx])
            world.tick()  # 同步模式下 spawn 的坐标在下一 tick 才生效
        except Exception:
            continue
        scene_actors.clear()
        spawn_scene_actors(world,scene,cand)
        if n_actors==0:
            # 空旷场景：验证前方有路可行驶
            try:
                wpt=world.get_map().get_waypoint(cand.get_location(), project_to_road=True)
                road_ok=bool(wpt and wpt.next(30.0))
            except Exception:
                road_ok=False
        else:
            road_ok=(len(scene_actors)>=n_actors)
            if road_ok:
                # 障碍车必须落在 LiDAR 前方走廊内（弯道上直线走廊会漏检）
                bad=[ent['cfg'].get('actor_id') for ent in scene_actors
                     if 'vehicle' in ent['actor'].type_id and not _actor_in_front_corridor(cand, ent['actor'])]
                if bad:
                    road_ok=False
        if not road_ok:
            for ent in scene_actors:
                try: ent['actor'].destroy()
                except Exception: pass
            scene_actors.clear()
            try: cand.destroy()
            except Exception: pass
            continue
        ego=cand
        print(f'  [Scene] 出生点 idx={idx} 可用')
        break
    if ego is None:
        print('  [Scene] 警告: 未找到场景演员全部可用的出生点，退而求其次')
        for off in range(len(pts)):
            try:
                ego=world.spawn_actor(bp,pts[(base_idx+off)%len(pts)])
                world.tick()  # 同步模式下 spawn 的坐标在下一 tick 才生效
                break
            except Exception:
                continue
        if ego is None:
            raise RuntimeError('无法在任何出生点生成自车')
        scene_actors.clear()
        spawn_scene_actors(world,scene,ego)
    ego_speed_mps=float(es.get('initial_speed_kph',0))/3.6
    print(f'  [Scene] ego 初始速度: {es.get("initial_speed_kph",0)} km/h ({ego_speed_mps:.2f} m/s)')
    try: ego.set_simulate_physics(True)
    except Exception: pass
    scfg=scene.get('sensors',{})
    rgb_cfg=scfg.get('front_rgb',{})
    for _s in world.get_actors().filter('sensor.camera.rgb'):
        try: _s.destroy()
        except Exception: pass
    cb=world.get_blueprint_library().find('sensor.camera.rgb')
    cb.set_attribute('image_size_x',str(rgb_cfg.get('width',800))); cb.set_attribute('image_size_y',str(rgb_cfg.get('height',600))); cb.set_attribute('fov',str(rgb_cfg.get('fov',90)))
    cb.set_attribute('sensor_tick','0.05')
    carla_camera=world.spawn_actor(cb,carla.Transform(carla.Location(x=1.5,z=2.0)),attach_to=ego)
    def _on_cam(img):
        arr=np.frombuffer(img.raw_data,dtype=np.uint8).reshape((img.height,img.width,4))[:,:,:3]; camera_image[0]=arr
    carla_camera.listen(_on_cam)
    if scfg.get('collision',{}).get('enabled',True):
        for _s in world.get_actors().filter('sensor.other.collision'):
            try: _s.destroy()
            except Exception: pass
        col_bp=world.get_blueprint_library().find('sensor.other.collision')
        collision_sensor=world.spawn_actor(col_bp,carla.Transform(),attach_to=ego)
        collision_sensor.listen(lambda e: collision_flag.__setitem__(0,True))
    lidar_cfg=scfg.get('lidar',{})
    if lidar_cfg.get('enabled',True):
        for _s in world.get_actors().filter('sensor.lidar.ray_cast'):
            try: _s.destroy()
            except Exception: pass
        lidar_bp=world.get_blueprint_library().find('sensor.lidar.ray_cast')
        lidar_bp.set_attribute('range',str(lidar_cfg.get('range',80))); lidar_bp.set_attribute('rotation_frequency',str(lidar_cfg.get('rotation_frequency',20))); lidar_bp.set_attribute('channels',str(lidar_cfg.get('channels',32))); lidar_bp.set_attribute('points_per_second',str(lidar_cfg.get('points_per_second',224000)))
        lidar_bp.set_attribute('sensor_tick','0.05')
        lidar=world.spawn_actor(lidar_bp,carla.Transform(carla.Location(x=0.0,z=2.35)),attach_to=ego)
        def _on_lidar(data):
            lidar_alive[0]=True
            pts=np.frombuffer(data.raw_data,dtype=np.float32).reshape((-1,4))
            # 仅保留车前方车道走廊内的回波；排除地面(z<-2.2)与高处杂物(z>1.0)
            front=pts[(pts[:,0]>=1.0)&(np.abs(pts[:,1])<=1.35)&(pts[:,2]>=-2.2)&(pts[:,2]<=1.0)]
            front_distance_m[0]=float(np.percentile(front[:,0],10)) if len(front)>=3 else None
        lidar.listen(_on_lidar)
    print('  [Scene] 传感器预热（等待首帧图像/LiDAR，最多40帧）...')
    got_cam=False; got_lidar=False
    for _ in range(40):
        try: world.tick()
        except Exception: break
        if camera_image[0] is not None: got_cam=True
        if lidar_alive[0]: got_lidar=True
        if got_cam and got_lidar: break
    print(f'  [Scene] 传感器预热结果: camera={"OK" if got_cam else "无帧"} lidar={"OK" if got_lidar else "无数据"}')
    if scfg.get('front_rgb',{}).get('enabled',True) and not got_cam:
        print('  [Scene] 错误: 摄像头无帧（streaming 链路异常），请重启 CARLA 后再运行本脚本')
        _cleanup_sensors()
        sys.exit(1)
    if lidar_cfg.get('enabled',True) and not got_lidar:
        print('  [Scene] 错误: LiDAR 无数据（streaming 链路异常），请重启 CARLA 后再运行本脚本')
        _cleanup_sensors()
        sys.exit(1)
    for _ in range(10):
        try: world.tick()
        except Exception: break
    _apply_ego_speed()
    time.sleep(0.5); carla_world=world
    print('Scene ready\n')
    for c_ in scene.get('commands',[])[:4]:
        prm=c_.get('parameters',{})
        extra=f' ({prm.get("target_speed_kph")}km/h)' if prm.get('target_speed_kph') else ''
        print(f'  建议指令: "{c_.get("source_text","")}" -> {c_.get("intent","?")}{extra}')
    for n_ in scene.get('notes',[])[:4]: print(f'    * {n_}')
    print('')
except Exception as e:
    print(f'CARLA error: {e}\n'); import traceback; traceback.print_exc()

def record_audio():
    input('\n>>> Press Enter to record...'); print('    * Recording... (Press Enter to stop)')
    frames=[]; stop=[False]
    def cb(i,_f,_t,_s):
        if stop[0]: raise sd.CallbackStop
        frames.append(i.copy())
    t=threading.Thread(target=lambda:(input(),stop.__setitem__(0,True)),daemon=True); t.start()
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE,channels=1,dtype='float32',callback=cb):
            t.join(timeout=10); stop[0]=True
    except sd.CallbackStop: pass
    if not frames: return None
    a=np.concatenate(frames).flatten().astype('float32')
    am=np.abs(a); mask=am>0.015
    if mask.any(): idx=np.where(mask)[0]; pad=int(0.08*SAMPLE_RATE); a=a[max(0,idx[0]-pad):min(len(a),idx[-1]+pad)]
    return a

def carla_tick():
    global sim_time_s
    if carla_world is None: return None,0,{}
    t0=time.monotonic_ns()
    n_ticks=int((scene or {}).get('runtime',{}).get('sim_ticks_per_round',1) or 1)
    try:
        for _ in range(n_ticks):
            carla_world.tick(); sim_time_s+=scene_fixed_delta; update_scene_actors()
        _apply_ego_speed()
    except Exception:
        pass
    ms=(time.monotonic_ns()-t0)/1e6
    img=camera_image[0]; snap_path=None
    if img is not None:
        import cv2
        p=IMG_DIR/f'snap_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.jpg'
        cv2.imwrite(str(p),img); snap_path=str(p)
    ttc=None; spd=0
    if ego:
        v=ego.get_velocity(); spd=math.sqrt(v.x**2+v.y**2)
        if front_distance_m[0] is not None and spd>0.1: ttc=front_distance_m[0]/spd
    perc={'front_distance_m':round(front_distance_m[0],1) if front_distance_m[0] else None,'ttc_s':round(ttc,1) if ttc else None,'ego_speed_mps':round(spd,1),'collision':collision_flag[0]}
    return snap_path,ms,perc

def qwen_decide(voice_text,image_path,perception):
    if qwen_client is None or image_path is None: return None,0,None
    with open(image_path,'rb') as f: b64=base64.b64encode(f.read()).decode()
    p=perception
    prompt=f'''SAFETY-FIRST driving assistant. RULES:
1. If front_distance_m < 5m or ttc_s < 2s, output EMERGENCY_STOP regardless of voice.
2. If a pedestrian or obstacle is visible, do NOT accelerate.
3. Visual safety ALWAYS overrides voice command.
4. Only follow voice if road is clearly safe.
5. front_distance=null means NO obstacle detected in the front corridor (open road), NOT "unknown/unsafe"; if the image is clear you may follow SPEED_UP/SET_SPEED.

Perception: front_dist={p.get('front_distance_m','?')}m ttc={p.get('ttc_s','?')}s collision={p.get('collision',False)} speed={p.get('ego_speed_mps','?')}m/s
Voice: {voice_text}

Output JSON only:
{{"action":"SET_SPEED|STOP|KEEP_LANE|CHANGE_LANE|SLOW_DOWN|SPEED_UP|EMERGENCY_STOP|PULL_OVER|AVOID_OBSTACLE","confidence":0.0-1.0,"reason_zh":"brief reason"}}
'''
    content=[{'type':'image_url','image_url':{'url':f'data:image/jpeg;base64,{b64}'}},{'type':'text','text':prompt}]
    t0=time.monotonic_ns()
    try:
        r=qwen_client.chat.completions.create(model=QWEN_MODEL,messages=[{'role':'user','content':content}],temperature=0.0,max_tokens=128)
        ms=(time.monotonic_ns()-t0)/1e6
        text=r.choices[0].message.content.strip()
        if text.startswith('```'): text=text.split('```')[1]
        if text.lower().startswith('json'): text=text[4:]
        return json.loads(text.strip()),ms,None
    except Exception as e: return None,(time.monotonic_ns()-t0)/1e6,str(e)

ICN={'SET_SPEED':'SPEED','SPEED_UP':'ACCEL','SLOW_DOWN':'SLOW','STOP':'STOP','EMERGENCY_STOP':'E-STOP','CHANGE_LANE':'LANE','KEEP_LANE':'KEEP','PULL_OVER':'PULL','AVOID_OBSTACLE':'AVOID','UNKNOWN':'???'}
print('='*65); print('  CARLA Integrated Demo: Voice + LiDAR + Qwen + D-Safety'); print('='*65)
session_id=datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); all_results=[]

try:
    while True:
        try: cl=input('\n[q quit / Enter record]: ').strip().lower()
        except (EOFError,KeyboardInterrupt): break
        if cl in ('q','quit'): break
        audio=record_audio()
        if audio is None or len(audio)<800: continue
        alen=len(audio)/SAMPLE_RATE; rt={}

        t0=time.monotonic_ns()
        voice=audio_to_command(audio, t_audio_start_ns=t0)
        rt['voice_total']=round((time.monotonic_ns()-t0)/1e6,1)
        lat=voice.get('_latency',{}); rt['voice_asr']=lat.get('asr_ms',0); rt['voice_nlu']=lat.get('nlu_ms',0)
        intent=voice.get('intent','UNKNOWN'); conf=voice.get('confidence',0); status=voice.get('status','?'); source=voice.get('source_text','')

        snap_path,tick_ms,perception=carla_tick()
        if snap_path: rt['carla_tick']=round(tick_ms,1)

        d_action,d_reason=safety.check(ttc_s=perception.get('ttc_s'),front_distance_m=perception.get('front_distance_m'),collision=perception.get('collision',False))

        SIMPLE_INTENTS={'STOP','EMERGENCY_STOP','SLOW_DOWN','SPEED_UP','SET_SPEED','KEEP_LANE'}
        if intent in SIMPLE_INTENTS:
            # 简单指令由语音直接输出（README 约定），不经过 Qwen；D 安全层仍可覆盖
            qr=None; qms=0; qerr=None
        else:
            qr,qms,qerr=qwen_decide(source,snap_path,perception)
        rt['qwen']=round(qms,1) if qms else 0

        final_action=d_action if d_action else (qr.get('action','UNKNOWN') if qr else intent)
        final_source='D-SAFETY' if d_action else ('QWEN-VL' if qr else 'VOICE')
        final_reason=d_reason if d_action else (qr.get('reason_zh','') if qr else '')
        final_conf=1.0 if d_action else (qr.get('confidence',0) if qr else conf)

        result={'idx':len(all_results)+1,'timestamp':datetime.datetime.now().isoformat(),'audio_len_s':round(alen,1),'asr_text':source,'voice_intent':intent,'voice_confidence':conf,'voice_latency':rt,'perception':perception,'d_safety_action':d_action,'d_safety_reason':d_reason,'qwen_action':qr.get('action') if qr else None,'qwen_confidence':qr.get('confidence') if qr else None,'final_action':final_action,'final_source':final_source,'final_reason':final_reason,'snap_path':snap_path}
        all_results.append(result)

        vt=sum(v for v in [rt.get('voice_total',0),rt.get('carla_tick',0),rt.get('qwen',0)] if v)
        print(f'\n  {"="*62}')
        print(f'  |  #{len(all_results)}  Voice: {ICN.get(intent,intent):6s}  conf:{conf:.0%}  "{source}"')
        print(f'  |  [Voice] ASR={rt.get("voice_asr",0):.0f}ms  NLU={rt.get("voice_nlu",0):.0f}ms  Total={rt.get("voice_total",0):.0f}ms')
        print(f'  |  [Perception] front={perception.get("front_distance_m","?")}m  ttc={perception.get("ttc_s","?")}s')
        print(f'  |  Timing: voice={rt.get("voice_total",0):.0f}ms  carla={rt.get("carla_tick",0):.0f}ms  qwen={rt.get("qwen",0):.0f}ms  total={vt:.0f}ms')
        if d_action: print(f'  |  [D-Safety] OVERRIDE: {d_action} ({d_reason})')
        if qr and qerr is None: print(f'  |  [Qwen-VL] {qr.get("action","?")}  conf:{qr.get("confidence",0):.0%}')
        elif qerr: print(f'  |  [Qwen-VL] error: {qerr}')
        print(f'  |  FINAL: {final_action} ({final_source}) conf:{final_conf:.0%}')
        print(f'  |  Reason: {final_reason}')
        if snap_path: print(f'  |  Snap: {Path(snap_path).name}')
        print(f'  {"="*62}')

except Exception as e:
    print(f'\nError: {e}'); import traceback; traceback.print_exc()
finally:
    if all_results:
        rf=RESULTS/f'run_{session_id}.json'
        with open(rf,'w',encoding='utf-8') as f: json.dump(all_results,f,ensure_ascii=False,indent=2,default=str)
        print(f'\nResults saved: {rf}')
        sf=RESULTS/f'run_{session_id}_summary.txt'
        with open(sf,'w',encoding='utf-8') as f:
            f.write(f'Session: {session_id}\nRounds: {len(all_results)}\n')
            for r in all_results:
                f.write('  #{} voice={} final={}({})\\\n'.format(r['idx'],r['voice_intent'],r['final_action'],r['final_source']))
        print(f'Summary saved: {sf}')
    else: print('\nNo results to save (0 rounds)')
    prune_old_results(RESULTS)

    for ent in scene_actors:
        try: ent['actor'].destroy()
        except Exception: pass
    scene_actors.clear()
    _cleanup_sensors()
if carla_world:
    s=carla_world.get_settings(); s.synchronous_mode=False; carla_world.apply_settings(s)
    print('CARLA released')
print('\nDone')
