"""成员 A 的 CARLA 运行时边界包及其面向 C 的共享契约。"""

from .contracts import (
    CONTRACT_VERSION,
    ControlOutput,
    DrivingCommand,
    ExecutionFeedback,
    ExecutionStatus,
    LongitudinalOutput,
    LongitudinalRequest,
    RiskMetrics,
    RuntimeVehicleState,
    SignalState,
    TrafficConstraint,
)
from .high_level_command import HighLevelCommandAdapter, is_high_level_command
from .simulator import ActorRegistry, CarlaSession, SensorFrameBuffer, SynchronousWorld

__all__ = [
    "CONTRACT_VERSION", "SignalState", "RuntimeVehicleState", "DrivingCommand", "TrafficConstraint",
    "LongitudinalRequest", "ControlOutput", "RiskMetrics", "LongitudinalOutput",
    "ExecutionStatus", "ExecutionFeedback",
    "HighLevelCommandAdapter", "is_high_level_command",
    "ActorRegistry", "CarlaSession", "SensorFrameBuffer", "SynchronousWorld",
]
