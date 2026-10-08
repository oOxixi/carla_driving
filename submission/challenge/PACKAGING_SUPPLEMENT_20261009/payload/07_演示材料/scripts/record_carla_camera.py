"""Record an attached CARLA RGB camera. Never ticks or changes world settings."""
import argparse
import json
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=2000)
    p.add_argument('--role-name', default='acceptance84:ego')
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--fps', type=int, default=20)
    p.add_argument('--width', type=int, default=1280)
    p.add_argument('--height', type=int, default=720)
    p.add_argument('--wait-ego-s', type=float, default=90)
    a = p.parse_args()
    if min(a.fps, a.width, a.height) <= 0: p.error('fps/width/height must be positive')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg: p.error('ffmpeg missing: install ffmpeg with libx264; no video generated')
    try: import carla
    except ImportError: p.error('CARLA Python API missing; no video generated')
    out = a.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    client = carla.Client(a.host, a.port); client.set_timeout(10)
    world = client.get_world()
    (out/'camera_connected.json').write_text(json.dumps({'map': world.get_map().name, 'role_name': a.role_name}), encoding='utf-8')
    sensor = encoder = None
    errors = None
    q = queue.Queue(maxsize=80)
    counts = {'captured': 0, 'encoded': 0, 'dropped': 0}
    writer_error = []
    partial = out/'camera.partial.mp4'
    try:
        deadline = time.monotonic()+a.wait_ego_s
        ego = None
        while time.monotonic() < deadline and not (out/'STOP').exists():
            ego = next((actor for actor in world.get_actors().filter('vehicle.*') if actor.attributes.get('role_name') == a.role_name), None)
            if ego: break
            time.sleep(.1)
        if not ego: raise RuntimeError('Ego was not found before timeout/stop; no video generated')
        bp = world.get_blueprint_library().find('sensor.camera.rgb')
        for k, v in {'image_size_x': str(a.width), 'image_size_y': str(a.height), 'fov': '90', 'sensor_tick': str(1/a.fps)}.items(): bp.set_attribute(k, v)
        sensor = world.spawn_actor(bp, carla.Transform(carla.Location(x=-6, z=3), carla.Rotation(pitch=-12)), attach_to=ego)
        errors = (out/'ffmpeg.log').open('wb')
        encoder = subprocess.Popen([ffmpeg, '-hide_banner', '-y', '-f', 'rawvideo', '-pixel_format', 'bgra', '-video_size', f'{a.width}x{a.height}', '-framerate', str(a.fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(partial)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors)
        def receive(frame):
            counts['captured'] += 1
            try: q.put_nowait((frame.frame, frame.timestamp, bytes(frame.raw_data), time.time_ns()))
            except queue.Full: counts['dropped'] += 1
        def write_frames():
            try:
                with (out/'camera_frames.jsonl').open('w', encoding='utf-8') as log:
                    while True:
                        item = q.get()
                        if item is None: break
                        frame, sim_time, raw, wall_ns = item
                        encoder.stdin.write(raw)
                        counts['encoded'] += 1
                        log.write(json.dumps({'video_index': counts['encoded']-1, 'carla_frame': frame, 'sim_time_s': sim_time, 'received_unix_ns': wall_ns})+'\n')
                        log.flush()
            except Exception as e: writer_error.append(str(e))
        worker = threading.Thread(target=write_frames, daemon=True); worker.start()
        sensor.listen(receive)
        (out/'camera_attached.json').write_text(json.dumps({'ego_id': ego.id, 'sensor_id': sensor.id, 'fps': a.fps}), encoding='utf-8')
        while not (out/'STOP').exists() and ego.is_alive and encoder.poll() is None and not writer_error: time.sleep(.1)
        sensor.stop()
        while worker.is_alive():
            try: q.put(None, timeout=.2); break
            except queue.Full: pass
        worker.join(timeout=15)
        if worker.is_alive(): raise RuntimeError('Frame writer did not finish')
        encoder.stdin.close()
        rc = encoder.wait(timeout=30)
        counts.update({'ffmpeg_exit_code': rc, 'writer_errors': writer_error, 'video_has_audio': False})
        valid = rc == 0 and not writer_error and counts['encoded'] > 0 and partial.is_file() and partial.stat().st_size > 0
        if valid: partial.replace(out/'camera.mp4')
        counts['video_created'] = valid
        (out/'camera_result.json').write_text(json.dumps(counts, indent=2), encoding='utf-8')
        if not valid: raise RuntimeError('Recording failed; inspect ffmpeg.log and camera_result.json')
        return 0
    finally:
        if sensor:
            try: sensor.stop(); sensor.destroy()
            except RuntimeError: pass
        if encoder and encoder.poll() is None: encoder.terminate(); encoder.wait(timeout=10)
        if errors: errors.close()

if __name__ == '__main__': raise SystemExit(main())
