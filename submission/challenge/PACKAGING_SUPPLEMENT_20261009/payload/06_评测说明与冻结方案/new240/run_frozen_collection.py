"""Optional real CARLA/Teacher collection; never issues a benchmark or Gate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[1]
SOURCE = PACKAGE / '02_源码与部署' / 'source'
FREEZE = HERE / 'freeze'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list-only', action='store_true')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=2000)
    parser.add_argument('--teacher-url', help='Teacher v4 ModelRequest -> ManeuverPlan service base URL')
    parser.add_argument('--teacher-identity', type=Path, help='Existing genuine service identity JSON, with frozen collection_requirements identity keys')
    parser.add_argument('--output-dir', type=Path, default=HERE / 'collection_runs' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    parser.add_argument('--realtime', action='store_true')
    parser.add_argument('--follow-spectator', action='store_true')
    args = parser.parse_args()
    lock = json.loads((FREEZE / 'FREEZE_LOCK.json').read_text(encoding='utf-8'))
    for name, key in [('acquisition_slots.jsonl', 'acquisition_slots_sha256'), ('policy_manifest.json', 'policy_manifest_sha256')]:
        if digest(FREEZE / name) != lock[key]:
            raise SystemExit(f'Frozen file hash mismatch: {name}')
    slots = [json.loads(line) for line in (FREEZE / 'acquisition_slots.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    if len(slots) != lock['slot_count']:
        raise SystemExit('Frozen slot count mismatch')
    for slot in slots:
        scenario = (FREEZE / slot['scenario_path']).resolve()
        if not scenario.is_relative_to(FREEZE.resolve()) or digest(scenario) != slot['scenario_sha256']:
            raise SystemExit(f"Frozen scenario mismatch: {slot['slot_id']}")
    if args.list_only:
        for slot in slots:
            print(slot['slot_id'], slot['cohort'], slot['scenario_id'], slot['seed'], slot['command_ordinal'])
        print(f'{len(slots)} frozen slots; no collection, no model inference, no output files created.')
        return
    url = urlparse(args.teacher_url or '')
    if url.scheme not in ('http', 'https') or not url.netloc or '/v1' in url.path:
        raise SystemExit('Supply a Teacher v4 planner service base URL, not raw vLLM /v1.')
    if not args.teacher_identity:
        raise SystemExit('Supply genuine existing Teacher identity evidence via --teacher-identity; this tool does not manufacture identity metadata.')
    identity = json.loads(args.teacher_identity.read_text(encoding='utf-8'))
    requirements = lock['collection_requirements']
    for key in ('teacher_git_sha', 'teacher_model_id', 'teacher_model_revision', 'teacher_profile', 'teacher_artifact_fingerprint_sha256'):
        if identity.get(key) != requirements[key]:
            raise SystemExit(f'Teacher identity evidence mismatch: {key}')
    output = args.output_dir.resolve()
    if not output.is_relative_to(HERE) or output == HERE or output.is_relative_to(FREEZE):
        raise SystemExit('Output must be a new child directory of new240, outside freeze.')
    output.mkdir(parents=True, exist_ok=False)
    save(output / 'collection_context.json', {'status': 'COLLECTION_STARTED_NOT_A_BENCHMARK', 'freeze_id': lock['freeze_id'], 'teacher_url': args.teacher_url, 'teacher_identity_evidence_path': str(args.teacher_identity.resolve()), 'teacher_identity_evidence_sha256': digest(args.teacher_identity), 'identity_note': 'Provided evidence matched frozen requirements; not an independent attestation of the running endpoint.', 'policy_sha256': digest(FREEZE / 'policy_manifest.json')})
    logs = []
    records = []
    for slot in slots:
        slot_dir = output / ('slot_' + slot['slot_id'])
        slot_dir.mkdir()
        log_dir = slot_dir / 'logs'
        command = [sys.executable, '-m', 'integration.carla_runner', '--host', args.host, '--port', str(args.port), '--scenario-file', str((FREEZE / slot['scenario_path']).resolve()), '--seed', str(slot['seed']), '--qwen-service-url', args.teacher_url.rstrip('/'), '--qwen-mode', 'planner_v2', '--log-dir', str(log_dir)]
        if args.realtime:
            command.append('--realtime')
        if args.follow_spectator:
            command.append('--follow-spectator')
        record = {'slot': slot, 'command': command, 'cwd': str(SOURCE), 'started_utc': datetime.now(timezone.utc).isoformat()}
        save(slot_dir / 'command.json', record)
        with (slot_dir / 'console.log').open('w', encoding='utf-8') as console:
            result = subprocess.run(command, cwd=SOURCE, stdout=console, stderr=subprocess.STDOUT, check=False)
        record.update(exit_code=result.returncode, ended_utc=datetime.now(timezone.utc).isoformat(), logs=[str(p) for p in sorted(log_dir.glob('*.jsonl'))])
        save(slot_dir / 'result.json', record)
        records.append(record)
        logs.extend(record['logs'])
        save(output / 'execution_ledger.json', records)
        if result.returncode != 0:
            print(f"Slot {slot['slot_id']} exited {result.returncode}; recorded, no automatic retry.", flush=True)
    if not logs:
        raise SystemExit('No actual JSONL logs; no dataset created. Inspect execution_ledger.json.')
    collect = [sys.executable, '-m', 'challenge.dataset.collector', '--repo-root', str(SOURCE), '--output', str(output / 'collector_accepted_raw.jsonl'), '--rejected-output', str(output / 'collector_rejected.jsonl'), '--dataset-version', lock['freeze_id'] + '_raw_collection']
    for path in logs:
        collect.extend(['--input-log', path])
    save(output / 'collector_command.json', {'command': collect, 'cwd': str(SOURCE)})
    with (output / 'collector_console.log').open('w', encoding='utf-8') as console:
        result = subprocess.run(collect, cwd=SOURCE, stdout=console, stderr=subprocess.STDOUT, check=False)
    save(output / 'collection_status.json', {'status': 'RAW_COLLECTION_REQUIRES_QUALITY_IDENTITY_SLOT_AND_LEAKAGE_PREFLIGHT', 'collector_exit_code': result.returncode, 'executed_slots': len(records), 'failed_runner_slots': [r['slot']['slot_id'] for r in records if r['exit_code'] != 0], 'formal_gate_decision': False})
    print(f'Raw collection recorded at {output}; collector exit {result.returncode}. No frozen case set or Gate issued.')
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
