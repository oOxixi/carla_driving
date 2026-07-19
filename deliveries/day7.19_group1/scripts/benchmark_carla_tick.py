from __future__ import annotations

import argparse
import statistics
import time

import carla


def percentile(values, q):
    values = sorted(values)
    index = (len(values) - 1) * q
    lo = int(index)
    hi = min(lo + 1, len(values) - 1)
    alpha = index - lo
    return values[lo] * (1 - alpha) + values[hi] * alpha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--frames", type=int, default=30)
    args = parser.parse_args()

    client = carla.Client(args.host, args.port)
    client.set_timeout(60.0)

    world = client.get_world()
    original = world.get_settings()

    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.05
        settings.no_rendering_mode = False
        world.apply_settings(settings)

        durations = []

        for index in range(args.frames):
            start = time.monotonic()
            frame = world.tick()
            elapsed_ms = (time.monotonic() - start) * 1000
            durations.append(elapsed_ms)

            print(
                f"{index:03d} frame={frame} "
                f"world_tick={elapsed_ms:.2f} ms"
            )

        print("\n=== world.tick benchmark ===")
        print(f"frames: {len(durations)}")
        print(f"mean: {statistics.mean(durations):.2f} ms")
        print(f"median: {statistics.median(durations):.2f} ms")
        print(f"p95: {percentile(durations, 0.95):.2f} ms")
        print(f"max: {max(durations):.2f} ms")

    finally:
        world.apply_settings(original)


if __name__ == "__main__":
    main()
