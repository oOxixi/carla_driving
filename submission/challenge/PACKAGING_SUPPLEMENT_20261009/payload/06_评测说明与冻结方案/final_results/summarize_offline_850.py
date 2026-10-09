"""Summarize two genuinely executed new CPU replays from saved records only."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def ratio(n, d): return {'numerator': n, 'denominator': d, 'value': n/d if d else None}
def key(r): return (r['cohort'], r['case_id'])
def load_rows(p):
    rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
    data = {key(r): r for r in rows}
    if len(data) != len(rows): raise ValueError('Duplicate cohort/case record')
    return data
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def signature(s):
    return (s.get('behavior'), s.get('completion', {}).get('type'), s.get('target', {}).get('target_lane'), s.get('target', {}).get('target_id'))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fp32-dir', type=Path, required=True)
    p.add_argument('--int8-dir', type=Path, required=True)
    a = p.parse_args()
    directories = {'FP32': a.fp32_dir.resolve(), 'INT8': a.int8_dir.resolve()}
    records = {}; teachers = {}; manifests = {}; source = {}
    for model, folder in directories.items():
        if not folder.is_relative_to(HERE): p.error('Replay folder must be inside final_results')
        manifests[model] = json.loads((folder/'run_manifest.json').read_text(encoding='utf-8'))
        if manifests[model]['status'] not in ('COMPLETED', 'COMPLETED_WITH_ERRORS'): p.error('Replay not complete: '+model)
        records[model] = load_rows(folder/'student_predictions.jsonl')
        teachers[model] = load_rows(folder/'teacher_reference_predictions.jsonl')
        if len(records[model]) != 850 or set(records[model]) != set(teachers[model]): p.error('Replay coverage differs')
        for f in folder.glob('*.json*'): source[str(f.relative_to(HERE))] = {'sha256': sha(f), 'bytes': f.stat().st_size}
    if set(records['FP32']) != set(records['INT8']): p.error('Variant case identities differ')
    if teachers['FP32'] != teachers['INT8']: p.error('Variant Teacher references differ')
    results = {}; all_details = []
    for model, data in records.items():
        c = {name: 0 for name in ['cases', 'success', 'errors', 'teacher_steps', 'student_steps', 'step_count_equal', 'semantic_plan_equal', 'behavior_sequence_equal', 'behavior_equal', 'completion_equal', 'lane_equal', 'target_equal', 'target_present', 'target_present_equal', 'speed_teacher_present', 'speed_both_present', 'speed_missing', 'speed_hits']}
        deltas = []
        for k, row in data.items():
            reference = teachers[model][k]['prediction']['steps']
            success = row['status'] == 'SUCCESS'
            predicted = row['prediction']['steps'] if success else []
            c['cases'] += 1; c['success'] += success; c['errors'] += not success
            c['teacher_steps'] += len(reference); c['student_steps'] += len(predicted)
            c['step_count_equal'] += success and len(reference) == len(predicted)
            c['semantic_plan_equal'] += success and [signature(s) for s in reference] == [signature(s) for s in predicted]
            c['behavior_sequence_equal'] += success and [s.get('behavior') for s in reference] == [s.get('behavior') for s in predicted]
            disagreements = []
            for i, t in enumerate(reference):
                s = predicted[i] if i < len(predicted) else {}
                present = i < len(predicted)
                for name, tv, sv in [('behavior', t.get('behavior'), s.get('behavior')), ('completion', t.get('completion', {}).get('type'), s.get('completion', {}).get('type')), ('lane', t.get('target', {}).get('target_lane'), s.get('target', {}).get('target_lane')), ('target', t.get('target', {}).get('target_id'), s.get('target', {}).get('target_id'))]:
                    match = present and tv == sv
                    c[name+'_equal'] += match
                    if not match: disagreements.append({'step': i+1, 'field': name, 'teacher': tv, 'student': sv})
                ti = t.get('target', {}).get('target_id'); si = s.get('target', {}).get('target_id')
                if ti is not None: c['target_present'] += 1; c['target_present_equal'] += present and ti == si
                ts = t.get('target', {}).get('target_speed_mps'); ss = s.get('target', {}).get('target_speed_mps')
                if isinstance(ts, (int, float)):
                    c['speed_teacher_present'] += 1
                    if present and isinstance(ss, (int, float)):
                        delta = abs(ts-ss); deltas.append(delta); c['speed_both_present'] += 1; c['speed_hits'] += delta <= .5
                    else: c['speed_missing'] += 1
            if disagreements or len(reference) != len(predicted): all_details.append({'model': model, 'cohort': k[0], 'case_id': k[1], 'sample_id': row['sample_id'], 'teacher_steps': len(reference), 'student_steps': len(predicted), 'disagreements': disagreements, 'error': row.get('error')})
        metrics = {'prediction_success': ratio(c['success'], c['cases']), 'step_count_agreement': ratio(c['step_count_equal'], c['cases']), 'semantic_plan_agreement': ratio(c['semantic_plan_equal'], c['cases']), 'behavior_sequence_agreement': ratio(c['behavior_sequence_equal'], c['cases']), **{name+'_agreement': ratio(c[name+'_equal'], c['teacher_steps']) for name in ['behavior', 'completion', 'lane', 'target']}, 'target_id_agreement_when_teacher_present': ratio(c['target_present_equal'], c['target_present']), 'speed_within_0p5_mps_including_missing_as_failure': ratio(c['speed_hits'], c['speed_teacher_present']), 'numeric_speed_coverage': ratio(c['speed_both_present'], c['speed_teacher_present'])}
        results[model] = {'counts': c, 'metrics': metrics, 'speed_mae_over_both_present_mps': sum(deltas)/len(deltas) if deltas else None, 'speed_max_abs_error_over_both_present_mps': max(deltas) if deltas else None}
    # These are agreement declines versus stored Teacher labels, not human truth.
    declines = {'teacher_label_to_fp32': {}, 'teacher_label_to_int8': {}, 'fp32_to_int8': {}}
    for name in results['FP32']['metrics']:
        f = results['FP32']['metrics'][name]['value']; q = results['INT8']['metrics'][name]['value']
        declines['teacher_label_to_fp32'][name] = {'absolute_drop_percentage_points': (1-f)*100 if f is not None else None, 'relative_decay': 1-f if f is not None else None}
        declines['teacher_label_to_int8'][name] = {'absolute_drop_percentage_points': (1-q)*100 if q is not None else None, 'relative_decay': 1-q if q is not None else None}
        declines['fp32_to_int8'][name] = {'absolute_drop_percentage_points': (f-q)*100 if f is not None and q is not None else None, 'relative_decay': 1-q/f if f else None}
    pair_counts = {'cases': 850, 'semantic_plan_equal': 0, 'behavior_sequence_equal': 0, 'target_speed_numeric_pairs': 0, 'target_speed_one_missing': 0}
    paired_speed = []; pair_mismatch = []
    for k in records['FP32']:
        f = records['FP32'][k]; q = records['INT8'][k]
        if f['status'] != 'SUCCESS' or q['status'] != 'SUCCESS': pair_mismatch.append({'cohort': k[0], 'case_id': k[1], 'reason': 'inference error'}); continue
        fs = f['prediction']['steps']; qs = q['prediction']['steps']
        same = [signature(s) for s in fs] == [signature(s) for s in qs]
        pair_counts['semantic_plan_equal'] += same
        pair_counts['behavior_sequence_equal'] += [s.get('behavior') for s in fs] == [s.get('behavior') for s in qs]
        if not same: pair_mismatch.append({'cohort': k[0], 'case_id': k[1], 'reason': 'semantic fields differ'})
        for fp, qp in zip(fs, qs):
            fv = fp.get('target', {}).get('target_speed_mps'); qv = qp.get('target', {}).get('target_speed_mps')
            if isinstance(fv, (int, float)) and isinstance(qv, (int, float)): pair_counts['target_speed_numeric_pairs'] += 1; paired_speed.append(abs(fv-qv))
            elif (fv is None) != (qv is None): pair_counts['target_speed_one_missing'] += 1
    out = HERE/('offline850_comparison_'+manifests['FP32']['run_id'].removeprefix('offline850_new_cpu_fp32_')); out.mkdir(exist_ok=False)
    report = {'scope': 'New local CPU offline replay; no ASR or CARLA; stored Teacher labels not rerun; no official-image timing or formal B2 Gate.', 'denominator_policy': 'All 850 cases and all 931 Teacher steps; missing predicted steps count as mismatches. Null target equals null target in all-step target metric; separate nonnull-Teacher target metric is supplied. Semantic plan compares behavior, completion type, target lane and target ID plus sequence length; speed omitted from this categorical signature and reported separately.', 'runs': {m: {'run_id': v['run_id'], 'model': v['model'], 'packages': v['packages'], 'source_bindings': v['source_bindings']} for m, v in manifests.items()}, 'results': results, 'agreement_declines': declines, 'pairwise_fp32_int8': {'counts': pair_counts, 'semantic_plan_agreement': ratio(pair_counts['semantic_plan_equal'], 850), 'behavior_sequence_agreement': ratio(pair_counts['behavior_sequence_equal'], 850), 'target_speed_mae_mps': sum(paired_speed)/len(paired_speed) if paired_speed else None, 'target_speed_max_delta_mps': max(paired_speed) if paired_speed else None, 'mismatched_cases': pair_mismatch}, 'teacher_label_mismatches': all_details, 'source_output_bindings': source}
    (out/'comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    lines = ['# 新 CPU 850 例离线补采结果', '', report['scope'], '', '| 模型 | 指标 | 分子/分母 | 值 |', '|---|---|---|---|']
    with (out/'metrics.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f); w.writerow(['model', 'metric', 'numerator', 'denominator', 'value'])
        for model, result in results.items():
            for name, v in result['metrics'].items():
                w.writerow([model, name, v['numerator'], v['denominator'], v['value']]); lines.append(f"| {model} | {name} | {v['numerator']}/{v['denominator']} | {v['value']:.6%} |")
    lines += ['', report['denominator_policy'], '', 'Teacher 100% 基线表示自身保存标签一致率，并非独立人工真值。语义字段一致不代表完整数值计划等同；速度覆盖、误差和缺值必须同时查看。新结果独立保存，不覆盖旧 B3 成绩；旧的包含缺值分母 MAE 不在此沿用。', '', '具体逐例错误、模型/输入/源码和原始输出文件哈希见 comparison.json。']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'output': str(out), 'results': {m: {'counts': r['counts'], 'metrics': r['metrics'], 'speed_mae': r['speed_mae_over_both_present_mps']} for m, r in results.items()}}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__': raise SystemExit(main())
