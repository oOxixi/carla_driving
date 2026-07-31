"""Role-C synchronized multi-modal perception and fault degradation."""

from .fusion_tracker import (
    FusedObject,
    FusionResult,
    FusionTracker,
    FusionTrackerConfig,
    Observation,
)
from .rgb_pipeline import RGBDetection, RGBPipeline, RGBPipelineConfig, RGBTrack
from .sensor_adapter import (
    AlignedSensorFrame,
    Extrinsics,
    Modality,
    SensorRecorder,
    SensorReplayer,
    SensorSample,
    SensorSynchronizer,
)

__all__ = [
    "AlignedSensorFrame",
    "Extrinsics",
    "FusedObject",
    "FusionResult",
    "FusionTracker",
    "FusionTrackerConfig",
    "Modality",
    "Observation",
    "RGBDetection",
    "RGBPipeline",
    "RGBPipelineConfig",
    "RGBTrack",
    "SensorRecorder",
    "SensorReplayer",
    "SensorSample",
    "SensorSynchronizer",
]
