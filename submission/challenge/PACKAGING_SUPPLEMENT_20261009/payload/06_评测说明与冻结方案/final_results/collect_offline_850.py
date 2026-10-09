"""New CPU replay of all frozen 850 requests; never claims historical same-run.

Run variants as separate processes. No CARLA, ASR, network or gate signing.
Preflight is standard-library only. Actual execution requires numpy, torch,
Pillow, jsonschema and onnxruntime. Outputs only inside this script's directory.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
COHORTS = ('d2_v1_1_val', 'd3_wave2_safe_short_v1_val', 'd3_targeted_gap_strict_v1_val', 'd3_turn_gap_60_strict_v1_val', 'd3_gap300_strict_v1_val', 'b1_ms34_supplement_v1_val')
MODEL = {
    'fp32': ('03_训练与模型/A2模型与量化/models/student_v0_fp32_candidate.onnx', '681a5d4bf16ba61741ef0e559649c43c041de649eef3e8e6f0b6285beaab4286'),
    'full_int8': ('03_训练与模型/A2模型与量化/models/full_int8/student_int8.onnx', '275dce5c426fff85a0375eb286fc67febac8d835c1e36fe15b0fbd707cf836c3'),
}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package-root', type=Path, default=HERE.parents[1])
    p.add_argument('--variant', choices=MODEL, required=True)
    p.add_argument('--preflight-only', action='store_true')
    p.add_argument('--ort-threads', type=int, default=1)
    p.add_argument('--dependency-root', type=Path, help='Optional workspace vendor directory inserted before global site-packages')
    a = p.parse_args()
    if a.ort_threads < 1: p.error('--ort-threads must be positive')
    package = a.package_root.resolve(); source = package/'02_源码与部署/source'
    model = package/MODEL[a.variant][0]
    bindings = {}
    def bind(path):
        entry = {'path': str(path.relative_to(package)), 'sha256': sha(path), 'bytes': path.stat().st_size}
        bindings[entry['path']] = entry; return entry
    model_identity = bind(model)
    if model_identity['sha256'] != MODEL[a.variant][1]: p.error('Unexpected model hash; no inference executed')
    cases = []
    count_by_cohort = {}
    for cohort in COHORTS:
        root = source/'challenge/hil/frozen'/cohort
        f = root/'cases.jsonl'; bind(f)
        rows = [json.loads(l) for l in f.read_text(encoding='utf-8-sig').splitlines() if l.strip()]
        count_by_cohort[cohort] = len(rows)
        for row in rows:
            rgb = (root/row['rgb_path']).resolve()
            if not rgb.is_relative_to(root.resolve()): p.error('Frozen rgb path escapes cohort')
            rgb_identity = bind(rgb)
            if rgb_identity['sha256'] != row['rgb_sha256']: p.error('RGB hash mismatch: '+row['case_id'])
            cases.append((cohort, row, rgb, rgb_identity))
    if len(cases) != 850: p.error('Expected exactly 850 frozen records')
    if len({(cohort, row['case_id']) for cohort, row, _, _ in cases}) != 850: p.error('Duplicate cohort/case key')
    for rel in ['challenge/student/preprocess.py', 'challenge/student/contract.py', 'challenge/planner/student_adapter.py', 'runtime/interface_registry.py', 'interfaces/model_request.schema.json', 'interfaces/maneuver_plan.schema.json']:
        bind(source/rel)
    bind(Path(__file__))
    preflight = {'variant': a.variant, 'cases': len(cases), 'cohorts': count_by_cohort, 'missing_rgb': 0, 'rgb_hash_mismatches': 0, 'model': model_identity, 'scope': 'New CPU replay inputs only; historical B3 not reproduced and not a formal B2 gate.'}
    if a.preflight_only:
        write_json(HERE/('offline850_preflight_'+a.variant+'.json'), {**preflight, 'source_bindings': bindings})
        print(json.dumps(preflight, ensure_ascii=False)); return 0
    if a.dependency_root:
        dependency_root = a.dependency_root.resolve()
        if not dependency_root.is_dir(): p.error('Dependency root missing')
        sys.path.insert(0, str(dependency_root))
    sys.path.insert(0, str(source))
    import numpy as np
    import torch
    import onnxruntime as ort
    from challenge.student.preprocess import StudentPreprocessor
    from challenge.planner.student_adapter import StudentPlanAdapter
    from runtime.interface_registry import InterfaceRegistry
    torch.set_num_threads(1)
    options = ort.SessionOptions(); options.intra_op_num_threads = a.ort_threads; options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(model), sess_options=options, providers=['CPUExecutionProvider'])
    if 'CPUExecutionProvider' not in session.get_providers(): raise RuntimeError('CPU provider unavailable')
    input_names = [i.name for i in session.get_inputs()]
    expected_inputs = ['rgb', 'text_tokens', 'targets', 'state']
    if set(input_names) != set(expected_inputs): raise RuntimeError('Model input contract differs')
    outputs = [o.name for o in session.get_outputs()]
    preprocessor = StudentPreprocessor(); adapter = StudentPlanAdapter(model_id='student-v0-r3-fp32')
    registry = InterfaceRegistry(); registry.warm(('model_request', 'maneuver_plan'))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    out = HERE/('offline850_new_cpu_'+a.variant+'_'+stamp); out.mkdir()
    versions = {}
    for name in ['numpy', 'torch', 'Pillow', 'jsonschema', 'onnxruntime']:
        try: versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: versions[name] = 'unknown'
    manifest = {**preflight, 'run_id': out.name, 'status': 'RUNNING', 'started_utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version, 'platform': platform.platform(), 'packages': versions, 'providers': session.get_providers(), 'ort_threads': a.ort_threads, 'loaded_module_paths': {'numpy': np.__file__, 'torch': torch.__file__, 'onnxruntime': ort.__file__},
        'source_bindings': bindings, 'new_replay': True, 'historical_same_run': False, 'asr_executed': False, 'carla_executed': False, 'formal_b2_gate': False,
        'annotation_origin': 'Existing frozen Teacher plans; Teacher is not rerun. All labels were already exposed.',
        'request_mutation': 'Only rgb_ref is remapped to hash-verified frozen RGB path; source text, scene and other request fields remain unchanged.'}
    write_json(out/'run_manifest.json', manifest)
    success = failed = 0
    started = time.perf_counter()
    try:
        with (out/'student_predictions.jsonl').open('x', encoding='utf-8') as pred, (out/'raw_outputs.jsonl').open('x', encoding='utf-8') as rawfile, (out/'teacher_reference_predictions.jsonl').open('x', encoding='utf-8') as teacher:
            for n, (cohort, row, rgb, rgb_identity) in enumerate(cases, 1):
                request = dict(row['request']); request['rgb_ref'] = str(rgb)
                identity = {'cohort': cohort, 'case_id': row['case_id'], 'sample_id': row['sample_id'], 'request_id': request.get('request_id'), 'command_id': request.get('command_id')}
                teacher.write(json.dumps({**identity, 'record_type': 'stored_teacher_reference_for_new_replay', 'prediction': row['teacher_plan']}, ensure_ascii=False, allow_nan=False)+'\n')
                record = {**identity, 'record_type': 'new_cpu_offline_student_prediction', 'variant': a.variant, 'rgb_sha256': rgb_identity['sha256']}
                try:
                    request = registry.validate('model_request', request)
                    tensors = preprocessor(request)
                    feed = {key: t.numpy() for key, t in zip(expected_inputs, tensors.as_tuple(), strict=True)}
                    before = time.perf_counter_ns(); raw = session.run(outputs, feed); inference_ms = (time.perf_counter_ns()-before)/1e6
                    if not all(np.isfinite(v).all() for v in raw): raise ValueError('Non-finite raw model output')
                    rawfile.write(json.dumps({**identity, 'inference_ms': inference_ms, 'raw_outputs': {k: v.tolist() for k, v in zip(outputs, raw, strict=True)}}, ensure_ascii=False, allow_nan=False)+'\n')
                    plan = adapter.decode(request, {k: torch.from_numpy(v) for k, v in zip(outputs, raw, strict=True)})
                    plan = registry.validate('maneuver_plan', plan)
                    if plan['request_id'] != request['request_id'] or plan['command_id'] != request['command_id']: raise ValueError('Plan/request identity mismatch')
                    record.update({'status': 'SUCCESS', 'prediction': plan, 'error': None, 'inference_ms': inference_ms}); success += 1
                except Exception as error:
                    record.update({'status': 'INFERENCE_ERROR', 'prediction': None, 'error': {'type': type(error).__name__, 'message': str(error)}}); failed += 1
                pred.write(json.dumps(record, ensure_ascii=False, allow_nan=False)+'\n')
                if n % 50 == 0:
                    pred.flush(); rawfile.flush(); teacher.flush(); print(f'{a.variant}: {n}/850, success={success}, failed={failed}', flush=True)
        manifest['status'] = 'COMPLETED' if failed == 0 else 'COMPLETED_WITH_ERRORS'
    except BaseException as error:
        manifest['status'] = 'INTERRUPTED'; manifest['interruption'] = repr(error); raise
    finally:
        manifest.update({'success_count': success, 'error_count': failed, 'elapsed_wall_s': time.perf_counter()-started, 'finished_utc': datetime.now(timezone.utc).isoformat()})
        manifest['output_bindings'] = {f.name: {'sha256': sha(f), 'bytes': f.stat().st_size} for f in out.glob('*.jsonl')}
        write_json(out/'run_manifest.json', manifest)
    print(str(out)); return 0 if failed == 0 else 2

if __name__ == '__main__': raise SystemExit(main())
