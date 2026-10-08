"""Recompute saved predictions only. No model, network, CARLA, or gate signing.
Run: python recompute_results.py [--package-root PATH]
All outputs stay beside this script. Python 3.10+, standard library only.
"""
import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--package-root', type=Path, default=OUT.parents[1])
args = parser.parse_args()
ROOT = args.package_root.resolve()
bindings = {}

def read(rel, jsonl=False):
    p = ROOT / rel
    b = p.read_bytes()
    bindings[str(rel)] = {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}
    t = b.decode('utf-8-sig')
    return [json.loads(l) for l in t.splitlines() if l.strip()] if jsonl else json.loads(t)

def ratio(n, d):
    return {'numerator': n, 'denominator': d, 'value': n/d if d else None}

def edit(a, b):
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        row = [i]
        for j, cb in enumerate(b, 1):
            row.append(min(row[-1]+1, prev[j]+1, prev[j-1]+(ca != cb)))
        prev = row
    return prev[-1]

# Saved 240-case diagnostics use the current v3.1 adapter and model hashes.
BASE = Path('03_训练与模型/A2模型与量化/evaluation/full_int8')
diagnostic = read(BASE/'diagnostic_report.json')
labels_rel = Path('02_源码与部署/source/challenge/dataset/governance/b1_closeout_v1/independent_validation_v1/cases.jsonl')
labels = {r['sample_id']: r for r in read(labels_rel, True)}
predictions = {}
for model, fname in [('Teacher', 'teacher_reference_predictions.jsonl'), ('FP32', 'student_fp32_predictions.jsonl'), ('INT8', 'student_int8_predictions.jsonl')]:
    rows = read(BASE/fname, True)
    data = {r['sample_id']: r for r in rows}
    assert len(data) == len(rows) == 240 and set(data) == set(labels), 'Missing/duplicate prediction or label'
    predictions[model] = data

def score(data):
    c = Counter()
    details = []
    for sid, case in labels.items():
        record = data[sid]
        target = case['teacher_plan']['steps']
        actual = record.get('prediction', {}).get('steps', []) if record['status'] == 'SUCCESS' else []
        c['cases'] += 1
        c['successful_predictions'] += record['status'] == 'SUCCESS'
        c['step_count_equal'] += len(actual) == len(target)
        c['behavior_sequence_equal'] += [s.get('behavior') for s in actual] == [s.get('behavior') for s in target]
        mismatches = []
        for i, t in enumerate(target):
            a = actual[i] if i < len(actual) else {}
            c['teacher_steps'] += 1
            for field, tv, av in [
                ('behavior', t.get('behavior'), a.get('behavior')),
                ('completion_type', t.get('completion', {}).get('type'), a.get('completion', {}).get('type')),
                ('target_lane', t.get('target', {}).get('target_lane'), a.get('target', {}).get('target_lane')),
                ('target_id', t.get('target', {}).get('target_id'), a.get('target', {}).get('target_id'))]:
                matched = i < len(actual) and tv == av
                c[field+'_equal'] += matched
                if not matched: mismatches.append({'step': i+1, 'field': field, 'reference': tv, 'prediction': av})
        details.append({'sample_id': sid, 'scenario': case.get('metadata', {}).get('scenario_id'), 'teacher_steps': len(target), 'student_steps': len(actual), 'mismatches': mismatches})
    return {'counts': dict(c), 'metrics': {
        'step_count_agreement': ratio(c['step_count_equal'], c['cases']),
        'behavior_sequence_agreement': ratio(c['behavior_sequence_equal'], c['cases']),
        **{f+'_agreement': ratio(c[f+'_equal'], c['teacher_steps']) for f in ('behavior', 'completion_type', 'target_lane', 'target_id')}
    }, 'per_case': details}

case_results = {m: score(data) for m, data in predictions.items()}
assert all(predictions['Teacher'][sid]['prediction'] == labels[sid]['teacher_plan'] for sid in labels), 'Stored Teacher differs from case reference'
decline = {}
for m in ('FP32', 'INT8'):
    decline[m] = {k: {'absolute_drop_percentage_points': 100*(case_results['Teacher']['metrics'][k]['value']-v['value']), 'relative_decay': 1-v['value']/case_results['Teacher']['metrics'][k]['value']} for k, v in case_results[m]['metrics'].items()}

# Genuine audio inference, but the 250 audio inputs are TTS, not human recordings.
ASR = Path('06_评测说明与冻结方案/历史ASR实跑证据')
manifest = read(ASR/'原始输入/manifest.json')
asr = {}
for name in ('local_clean_250_final_20260726', 'local_synthetic_snr10_250_20260726', 'local_clean_250_cascade_priority_20260726'):
    report = read(ASR/'原始结果'/f'{name}.json')
    records = report['records']
    assert len(records) == len(manifest) == 250
    # Normalization exactly follows the historical evaluator, including case folding.
    def norm(t): return re.sub(r'[\W_]+', '', unicodedata.normalize('NFKC', str(t)).lower(), flags=re.UNICODE)
    total_chars = sum(r['reference_chars'] for r in records)
    distance = sum(r['edit_distance'] for r in records)
    for item, rec in zip(manifest, records):
        assert item['text'] == rec['reference_text'] and item['intent'] == rec['expected_intent'] and item['slots'] == rec['expected_slots']
        ref, hyp = norm(rec['reference_text']), norm(rec['source_text'])
        assert len(ref) == rec['reference_chars'] and edit(ref, hyp) == rec['edit_distance'] and (ref == hyp) == rec['asr_exact'], 'Saved transcript verdict differs from recomputation'
        audio = ROOT / ASR / '原始输入' / item['audio']
        assert audio.is_file(), f'Missing audio {audio}'
        bindings[str(audio.relative_to(ROOT))] = {'sha256': hashlib.sha256(audio.read_bytes()).hexdigest(), 'bytes': audio.stat().st_size}
    asr[name] = {
        'source': str(ASR/'原始结果'/f'{name}.json'), 'condition': report['condition'],
        'metrics': {'asr_exact_accuracy': ratio(sum(bool(r['asr_exact']) for r in records), len(records)),
        'asr_character_accuracy': ratio(total_chars-distance, total_chars),
        'intent_accuracy': ratio(sum(bool(r['intent_ok']) for r in records), len(records)),
        'slot_accuracy': ratio(sum(bool(r['slots_ok']) for r in records), len(records))},
        'recomputation_scope': 'ASR exact/character verdicts independently recomputed from saved transcripts using historical NFKC normalization and Levenshtein distance; intent/slot verdicts aggregated; no new ASR inference.',
        'inference_success': sum(bool(r['inference_ok']) for r in records),
        'synthesized_audio': True, 'current_teacher_student_asr_comparison': False,
    }

# These 83-scenario artifacts contain aggregates and failures, not full per-run logs.
SUITE = Path('05_B3性能与评测/04_结果汇总/v31_fp32_int8_20261008')
scenarios = {}
for m, fn in [('FP32', '01_suite_full83_fp32_v31.json'), ('INT8', '02_suite_full83_int8.json')]:
    s = read(SUITE/fn)
    assert s['runs'] == 83 and sum(g['runs'] for g in s['by_suite_group'].values()) == 83
    assert sum(g['passed'] for g in s['by_suite_group'].values()) == s['passed']
    assert s['oracle_alignment']['checked']-s['oracle_alignment']['passed'] == len(s['oracle_alignment']['failed_scenarios'])
    scenarios[m] = {'model': s['model'], 'source': str(SUITE/fn), 'scenario_task_success': ratio(s['passed'], s['runs']),
        'scenario_behavior_oracle_alignment': ratio(s['oracle_alignment']['passed'], s['oracle_alignment']['checked']),
        'extension_acceptance': ratio(s['extension_acceptance']['passed'], s['extension_acceptance']['runs']),
        'groups': s['by_suite_group'], 'failed_scenarios': s['failed_scenarios'],
        'recomputation_scope': 'Aggregate arithmetic checked against group counts and saved failure list; raw simulator logs not rerun.'}
source850 = read(SUITE/'05_teacher_student_decay_v31.json')
cohorts = {}
for folder in ['d2_v1_1_val', 'd3_wave2_safe_short_v1_val', 'd3_targeted_gap_strict_v1_val', 'd3_turn_gap_60_strict_v1_val', 'd3_gap300_strict_v1_val', 'b1_ms34_supplement_v1_val']:
    rows = read(Path('02_源码与部署/source/challenge/hil/frozen')/folder/'cases.jsonl', True)
    steps = [s for r in rows for s in r['teacher_plan']['steps']]
    cohorts[folder] = {'cases': len(rows), 'teacher_steps': len(steps), 'teacher_target_id_present': sum(s.get('target', {}).get('target_id') is not None for s in steps), 'teacher_numeric_speed_present': sum(isinstance(s.get('target', {}).get('target_speed_mps'), (int, float)) for s in steps)}
assert sum(c['cases'] for c in cohorts.values()) == 850
summary850 = {m: source850['case_level_'+m.lower()]['summary'] for m in ('FP32', 'INT8')}

result = {
    'schema_version': 'saved-evidence-reconciliation-1.0', 'formal_b2_gate_decision': False,
    'method': 'Recompute archived evidence; no new model execution, no fabricated labels/signatures.',
    'current_models': {'fp32': diagnostic['fp32_candidate'], 'int8': diagnostic['int8_candidate'], 'adapter_contract_id': diagnostic['adapter_contract_id']},
    'saved_240_case_semantic_plan_agreement': {'annotation': 'Frozen case teacher_plan, Qwen/Qwen3.5-2B stored Teacher plans. Teacher 100% is agreement with its own labels, not independently established human ground truth.',
        'denominators': '240 cases; all Teacher steps, including absent Student steps as mismatches; target_id null==null counts as match.',
        'dataset': diagnostic['dataset'], 'results': case_results, 'teacher_to_student_decline': decline,
        'use_scope': 'Current v3.1 saved prediction post-hoc diagnostic only. Labels were exposed before adapter revision; not unseen independent B2 validation.', 'formal_blockers': diagnostic['formal_blockers']},
    'historical_250_asr': asr,
    '83_scenario_application_metrics': scenarios,
    '850_case_aggregate_evidence': {'source': str(SUITE/'05_teacher_student_decay_v31.json'), 'cohort_counts_recomputed': cohorts, 'saved_summaries': summary850,
        'scope': 'Cohort inputs/Teacher step counts verified. Student per-case predictions for these 850 cases are absent, so Student agreement ratios are source-reported aggregates, not fresh per-case recomputation.',
        'speed_warning': 'Source speed MAE divides finite-value error sum by all numeric Teacher-speed steps including missing Student speeds. Do not interpret this as MAE over matched numeric pairs. Tolerance hit rate treats missing speeds as failures.',
        'not_asr': True},
    'shared_asr_frontend': {'confirmed': 'Saved ModelRequest.source_text is already text; compressed Student handles downstream plan generation. The archived ASR evaluation covers a separate voice pipeline.',
        'not_confirmed': 'No paired current Teacher/FP32/INT8 run manifest binds the identical ASR weights, configuration, source revision and audio input hashes. Shared architecture does not prove current ASR decay = 0.',
        'missing_inputs': ['Current paired Teacher/Student audio-front-end run manifest or saved transcripts on the same 250 inputs', 'Current ASR/frontend weight and config hashes for both endpoints', 'Unseen independent B2 benchmark and frozen policy for formal gate'],
        'official_human_recording_requirement_claimed': False},
    'source_bindings': bindings,
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT/'application_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
table = []
for m, r in case_results.items():
    for k, v in r['metrics'].items(): table.append(['240已存预测', m, k, v['numerator'], v['denominator'], v['value'], 'Teacher计划标签；事后诊断'])
for name, r in asr.items():
    for k, v in r['metrics'].items(): table.append(['250历史TTS音频', name, k, v['numerator'], v['denominator'], v['value'], '历史前端实跑；非当前模型ASR衰减'])
for m, r in scenarios.items():
    for k in ['scenario_task_success', 'scenario_behavior_oracle_alignment', 'extension_acceptance']:
        v = r[k]; table.append(['83场闭环', m, k, v['numerator'], v['denominator'], v['value'], '原聚合记录复核；oracle分母80'])
for m, s in summary850.items():
    for k, d in [('step_count_agreement', 850), ('behaviour_agreement', s['steps_compared']), ('lane_agreement', s['steps_compared']), ('completion_agreement', s['steps_compared']), ('target_id_agreement', sum(c['teacher_target_id_present'] for c in cohorts.values())), ('speed_within_0p5_mps_rate', sum(c['teacher_numeric_speed_present'] for c in cohorts.values()))]:
        n = round(s[k]*d)
        assert abs(n/d-s[k]) < 1e-10, 'Aggregate ratio denominator mismatch'
        table.append(['850源报告聚合', m, k, n, d, s[k], '来源聚合比例；仅Teacher分母独立复算，非逐例Student复算'])
with (OUT/'application_metrics.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['证据集合', '模型或条件', '指标', '分子', '分母', '比例', '适用范围']); w.writerows(table)
lines = ['# 应用指标结果表（已有证据复算）', '', '本目录给出可直接引用的结果及来源哈希；不是 B2 Gate 签署，也不代表新增未见样本评测。', '', '| 集合 | 模型/条件 | 指标 | 分子/分母 | 结果 |', '|---|---|---|---|---|']
for group, m, k, n, d, value, scope in table: lines.append(f'| {group} | {m} | {k} | {n}/{d} | {value:.4%} |')
lines += ['', '240 条以保存的 Qwen Teacher 计划作标签，Teacher 的 100% 是自身标签一致率。所有参考步纳入分母，Student 缺步按错误，null 目标对 null 目标按相等。行为序列一致率仅比较行为与步数，不包含速度等连续字段。原诊断明确标签在适配器修订前已暴露，因此这些数字只用于事后应用诊断。当前 FP32 与 INT8 在表内语义计划指标无额外下降，不能代称 ASR 指标。', '', '83 场采用场景自带的 oracle_expected_behaviors 判据；只有 80 场有该检查，其余 3 场不进入对齐分母。任务完成、扩展验收、oracle 对齐是不同指标。表中数字来自保存的聚合记录，复算脚本只复核其分组计数与失败数。', '', '850 例六队列/931 个 Teacher 步的输入数量已经复算。当前 v3.1 的保存聚合结果：FP32/INT8 行为对齐均为 99.5704%，车道/完成类型均为 99.7852%；Teacher 提供目标时目标一致率 88.7324%。这批 Student 逐例输出不在包内，故只收录为源报告聚合证据，不能冒充新复算。速度缺值有 561 步；原报告 MAE 使用包含缺值的分母，不应据此宣传低速度误差。', '', '250 条音频均为 edge-tts 合成，历史报告确实执行过音频识别；完全匹配/字符准确率/意图/槽位指标分开列出。10 dB SNR 数字加噪不能写为 50 dBA。没有材料证明官方强制真人音频。', '', '压缩模型接收已转写文本，可确认 ASR 是上游独立模块。尚无当前 Teacher/FP32/INT8 共用前端的同次运行清单与权重、配置绑定，故不能写“当前 ASR 衰减 0%”。正式衰减仍需当前同输入的保存转写结果及模型前端身份，正式 B2 Gate 还需未见独立测试集与冻结判据。', '', '运行复算：`python recompute_results.py`。只读包内保存的数据，不运行模型/CARLA，不联网；只覆盖本目录三份结果。`application_results.json` 保存逐例差异、模型身份、限制及全部输入哈希，`application_metrics.csv` 为可引用表。']
(OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(json.dumps({'outputs': ['application_results.json', 'application_metrics.csv', 'RESULTS.md'], 'case_count': len(labels), 'asr_count': len(manifest), 'frozen_case_count': sum(c['cases'] for c in cohorts.values())}, ensure_ascii=False))
