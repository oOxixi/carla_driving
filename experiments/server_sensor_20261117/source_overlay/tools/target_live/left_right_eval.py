"""Evaluate image-relative left/right selection on newly captured CARLA scenes.

Candidate boxes come from projected simulator actor geometry, not a detector;
no model output is sent to the vehicle controls.
"""
from pathlib import Path
import copy, hashlib, json, math, queue, sys, time
from datetime import datetime, timezone
import carla
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.collect_qwen_target_scenes import _project_bbox
from integration.qwen_image_stager import QwenImageStager
from qwen_service.client import QwenServiceClient

OUT = ROOT / 'artifacts/runtime/target_live/left_right'
OUT.mkdir(parents=True, exist_ok=True)
LOG = ROOT / 'artifacts/runtime/target_live/logs/P0_REAL_TARGET_DEMO_20261103_215505_560214.jsonl'
with LOG.open(encoding='utf-8') as stream:
    template = next(row['payload']['orchestration']['model_request'] for line in stream
                    if (row := json.loads(line)).get('record_type') == 'canonical_routing'
                    and row.get('phase') == 'SUBMIT')
client = carla.Client('127.0.0.1', 2100)
client.set_timeout(12)
world = client.get_world()
blueprints = world.get_blueprint_library()
spawn_points = world.get_map().get_spawn_points()
stager = QwenImageStager(ROOT, ref_prefix='artifacts/runtime/target_live/left_right/images')
model = QwenServiceClient('http://127.0.0.1:18006', timeout_s=30)
all_actors = []
rows = []
scenes = []

def cleanup(actors):
    for actor in reversed(actors):
        try:
            if actor.type_id.startswith('sensor.'): actor.stop()
            actor.destroy()
        except RuntimeError: pass

def publish():
    data = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'model': 'Qwen/Qwen3.5-2B', 'temperature': 0,
            'map': world.get_map().name, 'expected_scenes': 4, 'expected_cases': 8,
            'ground_truth_method': 'carla_actor_projection',
            'scenes': scenes, 'cases': rows}
    temporary = OUT / 'result.tmp'
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(OUT / 'result.json')

def offset(t, longitudinal, lateral):
    yaw = math.radians(t.rotation.yaw)
    return carla.Transform(carla.Location(x=t.location.x + math.cos(yaw)*longitudinal - math.sin(yaw)*lateral,
                                          y=t.location.y + math.sin(yaw)*longitudinal + math.cos(yaw)*lateral,
                                          z=t.location.z + .15), t.rotation)

for scene_index, (start, dist) in enumerate([(220,14),(70,17),(130,20),(190,23)], 1):
    actors = []
    try:
        scene = None
        for attempt in range(24):
            cleanup(actors); actors = []
            transform = spawn_points[(start + attempt) % len(spawn_points)]
            ego = world.try_spawn_actor(blueprints.find('vehicle.tesla.model3'), transform)
            if ego is None: continue
            actors.append(ego); ego.set_simulate_physics(False)
            spawned = []
            vehicle_types = ['vehicle.audi.tt', 'vehicle.lincoln.mkz_2020']
            for j, lateral in enumerate((-3.2, 3.2)):
                vehicle = world.try_spawn_actor(blueprints.find(vehicle_types[(scene_index+j)%2]), offset(transform, dist, lateral))
                if vehicle is None: break
                actors.append(vehicle); vehicle.set_simulate_physics(False); spawned.append(vehicle)
            if len(spawned) != 2: continue
            camera_bp = blueprints.find('sensor.camera.rgb')
            camera_bp.set_attribute('image_size_x','800');camera_bp.set_attribute('image_size_y','450')
            camera_bp.set_attribute('fov','75');camera_bp.set_attribute('sensor_tick','0.0')
            camera = world.spawn_actor(camera_bp, carla.Transform(carla.Location(x=1.5,z=1.7)), attach_to=ego)
            actors.append(camera)
            frames = queue.Queue(maxsize=8)
            def on_frame(frame):
                try: frames.put_nowait(frame)
                except queue.Full: pass
            camera.listen(on_frame)
            # A paired semantic camera checks that the vehicles actually render,
            # rather than accepting boxes hidden behind roads or buildings.
            semantic_bp = blueprints.find('sensor.camera.semantic_segmentation')
            semantic_bp.set_attribute('image_size_x','800');semantic_bp.set_attribute('image_size_y','450')
            semantic_bp.set_attribute('fov','75');semantic_bp.set_attribute('sensor_tick','0.0')
            semantic = world.spawn_actor(semantic_bp, carla.Transform(carla.Location(x=1.5,z=1.7)), attach_to=ego)
            actors.append(semantic)
            semantic_frames=queue.Queue(maxsize=8)
            def on_semantic(frame):
                try: semantic_frames.put_nowait(frame)
                except queue.Full: pass
            semantic.listen(on_semantic)
            for _ in range(6): image=frames.get(timeout=12)
            mask_frame=semantic_frames.get(timeout=12)
            for _ in range(60):
                if image.frame==mask_frame.frame: break
                if image.frame<mask_frame.frame: image=frames.get(timeout=12)
                else: mask_frame=semantic_frames.get(timeout=12)
            if image.frame!=mask_frame.frame: continue
            semantic_raw=np.frombuffer(mask_frame.raw_data,dtype=np.uint8).reshape((450,800,4))
            objects=[]
            for vehicle in spawned:
                box = _project_bbox(vehicle,camera,800,450,75)
                if box is None: break
                x1,y1,x2,y2=box
                patch=semantic_raw[int(y1*450):max(int(y2*450),int(y1*450)+1),
                                   int(x1*800):max(int(x2*800),int(x1*800)+1),2]
                visible_pixels=int(np.count_nonzero(patch==14))
                if visible_pixels < max(60, int(patch.size*.03)): break
                objects.append({'actor_id':vehicle.id, 'blueprint':vehicle.type_id,
                                'bbox':box, 'center_x':(box[0]+box[2])/2,
                                'visible_vehicle_pixels':visible_pixels})
            if len(objects)!=2: continue
            objects.sort(key=lambda x:x['center_x'])
            if not (.08 < objects[0]['center_x'] < objects[1]['center_x'] < .92): continue
            if objects[1]['bbox'][0] - objects[0]['bbox'][2] < .02: continue
            if min((o['bbox'][2]-o['bbox'][0]) for o in objects)<.035: continue
            # Alternate candidate IDs/colors: T1 is left on odd scenes, right on even scenes.
            ordered = objects if scene_index % 2 else list(reversed(objects))
            visuals=[]
            for idx,obj in enumerate(ordered):
                obj['label'] = f'T{idx+1}'; obj['target_id'] = f'C-000{idx+1}'
                visuals.append({'bbox_xyxy_norm':obj['bbox'],'label':obj['label'],'target_id':obj['target_id']})
            req=copy.deepcopy(template)
            req['target_grounding']={'candidate_ids':['C-0001','C-0002'], 'reason':'TEST_SPATIAL_RELATION',
                                     'resolved_id':None,'status':'AMBIGUOUS','visual_candidates':visuals}
            req['targets']=[{'class':'vehicle','confidence':1.0,'distance_m':None,
                             'relation':'unknown','relative_speed_mps':None,'target_id':v['target_id']} for v in visuals]
            req['scene_capabilities']={'available_lanes':['CURRENT'],'current_lane':'unknown',
                'intersection_ahead':False,'left_gap_safe':False,'left_lane_exists':False,
                'right_gap_safe':False,'right_lane_exists':False,'route_available':True,'stop_line_clear':True}
            req['scene_summary'].update({'frame_id':image.frame,'min_gap_m':None,'risk_level':'LOW','traffic_light':'UNKNOWN','ttc_s':None})
            req['command_hint']={'direction':None,'intent':'FOLLOW','target':None,'target_speed_mps':5.0}
            cmd=f'lr-scene-{scene_index}-{image.frame}'
            req['command_id']=cmd
            stager.stage(cmd,image,frame_id=image.frame)
            req=stager.prepare_request(req)
            imagepath=ROOT/req['rgb_ref']
            scene={'scene':scene_index,'frame':image.frame,'image_ref':req['rgb_ref'],
                   'image_sha256':hashlib.sha256(imagepath.read_bytes()).hexdigest(),
                   'left':objects[0],'right':objects[1],'distance_setting_m':dist,
                   'ego_actor_id':ego.id, 'camera_actor_id':camera.id, 'spawn_index':(start+attempt)%len(spawn_points)}
            scenes.append(scene)
            print('SCENE',json.dumps(scene),flush=True)
            break
        if scene is None: raise RuntimeError(f'could not construct scene {scene_index}')
        for side in ('left','right'):
            payload=copy.deepcopy(req)
            payload['source_text']=('\u8bf7\u8ddf\u968f\u753b\u9762\u5de6\u8fb9\u7684\u8f66\u8f86' if side=='left'
                                    else '\u8bf7\u8ddf\u968f\u753b\u9762\u53f3\u8fb9\u7684\u8f66\u8f86')
            payload['request_id']=f'left-right-{scene_index}-{side}-{image.frame}'
            payload['created_at_ns']=time.monotonic_ns();payload['deadline_ns']=payload['created_at_ns']+25_000_000_000
            case={'case':len(rows)+1,'scene':scene_index,'side':side,'instruction':payload['source_text'],
                  'expected_label':scene[side]['label'],'expected_target_id':scene[side]['target_id']}
            start_time=time.perf_counter()
            try:
                response=model.infer(payload);g=response.get('model_grounding') or {}
                selected=g.get('target_id'); case.update({'response':response,'raw_choice':g.get('raw_choice'),
                    'selected_id':selected,'selected_label':next((v['label'] for v in visuals if v['target_id']==selected),None),
                    'abstained':bool(g.get('abstained')),'correct':selected==case['expected_target_id'] and not g.get('abstained')})
            except Exception as exc:
                case.update({'error':str(exc),'correct':False})
            case['elapsed_ms']=round((time.perf_counter()-start_time)*1000)
            rows.append(case);publish()
            print('CASE',json.dumps({k:v for k,v in case.items() if k!='response'},ensure_ascii=False),flush=True)
    finally:
        cleanup(actors)
print('DONE',len(scenes),len(rows),sum(bool(x.get('correct')) for x in rows),flush=True)
