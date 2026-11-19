"""Nine AI-authored DEVELOPMENT drafts, never new independent Test or approved data."""
import argparse
import json
from pathlib import Path

from ...data import load_jsonl, output_directory, protected_hashes, text_hash
from ...prepare import external_registry
from ...proposals import draft_packets, draft_markdown, draft_summary
from ...release import write_rows


def step(action, evidence, **slots):
    return dict(action=action, evidence=evidence, target_text=None, direction=None,
                speed_kph=None, gap_m=None, condition=None) | slots


def drafts():
    cases = [
        ('passing_roles', 'yield_follow', '右方那辆电动拖车不会移动，请由本车从左边越过它。',
         [step('AVOID_OBSTACLE', '从左边越过它', target_text='右方那辆电动拖车', direction='LEFT')], {}),
        ('passing_roles', 'yield_follow', '右方那辆电动拖车正在驶来，请让它先通过。',
         [step('YIELD', '让它先通过', target_text='右方那辆电动拖车')], {}),
        ('parking_location', 'lane_choice', '驶过入口标志后，就地停车，不要靠边停车。',
         [step('STOP', '就地停车', condition='驶过入口标志后')], {'PULL_OVER': True}),
        ('parking_location', 'lane_choice', '驶过入口标志后，靠边停车。',
         [step('PULL_OVER', '靠边停车', condition='驶过入口标志后')], {}),
        ('direction_and_tail', 'lane_choice', '先借用左边相邻车道，再往右侧绕开隔离水马，末尾继续沿当前车道走。',
         [step('CHANGE_LANE_LEFT', '借用左边相邻车道', direction='LEFT'),
          step('AVOID_OBSTACLE', '往右侧绕开隔离水马', direction='RIGHT', target_text='隔离水马'),
          step('KEEP_LANE', '继续沿当前车道走')], {}),
        ('direction_and_tail', 'lane_choice', '先借用右边相邻车道，再往左侧绕开隔离水马，末尾继续沿当前车道走。',
         [step('CHANGE_LANE_RIGHT', '借用右边相邻车道', direction='RIGHT'),
          step('AVOID_OBSTACLE', '往左侧绕开隔离水马', direction='LEFT', target_text='隔离水马'),
          step('KEEP_LANE', '继续沿当前车道走')], {}),
        ('gate_scope', 'conditional_resume', '把速度设为21公里每小时，然后跟随棕色面包车。',
         [step('SET_SPEED', '把速度设为21公里每小时', speed_kph=21),
          step('FOLLOW', '跟随棕色面包车', target_text='棕色面包车')], {}),
        ('gate_scope', 'conditional_resume', '电子栏杆收起后，把速度设为21公里每小时并跟随棕色面包车。',
         [step('SET_SPEED', '把速度设为21公里每小时', speed_kph=21, condition='电子栏杆收起后'),
          step('FOLLOW', '跟随棕色面包车', target_text='棕色面包车', condition='电子栏杆收起后')], {}),
        ('gate_scope', 'conditional_resume', '电子栏杆收起后，把速度设为21公里每小时；听到调度员确认后，再跟随棕色面包车。',
         [step('SET_SPEED', '把速度设为21公里每小时', speed_kph=21, condition='电子栏杆收起后'),
          step('FOLLOW', '跟随棕色面包车', target_text='棕色面包车', condition='听到调度员确认后')], {}),
    ]
    seeds, labels = [], []
    for i, (group, family, source, steps, prohibited) in enumerate(cases, 1):
        identifier = f'BOUNDARY_V2_{i:03d}'
        seeds.append(dict(sample_id=identifier, source_text=source, semantic_family=family,
                          group_id='boundaries_v2_' + group))
        labels.append(dict(sample_id=identifier, source_text=source,
            label=dict(steps=steps, prohibited_actions=prohibited, requires_confirmation=False), contract_gap=False,
            review_notes=['AI构造的开发草稿，非真实口语、Teacher输出或独立测试。',
                          '核对目标指代、各步方向、条件有无及范围，并检查是否应与旧Train/Dev组并组；本批不得自动进入训练。']))
    return draft_packets(seeds, labels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-reviewed', type=Path, required=True)
    parser.add_argument('--test-registry', type=Path, required=True)
    parser.add_argument('--supplemental-registry', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    previous = load_jsonl(args.previous_reviewed)
    protected = protected_hashes() | external_registry(args.test_registry) | external_registry(args.supplemental_registry, role='INDEPENDENT_VALIDATION')
    protected |= {text_hash(r['source_text']) for r in previous}
    packets = drafts()
    if any(text_hash(r['source_text']) in protected for r in packets):
        raise ValueError('exact protected or existing text collision')
    def grams(text):
        return {text[i:i+3] for i in range(max(1, len(text)-2))}
    neighbors = []
    for row in packets:
        left = grams(row['source_text'])
        ranked = sorted([(len(left & grams(old['source_text'])) / len(left | grams(old['source_text'])), old)
                         for old in previous], key=lambda item: (-item[0], item[1]['sample_id']))[:3]
        neighbors.append(dict(sample_id=row['sample_id'], nearest=[dict(score=score, sample_id=old['sample_id'],
            group_id=old['group_id'], split=old['split'], source_text=old['source_text']) for score, old in ranked]))
    output = output_directory(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)
    write_rows(output / 'draft_review_queue.jsonl', packets)
    (output / 'REVIEW.md').write_text(draft_markdown(packets), encoding='utf-8')
    (output / 'near_neighbors.json').write_text(json.dumps(neighbors, ensure_ascii=False, indent=2), encoding='utf-8')
    report = draft_summary(packets)
    report.update(group_count=len({r['group_id'] for r in packets}), exact_exclusion_check_passed=True,
                  grouping_review_pending=True, near_duplicate_independence_proven=False,
                  development_informed_by_disclosed_errors=True, added_to_current_training=False)
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
