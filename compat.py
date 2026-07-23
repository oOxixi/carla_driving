"""Small runtime compatibility helpers for the local validation environment."""

from __future__ import annotations

from enum import Enum

try:
    from enum import StrEnum
except ImportError:  # Python 3.10 CARLA wheel compatibility.
    class StrEnum(str, Enum):
        pass

