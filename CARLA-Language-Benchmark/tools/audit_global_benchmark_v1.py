#!/usr/bin/env python3
"""Compatibility entry point for the repository-wide benchmark audit."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.benchmark_audit import audit_dataset, main


if __name__ == "__main__":
    raise SystemExit(main())
