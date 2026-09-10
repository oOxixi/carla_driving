#!/usr/bin/env python3
"""Read-only CARLA chase camera with live command subtitles."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import signal
import threading
import time
from typing import Any

import carla
from PIL import Image, ImageDraw


class FrameStore:
    def __init__(self) -> None:
        self.condition = threading.Condition()
        self.jpeg: bytes | None = None
        self.sequence = 0

    def publish(self, jpeg: bytes) -> None:
        with self.condition:
            self.jpeg = jpeg
            self.sequence += 1
            self.condition.notify_all()

    def wait_after(self, sequence: int, timeout: float = 2.0) -> tuple[int, bytes | None]:
        with self.condition:
            if self.sequence <= sequence:
                self.condition.wait(timeout)
            return self.sequence, self.jpeg


class CommandStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._payload: dict[str, Any] = {
            "sequence": 0,
            "command_id": None,
            "source_text": "等待第一条驾驶指令…",
            "disposition": None,
            "log_file": None,
        }

    def publish(self, record: dict[str, Any], log_file: Path) -> None:
        source_text = record.get("source_text")
        command_id = record.get("command_id")
        if not isinstance(source_text, str) or not source_text.strip():
            return
        if not isinstance(command_id, str) or not command_id.strip():
            return
        with self._lock:
            if command_id == self._payload["command_id"]:
                return
            self._payload = {
                "sequence": int(self._payload["sequence"]) + 1,
                "command_id": command_id,
                "source_text": source_text.strip(),
                "disposition": record.get("disposition"),
                "log_file": str(log_file),
            }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._payload)


FRAMES = FrameStore()
COMMANDS = CommandStore()
STOP = threading.Event()


def ego_vehicle(world: carla.World) -> carla.Vehicle | None:
    for actor in world.get_actors().filter("vehicle.*"):
        if actor.attributes.get("role_name") == "acceptance84:ego":
            return actor
    return None


def encode_frame(image: carla.Image, ego: carla.Vehicle) -> None:
    frame = Image.frombuffer(
        "RGBA", (image.width, image.height), image.raw_data, "raw", "BGRA", 0, 1,
    ).convert("RGB")
    velocity = ego.get_velocity()
    speed_kph = 3.6 * (
        velocity.x * velocity.x + velocity.y * velocity.y + velocity.z * velocity.z
    ) ** 0.5
    draw = ImageDraw.Draw(frame)
    label = f"S2 FULL 8 KM | frame {image.frame} | {speed_kph:5.1f} km/h"
    draw.rectangle((12, 12, 520, 52), fill=(0, 0, 0))
    draw.text((22, 23), label, fill=(255, 255, 255))
    output = io.BytesIO()
    frame.save(output, "JPEG", quality=80)
    FRAMES.publish(output.getvalue())


def _latest_log(log_dir: Path, scenario_id: str) -> Path | None:
    candidates = list(log_dir.glob(f"{scenario_id}_*.jsonl"))
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def watch_commands(
    log_dir: Path, scenario_id: str, command_log: Path | None = None,
) -> None:
    active_path: Path | None = None
    stream = None
    try:
        while not STOP.wait(0.2):
            latest = (
                command_log
                if command_log is not None and command_log.is_file()
                else _latest_log(log_dir, scenario_id)
            )
            if latest is None:
                continue
            if latest != active_path:
                if stream is not None:
                    stream.close()
                active_path = latest
                stream = latest.open("r", encoding="utf-8")
            assert stream is not None
            while True:
                position = stream.tell()
                line = stream.readline()
                if not line:
                    stream.seek(position)
                    break
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("record_type") == "canonical_command_route":
                    COMMANDS.publish(record, active_path)
    finally:
        if stream is not None:
            stream.close()


PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CARLA 场景2 · 完整8km</title>
<style>
html,body{margin:0;height:100%;overflow:hidden;background:#080b10;color:#fff;font-family:"Microsoft YaHei",sans-serif}
main{height:100%;display:grid;place-items:center;position:relative}
#stream{width:100vw;height:100vh;object-fit:contain;background:#080b10}
#top{position:absolute;top:16px;right:18px;display:flex;gap:10px;align-items:center}
.pill{border:1px solid #ffffff45;background:#07111ddd;color:#fff;border-radius:999px;padding:9px 15px;font-size:14px;backdrop-filter:blur(8px)}
#subtitle{display:none;position:absolute;left:50%;bottom:38px;transform:translateX(-50%);width:min(92vw,1100px);box-sizing:border-box;text-align:center;background:#05080de8;border:1px solid #ffffff38;border-radius:14px;padding:17px 24px 15px;box-shadow:0 10px 40px #000a}
#subtitle.show{display:block}
#caption{font-size:clamp(19px,2.1vw,32px);font-weight:750;line-height:1.45;text-shadow:0 2px 3px #000}
#meta{margin-top:7px;color:#8ee7c6;font-size:13px;letter-spacing:.04em}
</style></head><body><main>
<img id="stream" src="/stream.mjpg" alt="CARLA实时驾驶画面">
<div id="top"><span class="pill" id="connection">连接中</span></div>
<section id="subtitle"><div id="caption">等待第一条驾驶指令…</div><div id="meta">Town03_Opt · Qwen 2B · 完整8km</div></section>
</main><script>
let lastSequence=0,hideTimer=null;
const subtitle=document.getElementById('subtitle'), caption=document.getElementById('caption');
const meta=document.getElementById('meta'), connection=document.getElementById('connection');
async function poll(){
  try{
    const response=await fetch('/status.json',{cache:'no-store'}); const status=await response.json();
    connection.textContent='实时连接';
    if(status.sequence!==lastSequence){
      lastSequence=status.sequence; caption.textContent=status.source_text;
      meta.textContent=`第 ${status.sequence} 条 · ${status.command_id||''} · Qwen 2B`;
      if(status.sequence>0){
        subtitle.classList.add('show'); clearTimeout(hideTimer);
        const visibleMs=Math.max(10000,Math.min(20000,status.source_text.length*250));
        hideTimer=setTimeout(()=>subtitle.classList.remove('show'),visibleMs);
      }
    }
  }catch(_){connection.textContent='等待数据';}
  setTimeout(poll,250);
}
poll();
</script></body></html>""".encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)
            return
        if self.path == "/status.json":
            body = json.dumps(COMMANDS.snapshot(), ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path != "/stream.mjpg":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        sequence = -1
        try:
            while not STOP.is_set():
                sequence, jpeg = FRAMES.wait_after(sequence)
                if jpeg is None:
                    continue
                self.wfile.write(
                    b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(jpeg)).encode("ascii") + b"\r\n\r\n" + jpeg + b"\r\n"
                )
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--carla-port", type=int, default=2000)
    parser.add_argument("--http-port", type=int, default=18081)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--log-dir", type=Path, required=True)
    parser.add_argument(
        "--command-log", type=Path,
        help="runner console log containing canonical_command_route records",
    )
    parser.add_argument(
        "--scenario-id", default="OFFICIAL_S2_COMPLEX_AVOIDANCE_8KM",
    )
    args = parser.parse_args()

    client = carla.Client(args.host, args.carla_port)
    client.set_timeout(5.0)
    world = client.get_world()
    server = ThreadingHTTPServer(("127.0.0.1", args.http_port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(
        target=watch_commands,
        args=(
            args.log_dir.resolve(),
            args.scenario_id,
            args.command_log.resolve() if args.command_log is not None else None,
        ),
        daemon=True,
    ).start()
    print(f"viewer ready: http://127.0.0.1:{args.http_port}", flush=True)

    camera = None
    try:
        while not STOP.is_set() and camera is None:
            ego = ego_vehicle(world)
            if ego is None:
                time.sleep(0.25)
                world = client.get_world()
                continue
            blueprint = world.get_blueprint_library().find("sensor.camera.rgb")
            blueprint.set_attribute("image_size_x", str(args.width))
            blueprint.set_attribute("image_size_y", str(args.height))
            blueprint.set_attribute("fov", "100")
            blueprint.set_attribute("sensor_tick", "0.05")
            transform = carla.Transform(
                carla.Location(x=-8.0, z=4.2), carla.Rotation(pitch=-13.0),
            )
            camera = world.spawn_actor(
                blueprint,
                transform,
                attach_to=ego,
                attachment_type=carla.AttachmentType.SpringArmGhost,
            )
            camera.listen(lambda image: encode_frame(image, ego))
            print(f"viewer attached: ego={ego.id}, camera={camera.id}", flush=True)
        while not STOP.wait(0.5):
            if camera is not None and not camera.is_alive:
                break
    finally:
        STOP.set()
        server.shutdown()
        server.server_close()
        if camera is not None:
            try:
                camera.stop()
                camera.destroy()
            except RuntimeError:
                pass


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_args: STOP.set())
    signal.signal(signal.SIGINT, lambda *_args: STOP.set())
    main()
