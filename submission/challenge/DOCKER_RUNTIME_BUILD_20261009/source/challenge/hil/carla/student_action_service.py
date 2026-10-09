"""Put the lightweight Student into the CARLA closed loop through the A-E contract.

The repo's CARLA runner already supports a remote high-level decision module:
``python -m integration.carla_runner --qwen-remote --qwen-base-url <url>`` posts an
OpenAI-compatible chat completion whose prompt carries the structured context
(``build_action_choice_prompt``) and whose answer is a single letter::

    A=START  B=STOP  C=SLOW_DOWN  D=SET_SPEED  E=EMERGENCY_STOP

This module serves that endpoint while the decision comes from the distilled
Student ONNX (v3 candidate) instead of the 2B VLM, so the same scenarios, the
same acceptance criteria and the same safety chain can be used to measure the
lightweight model in the loop.

Degraded-but-declared mappings (all of them are logged per request):

* the prompt carries voice/vehicle/perception/safety only, so ``command_hint``
  is reconstructed by a deterministic keyword table over the voice text;
* ``scene_capabilities`` is **not** in the live payload.  We publish a
  conservative set (route available, no lateral lane, no intersection) because
  the execution contract only realizes longitudinal actions; the decoder masks
  lateral behaviours exactly as it does in the deployed adapter;
* an image is only available as the inlined JPEG (already montaged by the
  runner), which is a geometry shift against the 224x224 training frames.

Every request also writes one JSONL record (payload, reconstructed request,
plan, chosen letter, latency), so the run can be audited afterwards.

Usage::

    py -3.12 -m challenge.hil.carla.student_action_service \
        --onnx D:\\nana\\oe\\work\\v3\\student_v0_fp32_v3.onnx \
        --port 8100 --log-dir challenge/hil/artifacts/student_loop
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import onnxruntime as ort
import torch

from challenge.planner.student_adapter import StudentPlanAdapter
from challenge.student.contract import OUTPUT_NAMES
from challenge.student.preprocess import StudentPreprocessor


PROMPT_INPUT_MARKER = "输入:"
ACTION_CODES = ("A", "B", "C", "D", "E")

# Behaviour -> strict /infer action (the five intents the boundary validates).
_BEHAVIOUR_ACTION = {
    "STOP": "STOP",
    "HOLD": "STOP",
    "PULL_OVER": "STOP",
    "EMERGENCY_STOP": "EMERGENCY_STOP",
    "YIELD": "SLOW_DOWN",
    "SLOW_DOWN": "SLOW_DOWN",
    "FOLLOW": "SLOW_DOWN",
    "AVOID_OBSTACLE": "SLOW_DOWN",
    "SET_SPEED": "SET_SPEED",
    "KEEP_LANE": "START",
    "RETURN_TO_LANE": "START",
    "TURN_LEFT": "START",
    "TURN_RIGHT": "START",
    "CHANGE_LANE_LEFT": "START",
    "CHANGE_LANE_RIGHT": "START",
}
_SPEED_ACTIONS = {"SET_SPEED", "SLOW_DOWN"}

# Deterministic voice-intent table.  The voice front end is another group's
# deliverable and is not available to the closed loop, so the intent is
# reconstructed from the scenario command text and recorded in the evidence.
_INTENT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("EMERGENCY_STOP", ("紧急", "急刹", "马上停", "立刻停")),
    # PULL_OVER must be tested before the plain stop keywords: "靠边停车"
    # contains "停车" but is a pull-over request, not a stop request.
    ("PULL_OVER", ("靠边", "路边")),
    ("STOP", ("停车", "停下", "停稳", "停 ") ),
    ("SET_SPEED", ("速度", "限速", "每小时", "km/h", "公里")),
    ("SLOW_DOWN", ("慢", "减速", "收油", "别太快")),
    ("FOLLOW", ("跟车", "跟随", "跟着")),
    ("AVOID_OBSTACLE", ("绕开", "绕行", "避让", "避障")),
    ("CHANGE_LANE", ("变道", "换道")),
    ("YIELD", ("让行", "让一下")),
    ("TURN", ("左转", "右转", "转弯")),
    ("KEEP_LANE", ("保持车道", "不要变道", "直行")),
)
_DIRECTION_KEYWORDS = (("LEFT", ("左",)), ("RIGHT", ("右",)), ("STRAIGHT", ("直行",)))

# Behaviour -> A-E letter.  STOP/HOLD/PULL_OVER stop; YIELD/SLOW_DOWN slow down;
# SET_SPEED keeps the commanded speed; FOLLOW/AVOID follow the repo prompt rule
# ("explicit follow or avoid without stop risk -> C"); everything else keeps
# driving.  Lateral behaviours are included because the executor cannot realize
# them anyway and the deterministic safety layer still guards the vehicle.
_BEHAVIOUR_LETTER = {
    "STOP": "B",
    "HOLD": "B",
    "PULL_OVER": "B",
    "EMERGENCY_STOP": "B",
    "YIELD": "C",
    "SLOW_DOWN": "C",
    "FOLLOW": "C",
    "AVOID_OBSTACLE": "C",
    "SET_SPEED": "D",
    "KEEP_LANE": "A",
    "RETURN_TO_LANE": "A",
    "TURN_LEFT": "A",
    "TURN_RIGHT": "A",
    "CHANGE_LANE_LEFT": "A",
    "CHANGE_LANE_RIGHT": "A",
    "START": "A",
}

_ALLOWED_BY_INTENT = {
    "EMERGENCY_STOP": ["SLOW_DOWN", "STOP"],
    "STOP": ["SLOW_DOWN", "STOP", "KEEP_LANE"],
    "PULL_OVER": ["SLOW_DOWN", "STOP", "CHANGE_LANE", "KEEP_LANE"],
    "SET_SPEED": ["SET_SPEED", "SLOW_DOWN", "STOP", "KEEP_LANE"],
    "SLOW_DOWN": ["SLOW_DOWN", "STOP", "KEEP_LANE"],
    "FOLLOW": ["FOLLOW", "SLOW_DOWN", "STOP", "KEEP_LANE", "SET_SPEED"],
    "AVOID_OBSTACLE": [
        "AVOID_OBSTACLE", "SLOW_DOWN", "STOP", "CHANGE_LANE",
        "RETURN_TO_LANE", "KEEP_LANE",
    ],
    "CHANGE_LANE": ["CHANGE_LANE", "KEEP_LANE", "SLOW_DOWN", "STOP"],
    "YIELD": ["YIELD", "SLOW_DOWN", "STOP", "KEEP_LANE"],
    "TURN": ["TURN", "SLOW_DOWN", "STOP", "KEEP_LANE", "SET_SPEED"],
    "KEEP_LANE": ["KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "STOP"],
}

_CLASS_MAP = {
    "person": "pedestrian",
    "pedestrian": "pedestrian",
    "bicycle": "cyclist",
    "motorcycle": "cyclist",
    "cyclist": "cyclist",
    "car": "vehicle",
    "truck": "vehicle",
    "bus": "vehicle",
    "vehicle": "vehicle",
    "obstacle": "obstacle",
    "static.prop": "obstacle",
    "static": "obstacle",
    "roadblock": "obstacle",
}


def voice_intent(text: str) -> tuple[str, str | None]:
    normalized = str(text or "")
    for intent, keywords in _INTENT_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            direction = None
            for name, marks in _DIRECTION_KEYWORDS:
                if any(mark in normalized for mark in marks):
                    direction = name
                    break
            if intent == "TURN" and direction not in {"LEFT", "RIGHT"}:
                direction = None
            if intent == "CHANGE_LANE" and direction not in {"LEFT", "RIGHT"}:
                direction = None
            return intent, direction
    return "KEEP_LANE", None


def _finite(value: object, default: float | None = None) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    value = float(value)
    return value if math.isfinite(value) else default


def _targets_from_perception(perception: Mapping[str, Any]) -> list[dict[str, Any]]:
    objects = perception.get("detected_objects")
    if not isinstance(objects, list):
        return []
    targets: list[dict[str, Any]] = []
    for index, item in enumerate(objects[:8]):
        if not isinstance(item, Mapping):
            continue
        raw_class = str(item.get("class", item.get("class_name", "unknown"))).lower()
        distance = _finite(item.get("distance_m"), 0.0) or 0.0
        relation = str(item.get("relation", "") or "")
        if not relation:
            relation = "center_ahead"
        targets.append({
            "target_id": str(item.get("track_id") or f"T-{index:03d}"),
            "class": _CLASS_MAP.get(raw_class, "unknown"),
            "confidence": _finite(item.get("confidence"), 0.5) or 0.5,
            "distance_m": max(0.0, float(distance)),
            "relation": relation,
            "relative_speed_mps": _finite(item.get("relative_speed_mps"), None),
        })
    return targets


def build_student_request(
    payload: Mapping[str, Any],
    *,
    rgb_path: Path | None,
    request_id: str,
    speed_limit_mps: float = 8.333333333333334,
) -> dict[str, Any]:
    """Map one live payload onto the Student request contract.

    Three live shapes are accepted:

    * the canonical planner-v2 **model request** (``constraints`` +
      ``command_hint`` + ``scene_summary``) -- used as-is, because it already
      carries the real ``scene_capabilities`` from the runtime and is the
      distribution the Student was trained on;
    * the strict ``/infer`` context (``voice_command``/``scene_state``/
      ``perception``/``safety_state``) -- synthesised;
    * the A-E prompt payload (``voice``/``vehicle``/...) -- synthesised.
    """
    if isinstance(payload.get("constraints"), Mapping) and isinstance(
        payload.get("scene_summary"), Mapping,
    ):
        request = dict(payload)
        if rgb_path is not None:
            request["rgb_ref"] = str(rgb_path)
        elif not request.get("rgb_ref"):
            request["rgb_ref"] = None
        request.setdefault("command_hint", {"intent": "KEEP_LANE"})
        return request
    if "voice_command" in payload or "scene_state" in payload:
        voice = str(payload.get("voice_command") or "")
        vehicle = payload.get("scene_state") if isinstance(payload.get("scene_state"), Mapping) else {}
        safety = payload.get("safety_state") if isinstance(payload.get("safety_state"), Mapping) else {}
    else:
        voice = str(payload.get("voice") or "")
        vehicle = payload.get("vehicle") if isinstance(payload.get("vehicle"), Mapping) else {}
        safety = payload.get("safety") if isinstance(payload.get("safety"), Mapping) else {}
    perception = payload.get("perception") if isinstance(payload.get("perception"), Mapping) else {}
    intent, direction = voice_intent(voice)
    ego_speed = _finite(vehicle.get("speed_mps"), _finite(vehicle.get("ego_speed_mps"), 0.0)) or 0.0
    lead_distance = _finite(perception.get("lead_distance_m"), None)
    ttc = _finite(safety.get("minimum_ttc_s"), _finite(safety.get("ttc_s"), None))
    collision = bool(safety.get("collision"))
    recommended = str(safety.get("recommended_action") or "").upper()
    must_stop = intent == "EMERGENCY_STOP" or recommended == "STOP" or collision
    if collision:
        risk = "EMERGENCY"
    elif recommended == "STOP" or (ttc is not None and ttc <= 2.0):
        risk = "HIGH"
    elif lead_distance is not None and lead_distance < 15.0:
        risk = "CAUTION"
    else:
        risk = "LOW"
    traffic_light = str(perception.get("traffic_light") or "UNKNOWN").upper()
    if traffic_light not in {"RED", "YELLOW", "GREEN", "UNKNOWN"}:
        traffic_light = "UNKNOWN"
    speed_limit = _finite(perception.get("speed_limit_mps"), speed_limit_mps) or speed_limit_mps
    now_ns = time.time_ns()
    return {
        "schema_version": "1.0",
        "request_id": request_id,
        "command_id": request_id,
        "created_at_ns": now_ns,
        "deadline_ns": now_ns + 500_000_000,
        "source_text": voice,
        "rgb_ref": str(rgb_path) if rgb_path is not None else None,
        "targets": _targets_from_perception(perception),
        "command_hint": {
            "intent": intent,
            "direction": direction,
            "target": None,
            "target_speed_mps": None,
        },
        "constraints": {
            "allowed_behaviors": list(_ALLOWED_BY_INTENT.get(intent, ["KEEP_LANE", "SLOW_DOWN", "STOP"])),
            "must_stop": must_stop,
            "speed_limit_mps": float(speed_limit),
            "max_target_speed_mps": float(speed_limit),
        },
        "scene_summary": {
            "traffic_light": traffic_light,
            "risk_level": risk,
            "min_gap_m": lead_distance,
            "ttc_s": ttc,
            "sim_time_s": 0.0,
            "frame_id": 0,
        },
        # Declared conservative defaults: the live payload carries no map
        # topology and the execution contract cannot realize lateral manoeuvres.
        "scene_capabilities": {
            "available_lanes": ["CURRENT"],
            "current_lane": "1",
            "original_lane": "1",
            "left_lane_exists": False,
            "right_lane_exists": False,
            "left_gap_safe": False,
            "right_gap_safe": False,
            "route_available": True,
            "intersection_ahead": False,
            "stop_line_clear": True,
            "grounded_target_ids": [],
        },
        "routing": {
            "disposition": "QWEN_PLAN",
            "reasons": ["ROUTE_REFERENCE"],
            "safe_wait_behavior": "KEEP_LANE_LIMITED",
            "score": 0,
        },
        "ego_speed_mps": ego_speed,
    }


def plan_to_letter(plan: Mapping[str, Any]) -> tuple[str, str]:
    """Map the Student plan's first step onto the A-E action boundary."""
    steps = plan.get("steps") or []
    if not steps:
        return "B", ""
    behaviour = str(steps[0].get("behavior") or "").upper()
    return _BEHAVIOUR_LETTER.get(behaviour, "A"), behaviour


def plan_to_action(
    plan: Mapping[str, Any], request: Mapping[str, Any],
) -> tuple[str, float | None, str]:
    """Map the Student plan onto the strict five-intent decision."""
    steps = plan.get("steps") or []
    if not steps:
        return "STOP", None, ""
    step = steps[0]
    behaviour = str(step.get("behavior") or "").upper()
    action = _BEHAVIOUR_ACTION.get(behaviour, "START")
    target = step.get("target") if isinstance(step.get("target"), Mapping) else {}
    speed = _finite(target.get("target_speed_mps"), None)
    if speed is None:
        speed = _finite(request.get("ego_speed_mps"), None)
    if action in _SPEED_ACTIONS:
        limits = [50.0]
        constraints = request.get("constraints") if isinstance(request.get("constraints"), Mapping) else {}
        for key in ("speed_limit_mps", "max_target_speed_mps"):
            value = _finite(constraints.get(key), None)
            if value is not None:
                limits.append(float(value))
        speed = 0.0 if speed is None else max(0.0, min(float(speed), *limits))
    else:
        speed = None
    return action, speed, behaviour


def parse_prompt_payload(prompt: str) -> dict[str, Any]:
    marker = prompt.find(PROMPT_INPUT_MARKER)
    if marker < 0:
        raise ValueError("prompt has no '输入:' section")
    remainder = prompt[marker + len(PROMPT_INPUT_MARKER):].lstrip()
    payload, _ = json.JSONDecoder().raw_decode(remainder)
    if not isinstance(payload, dict):
        raise TypeError("prompt payload must be a JSON object")
    return payload


def _extract_content(messages: object) -> tuple[str, bytes | None]:
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")
    text_parts: list[str] = []
    image: bytes | None = None
    for message in messages:
        if not isinstance(message, Mapping):
            continue
        content = message.get("content")
        if isinstance(content, str):
            text_parts.append(content)
            continue
        if not isinstance(content, list):
            continue
        for entry in content:
            if not isinstance(entry, Mapping):
                continue
            kind = entry.get("type")
            if kind == "text":
                text_parts.append(str(entry.get("text") or ""))
            elif kind == "image_url":
                url = entry.get("image_url")
                if isinstance(url, Mapping):
                    url = url.get("url")
                if isinstance(url, str) and url.startswith("data:"):
                    _, _, encoded = url.partition(",")
                    image = base64.b64decode(encoded)
    return "\n".join(text_parts), image


class StudentDecisionEngine:
    def __init__(
        self,
        onnx_path: str | Path,
        *,
        image_dir: Path,
        image_root: Path | None = None,
        confidence_mode: str = "plan",
        fixed_confidence: float = 0.9,
        zero_inputs: tuple[str, ...] = (),
    ) -> None:
        self.onnx_path = Path(onnx_path)
        self.session = ort.InferenceSession(
            str(self.onnx_path), providers=["CPUExecutionProvider"],
        )
        self.input_names = [item.name for item in self.session.get_inputs()]
        self.output_names = [item.name for item in self.session.get_outputs()]
        missing = [name for name in OUTPUT_NAMES if name not in self.output_names]
        if missing:
            raise ValueError(f"ONNX is missing Student outputs: {missing}")
        self.preprocessor = StudentPreprocessor()
        self.adapter = StudentPlanAdapter()
        self.image_dir = Path(image_dir)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.image_root = Path(image_root) if image_root is not None else None
        self.confidence_mode = confidence_mode
        self.fixed_confidence = float(fixed_confidence)
        unknown = [name for name in zero_inputs if name not in self.input_names]
        if unknown:
            raise ValueError(f"--zero-input names not in the model inputs: {unknown}")
        self.zero_inputs = tuple(zero_inputs)
        self._lock = threading.Lock()

    def _materialize_image(self, image: bytes | None, request_id: str) -> Path | None:
        if not image:
            return None
        digest = hashlib.sha256(image).hexdigest()[:16]
        path = self.image_dir / f"{request_id}-{digest}.jpg"
        if not path.exists():
            path.write_bytes(image)
        return path

    def _resolve_reference(self, reference: object) -> Path | None:
        """Resolve an /infer ``rgb_ref`` (absolute or prefix-relative)."""
        if not isinstance(reference, str) or not reference.strip():
            return None
        raw = Path(reference)
        candidates: list[Path] = []
        if raw.is_absolute():
            candidates.append(raw)
        candidates.append(Path(raw.name))
        if self.image_root is not None:
            candidates.append(self.image_root / raw)
            candidates.append(self.image_root / raw.name)
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        return None

    def decide(
        self,
        payload: Mapping[str, Any],
        image: bytes | None,
        request_id: str,
    ) -> dict[str, Any]:
        rgb_path = self._materialize_image(image, request_id)
        if rgb_path is None:
            rgb_path = self._resolve_reference(payload.get("rgb_ref"))
        request = build_student_request(payload, rgb_path=rgb_path, request_id=request_id)
        tensors = self.preprocessor(request)
        feed = {
            name: np.asarray(getattr(tensors, name), dtype=np.float32)
            for name in self.input_names
        }
        for name in self.zero_inputs:
            # Closed-loop modality ablation: keep the tensor's shape and dtype
            # but replace the content with its zero value.
            feed[name] = np.zeros_like(feed[name])
        started = time.perf_counter()
        with self._lock:
            raw = dict(zip(self.output_names, self.session.run(self.output_names, feed)))
        inference_ms = (time.perf_counter() - started) * 1000.0
        outputs = {name: torch.from_numpy(array) for name, array in raw.items()}
        plan = self.adapter.decode(request, outputs)
        letter, behaviour = plan_to_letter(plan)
        action, action_speed, behaviour = plan_to_action(plan, request)
        plan_confidence = max(0.0, min(1.0, float(plan.get("confidence", 0.0))))
        confidence = (
            plan_confidence if self.confidence_mode == "plan" else self.fixed_confidence
        )
        return {
            "request": request,
            "plan": plan,
            "behaviour": behaviour,
            "letter": letter,
            "action": action,
            "action_speed_mps": action_speed,
            "rgb_ref": str(rgb_path) if rgb_path is not None else None,
            "zero_inputs": list(self.zero_inputs),
            "plan_confidence": plan_confidence,
            "confidence": confidence,
            "inference_ms": inference_ms,
        }


class _Handler(BaseHTTPRequestHandler):
    server_version = "B3StudentActionService/1.0"
    engine: StudentDecisionEngine
    log_dir: Path
    infer_response: str = "plan"
    counters: dict[str, Any] = {}
    counter_lock = threading.Lock()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return

    def _send(self, code: int, payload: Mapping[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib signature
        if self.path.rstrip("/") in {"/health", "/v1/health"}:
            self._send(200, {
                "status": "READY",
                "production_ready": True,
                "backend": "student_onnx",
                "model": self.engine.onnx_path.name,
                "confidence_mode": self.engine.confidence_mode,
                "requests": self.counters.get("requests", 0),
            })
        elif self.path.rstrip("/") == "/metrics":
            with self.counter_lock:
                snapshot = json.loads(json.dumps(self.counters))
            latencies = sorted(snapshot.pop("latencies_ms", []))

            def percentile(fraction: float) -> float | None:
                if not latencies:
                    return None
                index = min(len(latencies) - 1, int(round(fraction * (len(latencies) - 1))))
                return latencies[index]

            snapshot["latency_ms"] = {
                "p50": percentile(0.50), "p95": percentile(0.95), "max": latencies[-1] if latencies else None,
            }
            self._send(200, snapshot)
        elif self.path.rstrip("/") == "/v1/models":
            self._send(200, {"object": "list", "data": [{"id": "student-v0-r3-fp32", "object": "model"}]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib signature
        route = self.path.rstrip("/")
        if route == "/infer":
            self._handle_infer()
            return
        if route not in {"/v1/chat/completions", "/chat/completions"}:
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b"{}"
        started = time.perf_counter()
        try:
            payload = json.loads(body.decode("utf-8"))
            prompt, image = _extract_content(payload.get("messages"))
            context = parse_prompt_payload(prompt)
            request_id = "req-" + hashlib.sha256(
                (prompt + str(time.time_ns())).encode("utf-8")
            ).hexdigest()[:16]
            result = self.engine.decide(context, image, request_id)
        except Exception as error:  # fail closed on any malformed request
            with self.counter_lock:
                self.counters["errors"] = self.counters.get("errors", 0) + 1
                self.counters["requests"] = self.counters.get("requests", 0) + 1
                self.counters.setdefault("last_error", f"{type(error).__name__}: {error}")
            self._record({
                "request_id": None, "error": f"{type(error).__name__}: {error}",
                "letter": "B", "fail_closed": True,
            })
            self._respond("B", 0.0, None, fail_closed=True)
            return
        with self.counter_lock:
            self.counters["requests"] = self.counters.get("requests", 0) + 1
            letters = self.counters.setdefault("letters", {})
            letters[result["letter"]] = letters.get(result["letter"], 0) + 1
            behaviours = self.counters.setdefault("behaviours", {})
            behaviours[result["behaviour"]] = behaviours.get(result["behaviour"], 0) + 1
            self.counters.setdefault("latencies_ms", []).append(result["inference_ms"])
        latency_ms = (time.perf_counter() - started) * 1000.0
        self._record({
            "request_id": result["request"]["request_id"],
            "voice": result["request"]["source_text"],
            "intent": result["request"]["command_hint"]["intent"],
            "payload": context,
            "student_request": result["request"],
            "plan": result["plan"],
            "behaviour": result["behaviour"],
            "letter": result["letter"],
            "plan_confidence": result["plan_confidence"],
            "reported_confidence": result["confidence"],
            "inference_ms": result["inference_ms"],
            "handler_ms": latency_ms,
        })
        self._respond(result["letter"], result["confidence"], result["behaviour"])

    def _handle_infer(self) -> None:
        """Strict repository contract: POST /infer -> one five-intent decision."""
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b"{}"
        started = time.perf_counter()
        request_id: str | None = None
        try:
            payload = json.loads(body.decode("utf-8"))
            request_id = str(payload.get("request_id") or "")
            if not request_id:
                raise ValueError("request_id is required")
            result = self.engine.decide(payload, None, request_id)
        except Exception as error:  # fail closed: no plan, no progress
            with self.counter_lock:
                self.counters["errors"] = self.counters.get("errors", 0) + 1
                self.counters["requests"] = self.counters.get("requests", 0) + 1
                self.counters.setdefault("last_error", f"{type(error).__name__}: {error}")
            self._record({
                "request_id": request_id, "error": f"{type(error).__name__}: {error}",
                "action": "STOP", "fail_closed": True,
            })
            self._send(200, {
                "status": "READY",
                "request_id": request_id or "unknown",
                "decision": {
                    "action": "STOP", "confidence": 0.0,
                    "requires_confirmation": True,
                    "reason_zh": "STUDENT_FAIL_CLOSED",
                },
            })
            return
        with self.counter_lock:
            self.counters["requests"] = self.counters.get("requests", 0) + 1
            actions = self.counters.setdefault("actions", {})
            actions[result["action"]] = actions.get(result["action"], 0) + 1
            behaviours = self.counters.setdefault("behaviours", {})
            behaviours[result["behaviour"]] = behaviours.get(result["behaviour"], 0) + 1
            self.counters.setdefault("latencies_ms", []).append(result["inference_ms"])
        latency_ms = (time.perf_counter() - started) * 1000.0
        self._record({
            "contract": "infer",
            "request_id": result["request"]["request_id"],
            "voice": result["request"]["source_text"],
            "intent": result["request"]["command_hint"]["intent"],
            "payload": payload,
            "student_request": result["request"],
            "plan": result["plan"],
            "behaviour": result["behaviour"],
            "action": result["action"],
            "action_speed_mps": result["action_speed_mps"],
            "rgb_ref": result["rgb_ref"],
            "plan_confidence": result["plan_confidence"],
            "reported_confidence": result["confidence"],
            "inference_ms": result["inference_ms"],
            "handler_ms": latency_ms,
        })
        decision: dict[str, Any] = {
            "action": result["action"],
            "confidence": result["confidence"],
            "requires_confirmation": False,
            "reason_zh": "STUDENT_V0_STRUCTURED",
            "decision_source": "STUDENT_ONNX",
        }
        if result["action_speed_mps"] is not None:
            decision["target_speed_mps"] = float(result["action_speed_mps"])
        if self.infer_response == "plan":
            # The canonical orchestrator validates the response body itself as
            # the plan (planner_v2 mode) or as a decision_plan (atomic_v1).
            self._send(200, result["plan"])
        else:
            self._send(200, {
                "status": "READY",
                "request_id": result["request"]["request_id"],
                "decision": decision,
            })

    def _respond(
        self,
        letter: str,
        confidence: float,
        behaviour: str | None,
        *,
        fail_closed: bool = False,
    ) -> None:
        logprob = -math.inf if fail_closed else math.log(max(min(confidence, 1.0), 1e-6))
        self._send(200, {
            "id": "chatcmpl-b3student",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "student-v0-r3-fp32",
            "choices": [{
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": letter},
                "logprobs": {
                    "content": [{
                        "token": letter,
                        "logprob": logprob,
                        "bytes": None,
                        "top_logprobs": [],
                    }]
                },
            }],
            "b3_student": {"behaviour": behaviour, "fail_closed": fail_closed},
        })

    def _record(self, entry: Mapping[str, Any]) -> None:
        entry = dict(entry)
        entry["wall_time_utc"] = datetime.now(timezone.utc).isoformat()
        path = self.log_dir / "student_decisions.jsonl"
        with self.counter_lock:
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")


def build_server(
    *,
    onnx_path: str | Path,
    host: str,
    port: int,
    log_dir: Path,
    image_dir: Path,
    image_root: Path | None = None,
    confidence_mode: str = "plan",
    fixed_confidence: float = 0.9,
    infer_response: str = "plan",
    zero_inputs: tuple[str, ...] = (),
) -> ThreadingHTTPServer:
    engine = StudentDecisionEngine(
        onnx_path,
        image_dir=image_dir,
        image_root=image_root,
        confidence_mode=confidence_mode,
        fixed_confidence=fixed_confidence,
        zero_inputs=zero_inputs,
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = type("_BoundHandler", (_Handler,), {
        "engine": engine, "log_dir": log_dir, "infer_response": infer_response,
        "counters": {}, "counter_lock": threading.Lock(),
    })
    server = ThreadingHTTPServer((host, port), handler)
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--log-dir", default="challenge/hil/artifacts/student_loop")
    parser.add_argument("--image-dir", default="challenge/hil/artifacts/student_loop/images")
    parser.add_argument(
        "--image-root",
        default=None,
        help="root the CARLA runner stages its 224x224 JPEGs under (resolves /infer rgb_ref)",
    )
    parser.add_argument("--confidence-mode", choices=("plan", "fixed"), default="plan")
    parser.add_argument(
        "--infer-response", choices=("plan", "envelope"), default="plan",
        help="plan = return the ManeuverPlan itself (canonical CARLA path); "
             "envelope = {status, request_id, decision} for the scenario_runner agent",
    )
    parser.add_argument("--fixed-confidence", type=float, default=0.9)
    parser.add_argument(
        "--zero-input", action="append", default=[],
        choices=["rgb", "text_tokens", "targets", "state"],
        help="replace one model input with zeros (closed-loop modality ablation); repeatable",
    )
    args = parser.parse_args()
    server = build_server(
        onnx_path=args.onnx,
        host=args.host,
        port=args.port,
        log_dir=Path(args.log_dir),
        image_dir=Path(args.image_dir),
        image_root=Path(args.image_root) if args.image_root else None,
        confidence_mode=args.confidence_mode,
        fixed_confidence=args.fixed_confidence,
        infer_response=args.infer_response,
        zero_inputs=tuple(args.zero_input),
    )
    print(f"student action service on http://{args.host}:{args.port} (onnx={args.onnx})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "StudentDecisionEngine",
    "build_server",
    "build_student_request",
    "parse_prompt_payload",
    "plan_to_action",
    "plan_to_letter",
    "voice_intent",
]
