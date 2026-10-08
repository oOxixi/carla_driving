"""Launch packaged Student, real audio runner and CARLA camera in one session."""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2]
SOURCE = PACKAGE/'02_源码与部署/source'
MODELS = {'full_int8': '03_训练与模型/A2模型与量化/models/full_int8/student_int8.onnx', 'fp32': '03_训练与模型/A2模型与量化/models/student_v0_fp32_candidate.onnx', 'mixed_top3': '03_训练与模型/A2模型与量化/models/mixed_precision_top3/student_int8_mixed_top3.onnx'}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def stop(proc):
    if proc.poll() is not None: return
    if os.name == 'nt': subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try: os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError: pass
    try: proc.wait(timeout=10)
    except subprocess.TimeoutExpired: proc.kill(); proc.wait()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host', default='127.0.0.1'); p.add_argument('--port', type=int, default=2000)
    p.add_argument('--service-port', type=int, default=8100)
    p.add_argument('--variant', choices=MODELS, default='full_int8')
    inputs = p.add_mutually_exclusive_group()
    inputs.add_argument('--audio', type=Path); inputs.add_argument('--live-mic', action='store_true')
    p.add_argument('--live-mic-source', default='@DEFAULT_SOURCE@')
    p.add_argument('--frames', type=int, default=1200)
    p.add_argument('--realtime', action='store_true'); p.add_argument('--follow-spectator', action='store_true')
    p.add_argument('--log-dir', type=Path, default=PACKAGE/'07_演示材料/runs')
    p.add_argument('--startup-timeout-s', type=float, default=90)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    if a.frames <= 0: p.error('frames must be positive')
    audio = (a.audio or SOURCE/'voice_group/test_samples/mandarin/0003.mp3').resolve()
    if not a.live_mic and not audio.is_file(): p.error('Audio input does not exist: '+str(audio))
    if a.live_mic and not sys.platform.startswith('linux'): p.error('--live-mic requires Linux/PulseAudio')
    run = a.log_dir.resolve()/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    url = f'http://127.0.0.1:{a.service_port}'
    service = [sys.executable, str(PACKAGE/'02_源码与部署/scripts/launch_student.py'), '--mode', 'http', '--variant', a.variant, '--host', '127.0.0.1', '--port', str(a.service_port), '--image-root', str(SOURCE)]
    rgb_prefix = 'artifacts/runtime/demo_images/'+run.name
    runner = [sys.executable, '-m', 'integration.carla_runner', '--scenario', 'cruise', '--host', a.host, '--port', str(a.port), '--frames', str(a.frames), '--log-dir', str(run/'runner'), '--qwen-service-url', url, '--qwen-mode', 'planner_v2', '--qwen-image-root', str(SOURCE), '--qwen-image-prefix', rgb_prefix]
    runner += ['--live-mic', '--live-mic-source', a.live_mic_source] if a.live_mic else ['--audio', str(audio)]
    if a.realtime: runner.append('--realtime')
    if a.follow_spectator: runner.append('--follow-spectator')
    camera = [sys.executable, str(Path(__file__).with_name('record_carla_camera.py')), '--host', a.host, '--port', str(a.port), '--output-dir', str(run/'camera')]
    plan = {'service': service, 'runner': runner, 'camera': camera, 'source': str(SOURCE), 'run_dir': str(run), 'model': str(PACKAGE/MODELS[a.variant])}
    if a.dry_run: print(json.dumps(plan, ensure_ascii=False, indent=2)); return 0
    required_files = [SOURCE/'integration/carla_runner.py', SOURCE/'config/driving_policy.json', PACKAGE/'02_源码与部署/scripts/launch_student.py']
    absent = [str(f) for f in required_files if not f.is_file()]
    if absent: p.error('Incomplete overlay installation; merge payload into the full material package. Missing: '+', '.join(absent))
    missing = [name for name in ('carla', 'onnxruntime') if importlib.util.find_spec(name) is None]
    if not shutil.which('ffmpeg'): missing.append('ffmpeg')
    if a.live_mic and not shutil.which('parecord'): missing.append('parecord')
    if missing: p.error('Missing dependencies: '+', '.join(missing)+'; no demo/video generated. Voice dependencies must also be installed from source/voice_group/requirements.txt.')
    if not (PACKAGE/MODELS[a.variant]).is_file(): p.error('Packaged Student model missing')
    try:
        with urllib.request.urlopen(url+'/health', timeout=1): p.error('Service port is already occupied; choose another --service-port')
    except (OSError, TimeoutError): pass
    run.mkdir(parents=True); (run/'camera').mkdir()
    start = time.time(); handles = []; procs = []
    env = os.environ.copy(); env['PYTHONPATH'] = str(SOURCE)+os.pathsep+env.get('PYTHONPATH', ''); env['PYTHONIOENCODING'] = 'utf-8'
    manifest = {**plan, 'started_unix_s': start, 'model_sha256': sha(PACKAGE/MODELS[a.variant]), 'voice_input': 'live microphone' if a.live_mic else str(audio), 'audio_is_default_tts': not a.live_mic and not a.audio, 'python': sys.version}
    if not a.live_mic:
        shutil.copy2(audio, run/('input'+audio.suffix)); manifest['input_audio_sha256'] = sha(audio)
    for rel in ['voice_group/pipeline.py', 'voice_group/asr_vad.py', 'challenge/planner/student_adapter.py', 'integration/carla_runner.py']:
        f = SOURCE/rel
        if f.is_file(): manifest.setdefault('source_sha256', {})[rel] = sha(f)
    def launch(command, name):
        log = (run/(name+'.log')).open('wb'); handles.append(log)
        proc = subprocess.Popen(command, cwd=SOURCE, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=os.name != 'nt')
        procs.append(proc); return proc
    status = 'FAILED'
    try:
        sp = launch(service, 'student_service'); deadline = time.monotonic()+a.startup_timeout_s
        healthy = False
        while time.monotonic() < deadline:
            if sp.poll() is not None: raise RuntimeError('Student service exited; inspect student_service.log')
            try:
                with urllib.request.urlopen(url+'/health', timeout=1) as response:
                    health = json.load(response)
                (run/'service_health.json').write_text(json.dumps(health, indent=2), encoding='utf-8'); healthy = True; break
            except (OSError, ValueError, TimeoutError): time.sleep(.25)
        if not healthy: raise RuntimeError('Student health timeout')
        cp = launch(camera, 'camera'); deadline = time.monotonic()+a.startup_timeout_s
        while not (run/'camera/camera_connected.json').exists():
            if cp.poll() is not None or time.monotonic() > deadline: raise RuntimeError('Camera initialization failed; inspect camera.log')
            time.sleep(.1)
        mic = launch(['parecord', '--device='+a.live_mic_source, '--file-format=wav', '--rate=16000', '--channels=1', str(run/'live_microphone.wav')], 'microphone') if a.live_mic else None
        rp = launch(runner, 'runner'); manifest['runner_started_unix_s'] = time.time()
        while rp.poll() is None:
            if sp.poll() is not None or cp.poll() is not None or (mic and mic.poll() is not None): raise RuntimeError('A demo component exited early; inspect session logs')
            time.sleep(.2)
        manifest['runner_exit_code'] = rp.returncode
        if rp.returncode: raise RuntimeError('Runner failed; inspect runner.log')
        (run/'camera/STOP').touch()
        if cp.wait(timeout=45): raise RuntimeError('Camera failed to finalize; inspect camera.log')
        if not (run/'camera/camera.mp4').is_file(): raise RuntimeError('No recorded video')
        status = 'EXECUTED_REQUIRES_CONTENT_REVIEW'
    finally:
        (run/'camera/STOP').touch()
        for proc in reversed(procs): stop(proc)
        for h in handles: h.close()
        service_dir = PACKAGE/'runs'/a.variant
        if (SOURCE/rgb_prefix).is_dir(): shutil.copytree(SOURCE/rgb_prefix, run/'rgb', dirs_exist_ok=True)
        if service_dir.is_dir():
            for f in service_dir.rglob('*'):
                if f.is_file() and f.stat().st_mtime >= start:
                    dest = run/'service_artifacts'/f.relative_to(service_dir); dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, dest)
        manifest.update({'status': status, 'finished_unix_s': time.time(), 'video_has_audio': False, 'review_required': 'Verify runner evidence contains actual ASR transcript, Student request/plan and vehicle control in this session. Recording completion does not assert task success.'})
        (run/'run_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(str(run)); return 0

if __name__ == '__main__': raise SystemExit(main())
