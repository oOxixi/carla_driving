"""Explicit adapters that compose the independently delivered control modules."""

from .contracts import DetectedObject, FrameResult, PerceptionFrame
from .carla_perception import CarlaPerceptionBridge, PerceptionAcquisitionError, PerceptionSample
from .offline_replay import ReplayFrameResult, ReplayReport, run_replay_manifest
from .qwen_async import AsyncDecisionResult, AsyncQwenDecisionBridge
from .qwen_boundary import QwenBoundaryFailure, QwenInputContext, fail_closed, validate_qwen_response
from .qwen_vl_adapter import QwenVLInferenceTrace, StrictQwenVLAdapter
from .runtime_loop import ControlRuntime
from .voice_adapter import AdaptedVoiceCommand, VoiceCommandAdapter

__all__ = [
    "AdaptedVoiceCommand", "AsyncDecisionResult", "AsyncQwenDecisionBridge",
    "CarlaPerceptionBridge", "ControlRuntime", "DetectedObject", "FrameResult",
    "PerceptionAcquisitionError", "PerceptionFrame", "PerceptionSample",
    "QwenBoundaryFailure", "QwenInputContext", "ReplayFrameResult", "ReplayReport",
    "QwenVLInferenceTrace", "StrictQwenVLAdapter", "VoiceCommandAdapter",
    "fail_closed", "run_replay_manifest", "validate_qwen_response",
]
