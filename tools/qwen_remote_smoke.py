from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from integration.qwen_boundary import QwenInputContext
from integration.qwen_remote_backend import OpenAICompatibleQwenVLBackend
from integration.qwen_vl_adapter import StrictQwenVLAdapter


def main() -> None:
    image_path = Path(
        os.environ.get(
            "QWEN_TEST_IMAGE",
            "artifacts/runtime/qwen_test.jpg",
        )
    ).resolve()

    backend = OpenAICompatibleQwenVLBackend(
        base_url=os.environ.get(
            "QWEN_BASE_URL",
            "http://127.0.0.1:8000/v1",
        ),
        api_key=os.environ.get("QWEN_API_KEY", "unused"),
        model=os.environ.get("QWEN_MODEL", "Qwen/Qwen3.5-2B"),
        timeout_s=10.0,
    )

    adapter = StrictQwenVLAdapter(
        backend,
        image_root=image_path.parent,
    )

    context = QwenInputContext(
        request_id="remote-smoke-001",
        frame=0,
        sim_time_s=0.0,
        voice_command="前方道路安全时，将速度设置为每秒五米",
        rgb_ref=image_path.name,
        scene_state={
            "speed_mps": 0.0,
            "behavior_state": "STOPPED",
            "route_progress": 0.0,
        },
        perception={
            "lead_vehicle": None,
            "traffic_light": "GREEN",
            "minimum_obstacle_distance_m": 20.0,
            "visual_valid": True,
        },
        safety_state={
            "collision": False,
            "minimum_ttc_s": 99.0,
            "route_deviation": False,
        },
    )

    decision = adapter.infer(context)
    print("validated decision:")
    print(decision)

    trace = adapter.last_trace
    if trace is not None:
        print(f"latency_ms={trace.latency_ms:.2f}")
        print(f"raw_output={trace.raw_output}")


if __name__ == "__main__":
    main()
