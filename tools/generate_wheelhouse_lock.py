"""Turn one pip --report result into a strict wheelhouse manifest and hash lock."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlparse


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--requirements-lock", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    root = args.wheelhouse.resolve()
    wheels = sorted(path for path in root.iterdir() if path.is_file() and path.suffix == ".whl")
    files = [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in wheels]
    by_name = {item["path"]: item for item in files}
    resolved = []
    for item in report["install"]:
        metadata = item["metadata"]
        filename = Path(unquote(urlparse(item["download_info"]["url"]).path)).name
        wheel = by_name.get(filename)
        if wheel is None:
            raise ValueError(f"report wheel is absent from wheelhouse: {filename}")
        resolved.append({"name": metadata["name"], "version": metadata["version"], **wheel})
    if len({item["name"].lower() for item in resolved}) != len(resolved):
        raise ValueError("resolver selected duplicate project names")
    args.lock.write_text(json.dumps({"files": files, "resolved": resolved}, indent=2) + "\n", encoding="utf-8")
    args.requirements_lock.write_text("\n".join(
        f"{item['name']}=={item['version']} --hash=sha256:{item['sha256']}" for item in resolved
    ) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
