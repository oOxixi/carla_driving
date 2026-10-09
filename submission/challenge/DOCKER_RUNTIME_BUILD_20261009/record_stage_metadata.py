#!/usr/bin/env python3
"""Record observed Docker stage identities and streamed archive hashes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex

GIB = 1024 ** 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-image-bytes', type=int, default=20 * GIB)
    parser.add_argument('--before-save', action='store_true')
    args = parser.parse_args()
    out = args.output
    image = json.loads((out / 'image_inspect.json').read_text())[0]
    base = json.loads((out / 'base_image_inspect.json').read_text())[0]
    registry = json.loads((out / 'registry_metadata.json').read_text())
    runtime = json.loads((out / 'runtime_dependencies.json').read_text())
    base_runtime = json.loads((out / 'base_runtime.json').read_text())
    base_os = {}
    for line in (out / 'base_os_release.txt').read_text().splitlines():
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values = shlex.split(value)
        base_os[key] = values[0] if len(values) == 1 else value
    if image.get('Architecture') != 'amd64' or image.get('Os') != 'linux':
        raise RuntimeError('Runtime stage is not Linux amd64')
    size = image['Size']
    if size > args.max_image_bytes:
        raise RuntimeError(f'Observed image size {size} exceeds configured export limit {args.max_image_bytes}')
    metadata = {
        'status': 'RUNTIME_STAGE_VERIFIED_PENDING_EXPORT',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_commit': os.environ.get('GITHUB_SHA'),
        'run_id': os.environ.get('GITHUB_RUN_ID'),
        'run_url': 'https://github.com/' + os.environ.get('GITHUB_REPOSITORY', '') + '/actions/runs/' + os.environ.get('GITHUB_RUN_ID', ''),
        'image_ref': os.environ.get('STAGE_IMAGE'), 'image_id': image['Id'],
        'repo_digests': image.get('RepoDigests') or [],
        'base_ref': registry['base_tag'], 'resolved_base': registry['resolved_base'],
        'base_kind': registry['base_kind'], 'official_base_ref': registry['official_base_ref'],
        'official_base_access': registry['official_base_access'],
        'official_environment_equivalent_candidate': registry['official_environment_equivalent_candidate'],
        'official_environment_equivalent': registry['official_environment_equivalent'],
        'official_equivalence_status': registry['official_equivalence_status'],
        'actual_base_os': base_os, 'actual_base_runtime': base_runtime,
        'actual_runtime_python': runtime['python'],
        'actual_runtime_versions': runtime['packages'],
        'base_image_id': base['Id'], 'base_repo_digests': base.get('RepoDigests') or [],
        'image_size_bytes_observed': size,
        'image_rootfs_diff_ids': image.get('RootFS', {}).get('Layers', []),
        'private_model_files_included': False,
        'runtime_dependency_check_run': True, 'runtime_import_check_run': True,
        'model_inference_run': False, 'final_student_image_built': False,
        'local_windows_docker_load_performed': False,
        'registry_published': False,
    }
    if args.before_save:
        required = min(size + GIB, int(registry['compressed_layers_bytes'] * 1.5) + 2 * GIB)
        available = shutil.disk_usage(out).free
        metadata.update(archive_free_bytes_before_save=available,
            archive_free_guard_bytes=required,
            archive_guard_kind='conservative gzip output estimate; not observed archive size')
        (out / 'stage_image_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
        if available < required:
            raise RuntimeError('Insufficient free disk for the compressed stage export guard')
        return
    archive = out / 'runtime-stage-image.tar.gz'
    if not archive.is_file() or archive.stat().st_size == 0:
        raise RuntimeError('Docker stage archive is missing or empty')
    digest = hashlib.sha256()
    with archive.open('rb') as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    metadata.update(status='RUNTIME_STAGE_BUILT_VERIFIED_EXPORTED_WITHOUT_PRIVATE_MODELS',
        archive_file=archive.name, archive_bytes=archive.stat().st_size,
        archive_sha256=digest.hexdigest(), archive_compression='gzip -1; Docker save stream')
    (out / 'stage_image_manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (out / 'archive_sha256.txt').write_text(digest.hexdigest() + '  ' + archive.name + '\n')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
