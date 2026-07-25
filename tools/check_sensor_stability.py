"""CLI entry point for the current-world CARLA sensor stability probe."""
from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from integration.sensor_stability import main


if __name__ == "__main__":
    raise SystemExit(main())
