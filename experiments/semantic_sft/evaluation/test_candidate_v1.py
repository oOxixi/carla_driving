"""Prospective authored semantic Test candidates. Never train on these records."""
import argparse
import json
from pathlib import Path

from qwen_service.task_understanding import _example_step as s, validate_extraction
from experiments.semantic_sft.data import HERE, baseline_guard, canonical_hash, load_jsonl, output_directory, protected_hashes, text_hash
from experiments.semantic_sft.batches.paraphrase_v1.build import examples as train_expansion


def candidates():
    def row(text, family, group, steps, prohibited=None, confirm=False):
        return {'source_text':text,'semantic_family':family,'evaluation_group_id':group,
                'expected_draft':{'steps':steps,'prohibited_actions':prohibited or {},'requires_confirmation':confirm},
                'status':'TEST_CANDIDATE_NOT_FROZEN','reserved_for_evaluation':True}
    rows=[
        row('左侧安全时向左并线，把车速设为26公里每小时，右侧安全时再向右并线','lane_choice','test_lane_speed_lane',[
            s('向左并线','CHANGE_LANE_LEFT',direction='LEFT',condition='左侧安全时'),s('把车速设为26公里每小时','SET_SPEED',speed_kph=26),
            s('再向右并线','CHANGE_LANE_RIGHT',direction='RIGHT',condition='右侧安全时')]),
        row('遇到路口先左转，通过路口后向右变道','lane_choice','test_turn_then_lane',[
            s('先左转','TURN_LEFT',direction='LEFT',condition='遇到路口'),s('向右变道','CHANGE_LANE_RIGHT',direction='RIGHT',condition='通过路口后')]),
        row('先设为20公里每小时，进入隧道后降到15公里每小时，驶出隧道后恢复20公里每小时','conditional_resume','test_tunnel_speed_stages',[
            s('先设为20公里每小时','SET_SPEED',speed_kph=20),s('降到15公里每小时','SLOW_DOWN',speed_kph=15,condition='进入隧道后'),
            s('恢复20公里每小时','SET_SPEED',speed_kph=20,condition='驶出隧道后')]),
        row('先减到18公里每小时，确认积水路段通过后保持当前车道并把速度恢复到30公里每小时','conditional_resume','test_water_clear_two_tasks',[
            s('先减到18公里每小时','SLOW_DOWN',speed_kph=18),s('保持当前车道','KEEP_LANE',condition='确认积水路段通过后'),
            s('把速度恢复到30公里每小时','SET_SPEED',speed_kph=30,condition='确认积水路段通过后')]),
        row('先减速到14公里每小时，从左侧绕过故障轿车，再从右侧绕过施工锥桶，最后回到原车道','overtake_return','test_two_avoidance_targets',[
            s('先减速到14公里每小时','SLOW_DOWN',speed_kph=14),s('从左侧绕过故障轿车','AVOID_OBSTACLE',target_text='故障轿车',direction='LEFT'),
            s('再从右侧绕过施工锥桶','AVOID_OBSTACLE',target_text='施工锥桶',direction='RIGHT'),s('最后回到原车道','RETURN_TO_LANE')]),
        row('从右侧超越前面的厢式货车，通过后先保持当前车道，直到左侧安全时返回原车道','overtake_return','test_wait_before_return',[
            s('从右侧超越前面的厢式货车','AVOID_OBSTACLE',target_text='前面的厢式货车',direction='RIGHT'),
            s('先保持当前车道','KEEP_LANE',condition='通过后'),s('返回原车道','RETURN_TO_LANE',condition='直到左侧安全时')]),
        row('禁止右转，先左转，再停车等待','negative_instruction','test_prohibit_turn_execute_other',[
            s('先左转','TURN_LEFT',direction='LEFT'),s('再停车等待','STOP')],{'TURN_RIGHT':True}),
        row('不要向右变道，也不要向左变道，先将车速设为21公里每小时，然后保持当前车道','negative_instruction','test_prohibit_both_lane_changes',[
            s('先将车速设为21公里每小时','SET_SPEED',speed_kph=21),s('然后保持当前车道','KEEP_LANE')],{'CHANGE_LANE_RIGHT':True,'CHANGE_LANE_LEFT':True}),
        row('先跟随前方小客车并保持5米距离，再让右侧行人先通过，最后右转','yield_follow','test_follow_yield_turn',[
            s('先跟随前方小客车并保持5米距离','FOLLOW',target_text='前方小客车',gap_m=5),
            s('再让右侧行人先通过','YIELD',target_text='右侧行人'),s('最后右转','TURN_RIGHT',direction='RIGHT')]),
        row('先让对向公交车通过，再跟随右前方的摩托车保持9米，等摩托车离开后停车','yield_follow','test_yield_follow_conditional_stop',[
            s('先让对向公交车通过','YIELD',target_text='对向公交车'),s('再跟随右前方的摩托车保持9米','FOLLOW',target_text='右前方的摩托车',gap_m=9),
            s('停车','STOP',condition='等摩托车离开后')]),
        row('别减速，把车速降到12公里每小时','ambiguity','test_conflicting_slow_prohibition',[
            s('别减速，把车速降到12公里每小时','HOLD')],{'SLOW_DOWN':True},True),
        row('跟随红色小车，但我说的目标不是红色小车','ambiguity','test_conflicting_target_reference',[
            s('跟随红色小车，但我说的目标不是红色小车','HOLD')],confirm=True),
    ]
    training=load_jsonl(HERE/'seeds.jsonl')+load_jsonl(HERE/'batches/negative_v1/seeds.jsonl')
    training_texts={text_hash(r['source_text']) for r in training}|{text_hash(r[0]) for r in train_expansion()}
    training_groups={r['group_id'] for r in training}
    for index,item in enumerate(rows,1):
        item['case_id']=f'SEM_TEST_CAND_V1_{index:03d}'
        validate_extraction(item['source_text'],item['expected_draft'])
        if text_hash(item['source_text']) in training_texts|protected_hashes() or item['evaluation_group_id'] in training_groups:
            raise ValueError('candidate conflicts with existing training/development material')
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if not baseline_guard()['passed']:
        raise ValueError('baseline guard failed')
    output=output_directory(args.output_dir)
    rows=candidates()
    output.mkdir(parents=True,exist_ok=False)
    (output/'test_candidates.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    lines=['# 待负责人确认的语义Test候选','',
           '12条均未冻结，预期标签为AI草稿。不得训练、调参或根据模型输出修改这些题后仍宣称独立Test。',
           'ID与完全匹配文本检查只是一层保护；请同时审核与训练材料是否为同一语义模板。',
           '本文件不自动产生Frozen Test排除清单。确认后另记冻结版本和哈希。','']
    for row in rows:
        lines.extend([f"## {row['case_id']}",'',row['source_text'],'',f"类别：{row['semantic_family']}；拟定组：{row['evaluation_group_id']}",'',
                      '```json',json.dumps(row['expected_draft'],ensure_ascii=False,indent=2),'```','',
                      '- [ ] 负责人确认语义标签、跨批模板独立性及保留为Test。',''])
    (output/'review_sheet.md').write_text('\n'.join(lines),encoding='utf-8')
    report={'scope':'AUTHORED_PROSPECTIVE_TEST_CANDIDATES_NOT_FROZEN_OR_OFFICIAL_UNSEEN','cases':12,
            'groups':12,'approved':0,'frozen':False,'content_sha256':canonical_hash(rows),
            'model_predictions_read':False,'train_text_exact_overlap':0,'semantic_independence_verified':False}
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    main()
