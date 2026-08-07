"""Allocate fresh, private Qwen launch logs without reusing prior evidence."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from uuid import UUID, uuid4


def create_launch_logs(output_root: Path, launch_id: UUID | None = None) -> str:
    """Create this launch's raw/evidence/runtime files exclusively and return its UUID."""
    output_root.mkdir(parents=True, exist_ok=True)
    identifier = str(launch_id or uuid4())
    paths = [
        output_root / f"qwen-evidence-{identifier}.log",
        output_root / f"qwen-vllm-{identifier}.log",
        output_root / f"qwen-runtime-{identifier}.json",
    ]
    created: list[Path] = []
    try:
        for path in paths:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
            created.append(path)
    except FileExistsError as exc:
        for path in created:
            path.unlink(missing_ok=True)
        raise ValueError(f"Qwen launch log collision: {exc.filename}") from exc
    return identifier


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(create_launch_logs(args.output_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
