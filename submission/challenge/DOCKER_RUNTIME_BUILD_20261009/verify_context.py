#!/usr/bin/env python3
"""Stop if the deliberately public runtime context accidentally contains weights."""
import json
from pathlib import Path
import sys

MODEL_SUFFIXES = {'.onnx', '.pt', '.pth', '.safetensors', '.hbm', '.bc', '.bin', '.ckpt'}
FORBIDDEN = MODEL_SUFFIXES | {'.tar', '.zip',
             '.gz', '.mp3', '.wav', '.mp4', '.f32', '.npy', '.npz', '.pkl'}


def main():
    root = Path(sys.argv[1]).resolve()
    files = [path for path in root.rglob('*') if path.is_file()]
    disallowed = [str(path.relative_to(root)) for path in files
                  if path.suffix.lower() in FORBIDDEN or path.is_symlink()]
    total = sum(path.stat().st_size for path in files)
    missing = [name for name in ('source', 'scripts/launch_student.py',
               'scripts/check_deployment.py', 'docker/verify_runtime.py',
               'docker/requirements-runtime-lock.txt', 'Dockerfile.stage')
               if not (root / name).exists()]
    errors = []
    if disallowed:
        errors.append('Forbidden binary/model/media/archive or symlink: ' + ', '.join(disallowed))
    if total > 100 * 1024 * 1024:
        errors.append('Public runtime context exceeds 100 MiB')
    if missing:
        errors.append('Missing context files: ' + ', '.join(missing))
    print(json.dumps({'status': 'FAIL' if errors else 'PASS',
        'context_file_count': len(files), 'context_bytes': total,
        'private_model_files_included': any(path.suffix.lower() in MODEL_SUFFIXES for path in files),
        'errors': errors}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
