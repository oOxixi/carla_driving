"""
语音组完整链路（交付版）—— A + B1 + B2 → DrivingCommand

车辆控制组用法：
    from pipeline import audio_to_command
    cmd = audio_to_command("some.wav")     # 返回 DrivingCommand dict

或命令行：python pipeline.py some.wav

依赖见 README。B1/B2 模块须与本文件在同一目录（vehicle_nlu/ 和 nlu_b2/）。
"""
import os, sys, time, json, uuid

if __package__:
    from .asr_vad import ASR
    from .asr_cascade import (
        CascadeConfig,
        FasterWhisperVerifier,
        apply_verification,
        mark_verifier_unavailable,
        needs_verification,
    )
    from .vehicle_nlu.src.b1_service import process_asr_text
    from .nlu_b2.parser import parse_command
else:
    # 兼容直接执行 ``python voice_group/pipeline.py audio.wav``。
    _HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _HERE)
    from asr_vad import ASR
    from asr_cascade import (
        CascadeConfig,
        FasterWhisperVerifier,
        apply_verification,
        mark_verifier_unavailable,
        needs_verification,
    )
    from vehicle_nlu.src.b1_service import process_asr_text
    from nlu_b2.parser import parse_command

_asr = None
_verifier = None
_cascade_config = None


def _get_asr():
    global _asr
    if _asr is None:
        _asr = ASR()
    return _asr


def _get_cascade_config():
    global _cascade_config
    if _cascade_config is None:
        _cascade_config = CascadeConfig.from_environment()
    return _cascade_config


def _get_verifier():
    global _verifier
    if _verifier is None:
        _verifier = FasterWhisperVerifier(_get_cascade_config())
    return _verifier


def preload_voice_models() -> dict:
    """Load both ASR models before timed command handling starts."""
    started = time.monotonic_ns()
    _get_asr()
    primary_loaded = time.monotonic_ns()
    config = _get_cascade_config()
    if config.enabled:
        _get_verifier().warmup()
    completed = time.monotonic_ns()
    return {
        "cascade_enabled": config.enabled,
        "primary_load_ms": round((primary_loaded - started) / 1e6, 1),
        "verifier_load_ms": round((completed - primary_loaded) / 1e6, 1),
        "total_load_ms": round((completed - started) / 1e6, 1),
    }


def _text_to_command(text: str, command_id: str, confidence=None) -> dict:
    b1 = process_asr_text(
        request_id=command_id,
        text=text,
        asr_confidence=confidence,
    )
    b2 = parse_command(b1)
    return {
        "source_text": text,
        "intent": b2.get("intent"),
        "parameters": b2.get("slots", {}),
        "status": b2.get("status"),
    }


def audio_to_command(audio, t_audio_start_ns: int = None) -> dict:
    """车辆控制组主入口。
    audio: 音频文件路径(str) 或 16kHz单声道 numpy 数组(实时流)。
    t_audio_start_ns: 实时场景传入采音起始时刻(time.monotonic_ns)，更准。
    返回 DrivingCommand dict。"""
    asr = _get_asr()
    cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
    t0 = time.monotonic_ns()

    a = asr.transcribe(audio, t_audio_start_ns=t_audio_start_ns)
    t_asr = time.monotonic_ns()
    b1 = process_asr_text(request_id=cmd_id, text=a["text"], asr_confidence=a["asr_confidence"])
    b2 = parse_command(b1)
    t_end = time.monotonic_ns()

    cmd = {
        "schema_version": "1.0",
        "command_id": cmd_id,
        "source_text": a["text"],
        "intent": b2.get("intent"),
        "parameters": b2.get("slots", {}),
        "asr_confidence": a["asr_confidence"],
        "intent_confidence": b2.get("intent_confidence"),
        "status": b2.get("status"),
        "ambiguity_type": "NONE" if b2.get("status") == "valid" else "AMBIGUOUS",
        "confirm_required": b2.get("status") != "valid",
        "errors": b2.get("errors", []),
        "warnings": b2.get("warnings", []),
        # 单调纳秒时间戳（time.monotonic_ns），供车辆控制组算真实端到端延时
        "t_audio_start_ns": a["t_audio_start_ns"],
        "t_asr_end_ns": a["t_asr_end_ns"],
        "t_intent_end_ns": t_end,
        "valid_duration_s": 3.0,
        "confidence": b2.get("intent_confidence"),
        "_latency": {
            "asr_ms": round((t_asr - t0) / 1e6, 1),
            "nlu_ms": round((t_end - t_asr) / 1e6, 1),
            "total_ms": round((t_end - t0) / 1e6, 1),
        },
    }
    cascade_config = _get_cascade_config()
    if cascade_config.enabled and needs_verification(cmd):
        verification_started = time.monotonic_ns()
        try:
            verification = _get_verifier().transcribe(audio)
            secondary = _text_to_command(
                verification["text"],
                f"{cmd_id}-verify",
                verification.get("calibrated_confidence"),
            )
            cmd = apply_verification(
                cmd,
                verification,
                secondary,
                minimum_confidence=(
                    cascade_config.minimum_calibrated_confidence
                ),
            )
        except Exception as error:
            cmd = mark_verifier_unavailable(cmd, error)
        cmd["_latency"]["verification_ms"] = round(
            (time.monotonic_ns() - verification_started) / 1e6,
            1,
        )
        cmd["_latency"]["total_ms"] = round(
            (time.monotonic_ns() - t0) / 1e6,
            1,
        )
    return cmd


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "test.wav"
    cmd = audio_to_command(path)
    print(json.dumps({k: v for k, v in cmd.items() if k != "_latency"}, ensure_ascii=False, indent=2))
    lat = cmd["_latency"]
    print(f"\n时延 ASR={lat['asr_ms']}ms NLU={lat['nlu_ms']}ms 端到端={lat['total_ms']}ms")
