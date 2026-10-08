"""Install code/document supplements over an existing full submission directory."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys


HERE = Path(__file__).resolve().parent
PAYLOAD = HERE / 'payload'
CACHE_NAMES = {'__pycache__', 'node_modules', 'cache', 'caches'}
INDEX_PATHS = {'99_交付清单/PACKAGE_MANIFEST.json', '99_交付清单/FILE_INDEX.csv', '99_交付清单/SHA256SUMS.txt'}


def hash_file(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else hash_legacy(handle)


def hash_legacy(handle):
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b''):
        digest.update(chunk)
    return digest.hexdigest()


def hidden(path):
    return path.name.startswith('.') or bool(getattr(path.stat(follow_symlinks=False), 'st_file_attributes', 0) & 2)


def payload_files():
    if not PAYLOAD.is_dir():
        raise ValueError('Missing payload directory')
    files = []
    for current, dirs, names in os.walk(PAYLOAD, followlinks=False):
        base = Path(current)
        kept = []
        for name in sorted(dirs):
            path = base / name
            if hidden(path) or name.lower() in CACHE_NAMES:
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(PAYLOAD.resolve()):
                raise ValueError(f'Unsafe payload directory: {path}')
            kept.append(name)
        dirs[:] = kept
        for name in sorted(names):
            path = base / name
            root_dockerignore = path.relative_to(PAYLOAD).as_posix() == '.dockerignore'
            if (hidden(path) and not root_dockerignore) or path.suffix.lower() in {'.pyc', '.pyo'}:
                continue
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(PAYLOAD.resolve()):
                raise ValueError(f'Unsafe payload file: {path}')
            files.append(path)
    if not files:
        raise ValueError('No eligible payload files')
    return sorted(files)


def load_manifest(root):
    for relative in INDEX_PATHS:
        path = root / relative
        if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file():
            raise ValueError(f'Existing regular index file required: {relative}')
    manifest = json.loads((root / '99_交付清单/PACKAGE_MANIFEST.json').read_text(encoding='utf-8-sig'))
    files = manifest.get('files')
    if not isinstance(files, list) or not all(isinstance(record, dict) and isinstance(record.get('path'), str) and isinstance(record.get('bytes'), int) and isinstance(record.get('sha256'), str) for record in files):
        raise ValueError('Unsupported manifest files schema; manual index refresh is required')
    if not INDEX_PATHS.issubset(set(manifest.get('self_exclusions', []))):
        raise ValueError('Unsupported manifest self-exclusions; manual index refresh is required')
    return manifest


def refresh_indexes(root, manifest, actions):
    records = {record['path']: dict(record) for record in manifest['files']}
    updated = []
    for _, destination, relative, _ in actions:
        name = relative.as_posix()
        if name in INDEX_PATHS:
            raise ValueError('Payload must not include generated indexes')
        records[name] = {**records.get(name, {}), 'path': name, 'bytes': destination.stat().st_size, 'sha256': hash_file(destination)}
        updated.append(name)
    for name in manifest['self_exclusions']:
        records.pop(name, None)
    files = [records[name] for name in sorted(records)]
    manifest['files'] = files
    manifest['overlay_index_refresh'] = {'updated_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'payload files only; existing unmodified records preserved without rehash', 'payload_paths': updated, 'final_delivery_declared': False}
    index_dir = root / '99_交付清单'
    (index_dir / 'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (index_dir / 'FILE_INDEX.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['path', 'bytes', 'sha256'], lineterminator='\n', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(files)
    (index_dir / 'SHA256SUMS.txt').write_text(''.join(f"{record['sha256']}  {record['path']}\n" for record in files), encoding='utf-8')
    print(f'INDEX_REFRESH: {len(updated)} payload records updated; unmodified package files not rehashed.')


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-root', required=True, type=Path, help='Existing complete material directory, not the GitHub checkout')
    parser.add_argument('--dry-run', action='store_true', help='List ADD/OVERWRITE/UNCHANGED actions without modifying files')
    args = parser.parse_args()
    root = args.package_root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Package root must already exist as a directory')
    for rel in ('01_技术报告', '02_源码与部署/source', '03_训练与模型', '06_评测说明与冻结方案'):
        directory = (root / rel).resolve()
        if not directory.is_relative_to(root) or not directory.is_dir():
            raise ValueError(f'Existing complete package directory is required: {rel}')
    if root == HERE or root.is_relative_to(HERE) or HERE.is_relative_to(root):
        raise ValueError('Package root must be separate from this GitHub supplement directory')
    manifest = load_manifest(root)
    actions = []
    for source in payload_files():
        relative = source.relative_to(PAYLOAD)
        if relative.as_posix() in INDEX_PATHS:
            raise ValueError('Payload must not include generated indexes')
        destination = root / relative
        resolved = destination.resolve()
        if not resolved.is_relative_to(root) or destination.is_symlink():
            raise ValueError(f'Target escapes package root or is a symlink: {relative}')
        if destination.exists() and not destination.is_file():
            raise ValueError(f'Target is not a regular file: {relative}')
        status = 'ADD'
        if destination.exists():
            status = 'UNCHANGED' if hash_file(source) == hash_file(destination) else 'OVERWRITE'
        actions.append((source, destination, relative, status))
    # Complete all path checks and show every overwrite before any mutation.
    for _, _, relative, status in actions:
        print(f'{status}\t{relative.as_posix()}')
    if args.dry_run:
        print('INDEX_REFRESH_PLANNED\t99_交付清单/PACKAGE_MANIFEST.json, FILE_INDEX.csv, SHA256SUMS.txt (payload records only)')
        print(f'DRY_RUN: {len(actions)} files inspected; no files changed.')
        return
    changed = 0
    for source, destination, relative, status in actions:
        if status == 'UNCHANGED':
            if os.name != 'nt' and destination.suffix == '.sh':
                destination.chmod(destination.stat().st_mode | stat.S_IXUSR)
            continue
        # Recheck containment before each write; never remove directories/files.
        if not destination.resolve().is_relative_to(root):
            raise ValueError(f'Target changed outside package root: {relative}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        if os.name != 'nt' and destination.suffix == '.sh':
            destination.chmod(destination.stat().st_mode | stat.S_IXUSR)
        if hash_file(source) != hash_file(destination):
            raise ValueError(f'Copied file hash mismatch: {relative}')
        changed += 1
    refresh_indexes(root, manifest, actions)
    print(f'INSTALLED: {changed} changed files; {len(actions) - changed} unchanged. No ZIP generated.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
