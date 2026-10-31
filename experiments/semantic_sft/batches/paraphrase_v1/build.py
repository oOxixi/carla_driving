"""Twelve authored wording variants; drafts only, retaining related existing group IDs."""
import argparse
import json
from pathlib import Path

from qwen_service.task_understanding import _example_step as step
from experiments.semantic_sft.data import baseline_guard, output_directory
from experiments.semantic_sft.proposals import draft_packets, draft_markdown, draft_summary


def examples():
    def case(text, family, group, steps, prohibited=None, confirm=False):
        return (text, family, group, {'steps':steps,'prohibited_actions':prohibited or {},'requires_confirmation':confirm})
    return [
        case('先留在当前车道，左边出现足够安全间距后再向左并线','lane_choice','lane_left_after_gap_01',[
            step('先留在当前车道','KEEP_LANE'),step('再向左并线','CHANGE_LANE_LEFT',direction='LEFT',condition='左边出现足够安全间距后')]),
        case('先保持当前车道，在左车道安全间隙足够时并入左边','lane_choice','lane_left_after_gap_01',[
            step('先保持当前车道','KEEP_LANE'),step('并入左边','CHANGE_LANE_LEFT',direction='LEFT',condition='在左车道安全间隙足够时')]),
        case('先减到22公里每小时，等路边作业人员离开后恢复35公里每小时','conditional_resume','workers_clear_resume_01',[
            step('先减到22公里每小时','SLOW_DOWN',speed_kph=22),step('恢复35公里每小时','SET_SPEED',speed_kph=35,condition='等路边作业人员离开后')]),
        case('降速至22公里每小时，待路边作业人员撤离后将车速恢复为35公里每小时','conditional_resume','workers_clear_resume_01',[
            step('降速至22公里每小时','SLOW_DOWN',speed_kph=22),step('将车速恢复为35公里每小时','SET_SPEED',speed_kph=35,condition='待路边作业人员撤离后')]),
        case('从左侧绕过停着的货运车，完成后回到原车道，再把车速设为33公里每小时','overtake_return','parkedtruck_left_return_02',[
            step('从左侧绕过停着的货运车','AVOID_OBSTACLE',target_text='停着的货运车',direction='LEFT'),
            step('回到原车道','RETURN_TO_LANE',condition='完成后'),step('再把车速设为33公里每小时','SET_SPEED',speed_kph=33)]),
        case('由左边通过停放的货运车，通过后返回原车道，然后设定33公里每小时','overtake_return','parkedtruck_left_return_02',[
            step('由左边通过停放的货运车','AVOID_OBSTACLE',target_text='停放的货运车',direction='LEFT'),
            step('返回原车道','RETURN_TO_LANE',condition='通过后'),step('然后设定33公里每小时','SET_SPEED',speed_kph=33)]),
        case('禁止向左变道，先减至17公里每小时，再靠边停稳','negative_instruction','no_left_slow_park_02',[
            step('先减至17公里每小时','SLOW_DOWN',speed_kph=17),step('再靠边停稳','PULL_OVER')],{'CHANGE_LANE_LEFT':True}),
        case('不要向左并线，减速到17公里每小时后靠边停车','negative_instruction','no_left_slow_park_02',[
            step('减速到17公里每小时','SLOW_DOWN',speed_kph=17),step('靠边停车','PULL_OVER',condition='减速到17公里每小时后')],{'CHANGE_LANE_LEFT':True}),
        case('先礼让推婴儿车的行人，再跟随前面的面包车，最后靠边停车','yield_follow','stroller_yield_van_01',[
            step('先礼让推婴儿车的行人','YIELD',target_text='推婴儿车的行人'),step('再跟随前面的面包车','FOLLOW',target_text='前面的面包车'),step('最后靠边停车','PULL_OVER')]),
        case('等推婴儿车的行人通过后跟随那辆面包车，随后靠边停好','yield_follow','stroller_yield_van_01',[
            step('等推婴儿车的行人通过','YIELD',target_text='推婴儿车的行人'),step('跟随那辆面包车','FOLLOW',target_text='那辆面包车',condition='等推婴儿车的行人通过后'),step('随后靠边停好','PULL_OVER')]),
        case('那辆先过去以后再跟上','ambiguity','unspecified_vehicle_reference_01',[
            step('那辆先过去以后再跟上','HOLD')],confirm=True),
        case('等那个车过去，然后跟着它走','ambiguity','unspecified_vehicle_reference_01',[
            step('等那个车过去，然后跟着它走','HOLD')],confirm=True),
    ]


def packets():
    seeds, proposals = [], []
    for number,(text,family,group,label) in enumerate(examples(),1):
        identifier=f'SFT_PARA_V1_{number:03d}'
        seeds.append({'sample_id':identifier,'source_text':text,'semantic_family':family,'group_id':group})
        proposals.append({'sample_id':identifier,'source_text':text,'label':label,'contract_gap':False,
            'review_notes':['AI编写的词面/参数变体，不是Teacher输出或人工金标；需真实复核。',
                            '沿用相关旧group_id，不得当作新独立模板或拆到原组的另一split。']})
    return draft_packets(seeds,proposals)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if not baseline_guard()['passed']:
        raise ValueError('baseline guard failed')
    rows=packets()
    output=output_directory(args.output_dir)
    output.mkdir(parents=True,exist_ok=False)
    (output/'draft_review_queue.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    (output/'draft_review_sheet.md').write_text(draft_markdown(rows),encoding='utf-8')
    (output/'report.json').write_text(json.dumps(draft_summary(rows),indent=2),encoding='utf-8')
    print(json.dumps({'draft_rows':len(rows),'approved_rows':0,'output':str(output)}))


if __name__=='__main__':
    main()
