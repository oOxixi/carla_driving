"""Hand-authored semantic contrasts: review drafts only, not automatic gold or new Test."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from qwen_service.task_understanding import ACTION_ZH, _example_step as s
from experiments.semantic_sft.data import baseline_guard, canonical_hash, load_jsonl, output_directory, text_hash
from experiments.semantic_sft.prepare import external_registry, registry_groups
from experiments.semantic_sft.proposals import draft_packets, draft_markdown, draft_summary
from experiments.semantic_sft.train import sha, verify_release


def build_batch():
    seeds, proposals, groups = [], [], {}
    def case(text, *steps, forbidden=None, confirm=False):
        return text, dict(steps=list(steps), prohibited_actions=forbidden or {}, requires_confirmation=confirm)
    def group(family, identifier, focus, cases):
        groups[identifier] = dict(family=family, focus=focus, sample_ids=[])
        for index, (text, label) in enumerate(cases, 1):
            sample_id = f'SCV1_{identifier}_{index:02d}'
            seeds.append(dict(sample_id=sample_id, source_text=text, semantic_family=family, group_id=identifier))
            proposals.append(dict(sample_id=sample_id, source_text=text, label=label, contract_gap=False,
                review_notes=['负责人待审的AI构造对照文本，不是真实Teacher输出或闭环数据。', focus,
                              '同组对照不能拆到Train/Val；须复核与旧61组及已曝光Test的语义关系。',
                              '仅理解用户意图；禁止事项不授权车辆违反安全层。']))
            groups[identifier]['sample_ids'].append(sample_id)

    group('lane_choice', 'scv1_background_merge_turn_follow', '背景车辆向左不等于本车左转；并线、转弯、跟随和保持车道对照。', [
        case('前面白色微型车向左走了，本车先保持车道，确认左侧空闲后并入左边车道。',
             s('先保持车道','KEEP_LANE'),s('并入左边车道','CHANGE_LANE_LEFT',direction='LEFT',condition='确认左侧空闲后')),
        case('前面白色微型车向左走了，本车保持车道，到了下一个路口再左拐。',
             s('保持车道','KEEP_LANE'),s('再左拐','TURN_LEFT',direction='LEFT',condition='到了下一个路口')),
        case('前面白色微型车向左走了，本车不要跟车，继续沿本车道行驶。',
             s('继续沿本车道行驶','KEEP_LANE'),forbidden={'FOLLOW':True}),
        case('前面白色微型车向左走了，本车跟随白色微型车，保持7米间距。',
             s('跟随白色微型车，保持7米间距','FOLLOW',target_text='白色微型车',gap_m=7)),
    ])
    group('lane_choice', 'scv1_lane_not_junction', '换车道不是路口转弯；未明说安全条件时不在语义标签中补默认条件。', [
        case('在当前路段换到右边那条行车道，之后向前直行。',
             s('换到右边那条行车道','CHANGE_LANE_RIGHT',direction='RIGHT'),s('向前直行','KEEP_LANE',direction='STRAIGHT')),
        case('往左挪一条车道，别转弯，随后继续行驶。',
             s('往左挪一条车道','CHANGE_LANE_LEFT',direction='LEFT'),s('继续行驶','KEEP_LANE'),
             forbidden={'TURN_LEFT':True,'TURN_RIGHT':True}),
        case('车道保持不变，在前方十字路口向右转。',
             s('车道保持不变','KEEP_LANE'),s('向右转','TURN_RIGHT',direction='RIGHT',condition='在前方十字路口')),
        case('不要变道，在前方十字路口向左转。',
             s('向左转','TURN_LEFT',direction='LEFT',condition='在前方十字路口'),
             forbidden={'CHANGE_LANE_LEFT':True,'CHANGE_LANE_RIGHT':True}),
    ])
    group('lane_choice', 'scv1_preserve_tail_tasks', '保留中间任务、后续调速和停车；不是只识别句首动作。', [
        case('先将速度设为27公里每小时，驶离环岛后右转，再保持当前车道，最后靠边停车。',
             s('先将速度设为27公里每小时','SET_SPEED',speed_kph=27),
             s('右转','TURN_RIGHT',direction='RIGHT',condition='驶离环岛后'),s('再保持当前车道','KEEP_LANE'),s('最后靠边停车','PULL_OVER')),
        case('先右拐，接着停车等候，绿灯亮起后再设定24公里每小时。',
             s('先右拐','TURN_RIGHT',direction='RIGHT'),s('停车等候','STOP'),
             s('再设定24公里每小时','SET_SPEED',speed_kph=24,condition='绿灯亮起后')),
        case('先向左变道，接着在下个街口右拐，再把速度设为29公里每小时，最后保持车道。',
             s('先向左变道','CHANGE_LANE_LEFT',direction='LEFT'),s('右拐','TURN_RIGHT',direction='RIGHT',condition='在下个街口'),
             s('再把速度设为29公里每小时','SET_SPEED',speed_kph=29),s('最后保持车道','KEEP_LANE')),
        case('先停车等候；路口放行后左拐，再将车速设为24公里每小时，接着靠边停车。',
             s('先停车等候','STOP'),s('左拐','TURN_LEFT',direction='LEFT',condition='路口放行后'),
             s('再将车速设为24公里每小时','SET_SPEED',speed_kph=24),s('靠边停车','PULL_OVER')),
    ])

    group('conditional_resume', 'scv1_shared_or_separate_gates', '同一条件管辖并列动作，与不同条件分别管辖相区分；不把条件当任务。', [
        case('先停车等候，施工人员撤到护栏外以后，再向右转并将车速设为28公里每小时。',
             s('先停车等候','STOP'),s('再向右转','TURN_RIGHT',direction='RIGHT',condition='施工人员撤到护栏外以后'),
             s('将车速设为28公里每小时','SET_SPEED',speed_kph=28,condition='施工人员撤到护栏外以后')),
        case('施工人员撤到护栏外以后右转；遇到限速牌再将车速设为28公里每小时。',
             s('右转','TURN_RIGHT',direction='RIGHT',condition='施工人员撤到护栏外以后'),
             s('再将车速设为28公里每小时','SET_SPEED',speed_kph=28,condition='遇到限速牌')),
        case('先减到28公里每小时，再右转；转完后停车。',
             s('先减到28公里每小时','SLOW_DOWN',speed_kph=28),s('再右转','TURN_RIGHT',direction='RIGHT'),
             s('停车','STOP',condition='转完后')),
        case('先向右转；停车线前停住，收到放行信号后保持车道继续行驶。',
             s('先向右转','TURN_RIGHT',direction='RIGHT'),s('停住','STOP',condition='停车线前'),
             s('保持车道继续行驶','KEEP_LANE',condition='收到放行信号后')),
    ])
    group('conditional_resume', 'scv1_background_direction_gate', '他人方位或运动方向不复制为本车方向；背景行人不自动变成让行任务。', [
        case('左边的自行车已停在护栏后，本车在下一路口向右拐。',
             s('向右拐','TURN_RIGHT',direction='RIGHT',condition='在下一路口')),
        case('看到右边的行人仍在人行道上时，保持车道继续前进。',
             s('保持车道继续前进','KEEP_LANE',condition='看到右边的行人仍在人行道上时')),
        case('当前车已经向左驶离本车道后，再把速度恢复为31公里每小时。',
             s('再把速度恢复为31公里每小时','SET_SPEED',speed_kph=31,condition='当前车已经向左驶离本车道后')),
        case('本车先停稳，等左边的道闸完全抬起后左拐，然后把车速设为23公里每小时。',
             s('先停稳','STOP'),s('左拐','TURN_LEFT',direction='LEFT',condition='等左边的道闸完全抬起后'),
             s('把车速设为23公里每小时','SET_SPEED',speed_kph=23)),
    ])
    group('conditional_resume', 'scv1_conditional_tail_scope', '条件、顺序词和跨句边界分别标注；恢复任务不因转弯或停车而消失。', [
        case('先左拐并保持车道；电子路牌显示放行后，再右转并设为26公里每小时。',
             s('先左拐','TURN_LEFT',direction='LEFT'),s('保持车道','KEEP_LANE'),
             s('再右转','TURN_RIGHT',direction='RIGHT',condition='电子路牌显示放行后'),
             s('设为26公里每小时','SET_SPEED',speed_kph=26,condition='电子路牌显示放行后')),
        case('经过桥头后向左换一条车道，随后靠边停好。',
             s('向左换一条车道','CHANGE_LANE_LEFT',direction='LEFT',condition='经过桥头后'),s('靠边停好','PULL_OVER')),
        case('先靠边停车；收到出发指令后右转。最后保持车道。',
             s('先靠边停车','PULL_OVER'),s('右转','TURN_RIGHT',direction='RIGHT',condition='收到出发指令后'),s('最后保持车道','KEEP_LANE')),
        case('前方道闸放行后先左转。到达空车位后再靠边停车。',
             s('先左转','TURN_LEFT',direction='LEFT',condition='前方道闸放行后'),s('再靠边停车','PULL_OVER',condition='到达空车位后')),
    ])

    group('overtake_return', 'scv1_pass_follow_lane_contrast', '慢车背景不自动触发超车；超过、跟随、只换车道分别标注，不要求不是全局禁止。', [
        case('绿色维修车行驶缓慢，本车从它左边超过绿色维修车，随后在路边停下。',
             s('从它左边超过绿色维修车','AVOID_OBSTACLE',target_text='绿色维修车',direction='LEFT'),s('在路边停下','PULL_OVER')),
        case('绿色维修车行驶缓慢，本车跟在绿色维修车后面，保持8米。',
             s('跟在绿色维修车后面，保持8米','FOLLOW',target_text='绿色维修车',gap_m=8)),
        case('绿色维修车行驶缓慢，本车只换到左边车道，之后保持车道，不要求超越。',
             s('只换到左边车道','CHANGE_LANE_LEFT',direction='LEFT'),s('保持车道','KEEP_LANE')),
        case('绿色维修车行驶缓慢，本车保持当前车道，维修车退出车道后将速度设为32公里每小时。',
             s('保持当前车道','KEEP_LANE'),s('将速度设为32公里每小时','SET_SPEED',speed_kph=32,condition='维修车退出车道后')),
    ])
    group('overtake_return', 'scv1_composed_pass_tasks', '新组合中分别保留让行、超越、转弯、跟随、返回和调速，不复刻已曝光Test原句。', [
        case('先让赶路的送货员通过，再从右侧绕开装卸货物的皮卡，接着在下个路口左拐，最后靠边停稳。',
             s('先让赶路的送货员通过','YIELD',target_text='赶路的送货员'),
             s('再从右侧绕开装卸货物的皮卡','AVOID_OBSTACLE',target_text='装卸货物的皮卡',direction='RIGHT'),
             s('左拐','TURN_LEFT',direction='LEFT',condition='在下个路口'),s('最后靠边停稳','PULL_OVER')),
        case('先向右变道，再从左侧绕开停靠的网约车，随后跟随黄色校车保持10米，最后停车。',
             s('先向右变道','CHANGE_LANE_RIGHT',direction='RIGHT'),s('再从左侧绕开停靠的网约车','AVOID_OBSTACLE',target_text='停靠的网约车',direction='LEFT'),
             s('跟随黄色校车保持10米','FOLLOW',target_text='黄色校车',gap_m=10),s('最后停车','STOP')),
        case('从右边绕开倒下的广告牌后，回到原来的车道，再从左边避开垃圾清运车，最后减到25公里每小时。',
             s('从右边绕开倒下的广告牌','AVOID_OBSTACLE',target_text='倒下的广告牌',direction='RIGHT'),
             s('回到原来的车道','RETURN_TO_LANE',condition='从右边绕开倒下的广告牌后'),
             s('再从左边避开垃圾清运车','AVOID_OBSTACLE',target_text='垃圾清运车',direction='LEFT'),s('最后减到25公里每小时','SLOW_DOWN',speed_kph=25)),
        case('先在路边停车，车辆再次出发后从右边通过停着的挖掘机，最后回到刚才的车道。',
             s('先在路边停车','PULL_OVER'),s('从右边通过停着的挖掘机','AVOID_OBSTACLE',target_text='停着的挖掘机',direction='RIGHT',condition='车辆再次出发后'),
             s('最后回到刚才的车道','RETURN_TO_LANE')),
    ])
    group('overtake_return', 'scv1_return_or_remain', '返回必须明说；继续沿超车后车道行驶不等于返回，单独返回不补一次超车。', [
        case('从左侧超越洒水车后，把速度设为27公里每小时，再回到原来的车道。',
             s('从左侧超越洒水车','AVOID_OBSTACLE',target_text='洒水车',direction='LEFT'),
             s('把速度设为27公里每小时','SET_SPEED',speed_kph=27,condition='从左侧超越洒水车后'),s('再回到原来的车道','RETURN_TO_LANE')),
        case('从左侧超越洒水车后，把速度设为27公里每小时，之后仍在超车后的车道行驶。',
             s('从左侧超越洒水车','AVOID_OBSTACLE',target_text='洒水车',direction='LEFT'),
             s('把速度设为27公里每小时','SET_SPEED',speed_kph=27,condition='从左侧超越洒水车后'),s('仍在超车后的车道行驶','KEEP_LANE')),
        case('先回到原车道，然后跟随黑色旅行车保持6米。',
             s('先回到原车道','RETURN_TO_LANE'),s('跟随黑色旅行车保持6米','FOLLOW',target_text='黑色旅行车',gap_m=6)),
        case('不要返回原车道，继续沿超车后的车道行驶。',
             s('继续沿超车后的车道行驶','KEEP_LANE'),forbidden={'RETURN_TO_LANE':True}),
    ])

    group('negative_instruction', 'scv1_turn_lane_negation', '禁止转弯不等于禁止同方向变道；禁止变道也不等于禁止路口转弯。', [
        case('不要向左转弯，向左边换一条车道，然后把速度降至24公里每小时。',
             s('向左边换一条车道','CHANGE_LANE_LEFT',direction='LEFT'),s('把速度降至24公里每小时','SLOW_DOWN',speed_kph=24),forbidden={'TURN_LEFT':True}),
        case('禁止向左变道，到了前方路口向左拐，再靠边停车。',
             s('向左拐','TURN_LEFT',direction='LEFT',condition='到了前方路口'),s('再靠边停车','PULL_OVER'),forbidden={'CHANGE_LANE_LEFT':True}),
        case('不要右转，换到右边车道后继续保持车道。',
             s('换到右边车道','CHANGE_LANE_RIGHT',direction='RIGHT'),s('继续保持车道','KEEP_LANE',condition='换到右边车道后'),forbidden={'TURN_RIGHT':True}),
        case('不要向右并线，在下个路口右拐，再把速度设为22公里每小时。',
             s('右拐','TURN_RIGHT',direction='RIGHT',condition='在下个路口'),s('再把速度设为22公里每小时','SET_SPEED',speed_kph=22),forbidden={'CHANGE_LANE_RIGHT':True}),
    ])
    group('negative_instruction', 'scv1_stop_follow_park_scope', '禁止跟车、靠边停车或普通停车的范围不同；不添加原句没有的禁止项。', [
        case('禁止跟车，先让左侧的骑车人通过，再把车速设为19公里每小时。',
             s('先让左侧的骑车人通过','YIELD',target_text='左侧的骑车人'),s('再把车速设为19公里每小时','SET_SPEED',speed_kph=19),forbidden={'FOLLOW':True}),
        case('不要跟车，也不要靠边停车，先让救援人员通过，然后保持当前车道。',
             s('先让救援人员通过','YIELD',target_text='救援人员'),s('保持当前车道','KEEP_LANE'),forbidden={'FOLLOW':True,'PULL_OVER':True}),
        case('不要靠边停车，先向右变道，随后在本车道停车等候。',
             s('先向右变道','CHANGE_LANE_RIGHT',direction='RIGHT'),s('在本车道停车等候','STOP'),forbidden={'PULL_OVER':True}),
        case('不要停车，先向右变道，再保持车道。',
             s('先向右变道','CHANGE_LANE_RIGHT',direction='RIGHT'),s('再保持车道','KEEP_LANE'),forbidden={'STOP':True}),
    ])
    group('negative_instruction', 'scv1_background_and_explicit_wait', '背景方位、条件中的他人通过和明确让行命令区分；禁止项不扩宽。', [
        case('前车正在右拐。本车不要跟车，保持当前车道。',
             s('保持当前车道','KEEP_LANE'),forbidden={'FOLLOW':True}),
        case('不要向右转，右前方的行人通过后靠边停稳。',
             s('靠边停稳','PULL_OVER',condition='右前方的行人通过后'),forbidden={'TURN_RIGHT':True}),
        case('右前方有行人，本车先让右前方的行人通过，然后靠边停车，禁止向右转。',
             s('先让右前方的行人通过','YIELD',target_text='右前方的行人'),s('靠边停车','PULL_OVER'),forbidden={'TURN_RIGHT':True}),
        case('禁止返回原车道，先设定23公里每小时，在下个路口左转。',
             s('先设定23公里每小时','SET_SPEED',speed_kph=23),s('左转','TURN_LEFT',direction='LEFT',condition='在下个路口'),forbidden={'RETURN_TO_LANE':True}),
    ])

    group('yield_follow', 'scv1_actor_location_not_ego_heading', '目标位于左前方不表示本车左转；同一目标的跟随和让行对照。', [
        case('跟随左前方的黄色轿车，保持12米距离，然后停车。',
             s('跟随左前方的黄色轿车，保持12米距离','FOLLOW',target_text='左前方的黄色轿车',gap_m=12),s('停车','STOP')),
        case('让左前方的黄色轿车先通过，然后停车。',
             s('让左前方的黄色轿车先通过','YIELD',target_text='左前方的黄色轿车'),s('停车','STOP')),
        case('左前方的黄色轿车已经离开，保持当前车道，随后靠边停下。',
             s('保持当前车道','KEEP_LANE'),s('靠边停下','PULL_OVER')),
        case('左前方的黄色轿车已经离开，本车向右换一条车道，随后靠边停下。',
             s('向右换一条车道','CHANGE_LANE_RIGHT',direction='RIGHT'),s('靠边停下','PULL_OVER')),
    ])
    group('yield_follow', 'scv1_wait_or_state_condition', '明确让人先过与仅描述完成条件分开；多个后续任务保留目标和共享条件。', [
        case('先礼让推着手推车的清洁员，然后向左转，最后减速到18公里每小时。',
             s('先礼让推着手推车的清洁员','YIELD',target_text='推着手推车的清洁员'),s('向左转','TURN_LEFT',direction='LEFT'),
             s('最后减速到18公里每小时','SLOW_DOWN',speed_kph=18)),
        case('清洁员通过人行道以后，在前方路口左转。然后减速到18公里每小时。',
             s('在前方路口左转','TURN_LEFT',direction='LEFT',condition='清洁员通过人行道以后'),s('减速到18公里每小时','SLOW_DOWN',speed_kph=18)),
        case('清洁员正朝左侧人行道走，本车保持当前车道，不要跟车。',
             s('保持当前车道','KEEP_LANE'),forbidden={'FOLLOW':True}),
        case('先跟随白色客车，等白色客车驶入停车区后，在路口右转并将车速设为20公里每小时。',
             s('先跟随白色客车','FOLLOW',target_text='白色客车'),
             s('在路口右转','TURN_RIGHT',direction='RIGHT',condition='等白色客车驶入停车区后'),
             s('将车速设为20公里每小时','SET_SPEED',speed_kph=20,condition='等白色客车驶入停车区后')),
    ])
    group('yield_follow', 'expansion_v2_yield_follow_03', '沿用旧Train组：多目标让行与跟随顺序，删除或交换一个明确任务必须改变标签。', [
        case('先给提着行李的旅客让路，随后跟在棕色面包车后面保持13米，再让拄拐杖的老人通过，最后在路边停靠。',
             s('先给提着行李的旅客让路','YIELD',target_text='提着行李的旅客'),s('跟在棕色面包车后面保持13米','FOLLOW',target_text='棕色面包车',gap_m=13),
             s('再让拄拐杖的老人通过','YIELD',target_text='拄拐杖的老人'),s('最后在路边停靠','PULL_OVER')),
        case('先给提着行李的旅客让路，再跟在棕色面包车后面保持13米，最后在路边停靠。',
             s('先给提着行李的旅客让路','YIELD',target_text='提着行李的旅客'),s('再跟在棕色面包车后面保持13米','FOLLOW',target_text='棕色面包车',gap_m=13),s('最后在路边停靠','PULL_OVER')),
        case('旅客和老人都已走上人行道，本车跟在棕色面包车后面保持13米，最后在路边停靠。',
             s('跟在棕色面包车后面保持13米','FOLLOW',target_text='棕色面包车',gap_m=13),s('最后在路边停靠','PULL_OVER')),
        case('先给提着行李的旅客让路，随后让拄拐杖的老人通过，再跟随棕色面包车保持13米，最后在路边停靠。',
             s('先给提着行李的旅客让路','YIELD',target_text='提着行李的旅客'),s('让拄拐杖的老人通过','YIELD',target_text='拄拐杖的老人'),
             s('再跟随棕色面包车保持13米','FOLLOW',target_text='棕色面包车',gap_m=13),s('最后在路边停靠','PULL_OVER')),
    ])

    group('ambiguity', 'scv1_exclusive_or_sequential', '同时互斥要求须澄清；顺序动作、明确禁止后的其他动作不能一律HOLD。', [
        case('要求车辆在同一时刻既并入左边车道，又并入右边车道。',
             s('要求车辆在同一时刻既并入左边车道，又并入右边车道。','HOLD'),confirm=True),
        case('先并到右边车道，完成后再回到原车道。',
             s('先并到右边车道','CHANGE_LANE_RIGHT',direction='RIGHT'),s('再回到原车道','RETURN_TO_LANE',condition='完成后')),
        case('不许左转，但又必须在同一个路口左转，两个要求同时生效。',
             s('不许左转，但又必须在同一个路口左转，两个要求同时生效。','HOLD'),forbidden={'TURN_LEFT':True},confirm=True),
        case('不许右转，但允许把车速设为17公里每小时，之后靠边停车。',
             s('把车速设为17公里每小时','SET_SPEED',speed_kph=17),s('靠边停车','PULL_OVER'),forbidden={'TURN_RIGHT':True}),
    ])
    group('ambiguity', 'scv1_target_choice_or_clear_target', '多个候选未选定须等待说明；唯一目标和明确非跟随指令不应误判为歧义。', [
        case('跟着救护车还是校车都行，但我还没决定选哪一辆，先不要执行跟车。',
             s('跟着救护车还是校车都行，但我还没决定选哪一辆，先不要执行跟车。','HOLD'),forbidden={'FOLLOW':True},confirm=True),
        case('两辆出租车都叫前车，我没说选哪一辆，先等待我说明。',
             s('两辆出租车都叫前车，我没说选哪一辆，先等待我说明。','HOLD'),confirm=True),
        case('不要跟车，先把车速设为18公里每小时，然后在路边停靠。',
             s('先把车速设为18公里每小时','SET_SPEED',speed_kph=18),s('在路边停靠','PULL_OVER'),forbidden={'FOLLOW':True}),
        case('跟随右前方车身印有邮政标记的货车，保持14米。',
             s('跟随右前方车身印有邮政标记的货车，保持14米','FOLLOW',target_text='右前方车身印有邮政标记的货车',gap_m=14)),
    ])
    group('ambiguity', 'expansion_v2_ambiguity_04', '沿用旧Train组：同时精确冲突与分阶段间距不同；禁止跟车与必须跟车冲突。', [
        case('跟车间距在整个行驶过程中必须一直精确等于6米，同时又必须一直精确等于16米。',
             s('跟车间距在整个行驶过程中必须一直精确等于6米，同时又必须一直精确等于16米。','HOLD'),confirm=True),
        case('先跟随前面的厢式客车保持6米；雨势加大后，仍跟随前面的厢式客车，但将间距改为16米。',
             s('先跟随前面的厢式客车保持6米','FOLLOW',target_text='前面的厢式客车',gap_m=6),
             s('仍跟随前面的厢式客车，但将间距改为16米','FOLLOW',target_text='前面的厢式客车',gap_m=16,condition='雨势加大后')),
        case('不要跟车，但必须立刻跟随前车并保持6米，两个要求同时生效。',
             s('不要跟车，但必须立刻跟随前车并保持6米，两个要求同时生效。','HOLD'),forbidden={'FOLLOW':True},confirm=True),
        case('不用改变跟车距离，继续跟随前面的厢式客车，保持6米。',
             s('继续跟随前面的厢式客车，保持6米','FOLLOW',target_text='前面的厢式客车',gap_m=6)),
    ])
    return draft_packets(seeds, proposals), groups


def coverage(rows, *, drafts=False):
    actions = {key: dict(steps=0, evidence=set(), groups=set()) for key in ACTION_ZH}
    lengths, confirmations = Counter(), Counter()
    for row in rows:
        label = row['proposal']['label'] if drafts else row['label']
        lengths[len(label['steps'])] += 1
        confirmations[str(label['requires_confirmation']).lower()] += 1
        for step in label['steps']:
            item = actions[step['action']]
            item['steps'] += 1
            item['evidence'].add(step['evidence'])
            item['groups'].add(row['group_id'])
    return dict(rows=len(rows), step_lengths=dict(lengths), confirmations=dict(confirmations), actions={key: dict(
        steps=value['steps'], distinct_evidence=len(value['evidence']),
        number_masked_evidence=len({re.sub(r'\d+(?:\.\d+)?', '#', text) for text in value['evidence']}),
        groups=len(value['groups'])) for key, value in actions.items()})


def signature(label):
    # Review triage only: identical structure is not proof of semantic duplication.
    return canonical_hash(dict(actions=[step['action'] for step in label['steps']],
        prohibited=label['prohibited_actions'], confirmation=label['requires_confirmation'],
        condition_present=[step['condition'] is not None for step in label['steps']],
        target_present=[step['target_text'] is not None for step in label['steps']],
        directions=[step['direction'] for step in label['steps']]))


def check_materials(rows, previous, protected_texts, protected_groups):
    known_ids = {row['sample_id'] for row in previous}
    known_texts = {text_hash(row['source_text']) for row in previous}
    seen_ids, seen_texts = set(), set()
    for row in rows:
        digest = text_hash(row['source_text'])
        if (row['sample_id'] in known_ids | seen_ids or digest in known_texts | seen_texts | protected_texts
                or row['group_id'] in protected_groups):
            raise ValueError('duplicate or protected text/group; do not rename an ID to bypass isolation')
        if row['label'] is not None or row['reviews'] or row['split'] != 'UNASSIGNED' or row['annotation_status'] != 'DRAFT':
            raise ValueError('new contrast output must remain unapproved and unassigned')
        seen_ids.add(row['sample_id']); seen_texts.add(digest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--existing-release', type=Path, required=True)
    parser.add_argument('--token-audit', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if not baseline_guard()['passed']:
        raise ValueError('baseline guard failed')
    release = args.existing_release.resolve(strict=True)
    _, version, _ = verify_release(release, sha(release / 'manifest.json'), args.token_audit)
    previous = load_jsonl(release / 'reviewed_rows.jsonl')
    test, supplement = release / 'test_exclusion_registry.json', release / 'supplemental_exclusion_registry.json'
    protected = external_registry(test) | external_registry(supplement, role='INDEPENDENT_VALIDATION')
    rows, groups = build_batch()
    check_materials(rows, previous, protected, registry_groups(test) | registry_groups(supplement))
    old_groups = {r['group_id']: dict(family=r['semantic_family'], split=r['split']) for r in previous}
    old_signatures = defaultdict(set)
    for row in previous:
        old_signatures[signature(row['label'])].add(row['group_id'])
    for key, item in groups.items():
        if key in old_groups and old_groups[key]['family'] != item['family']:
            raise ValueError('reused group cannot change semantic family')
        item['existing_group'] = old_groups.get(key)
        related = set().union(*(old_signatures[signature(r['proposal']['label'])] for r in rows if r['group_id'] == key))
        item['structurally_related_existing_groups'] = {g: old_groups[g] for g in sorted(related)}
        item['review_status'] = 'PENDING_OWNER_LABEL_AND_CROSS_BATCH_GROUP_REVIEW'
    if not {'expansion_v2_yield_follow_03','expansion_v2_ambiguity_04'} <= set(old_groups):
        raise ValueError('expected existing reference groups; do not silently invent replacement groups')
    output = output_directory(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'draft_review_queue.jsonl').open('x', encoding='utf-8', newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    (output / 'draft_review_sheet.md').write_text(draft_markdown(rows), encoding='utf-8', newline='\n')
    lines = ['# 语义对照组待审入口', '',
        '72条、18组均未批准，不分配Train/Val，不生成新Test。逐条参数和条件见[完整复核表](draft_review_sheet.md)。',
        '本批属于已看过旧Test结果后的开发补充。旧Test不进入训练，但不再作为后续调参后的独立效果证明。',
        '结构相同仅是分组排查提示，不是判定所有HOLD或相同动作链必须合成一组。', '']
    for group_id, item in groups.items():
        lines += [f'## {group_id}', '', item['focus'], '', '旧组：' + str(item['existing_group']), '']
        for row in rows:
            if row['group_id'] == group_id:
                actions = ' → '.join(step['action'] for step in row['proposal']['label']['steps'])
                lines.append(f"- [{row['sample_id']}](draft_review_sheet.md#{row['sample_id'].lower()})：{row['source_text']}（{actions}）")
        lines += ['', '- [ ] 已核对每句及跨批分组，未将已曝光Test简单改数字或换目标导入。', '']
    (output / 'review_index.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    (output / 'group_review.json').write_text(json.dumps(groups, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    report = draft_summary(rows)
    report.update(scope='TEST_INFORMED_DEVELOPMENT_CONTRAST_DRAFTS_NOT_TRAINING_OR_NEW_TEST',
        reference_dataset_version=version, reference_release_manifest_sha256=sha(release / 'manifest.json'),
        group_count=len(groups), reused_existing_groups=[key for key in groups if key in old_groups],
        current_approved_train_coverage=coverage([r for r in previous if r['split'] == 'train']),
        proposed_draft_coverage=coverage(rows, drafts=True), split_assignment='UNASSIGNED_PENDING_REVIEW',
        old_test_now_known_regression=True, fresh_independent_final_test_required=True, new_final_test_created=False,
        model_inference_run=False, training_started=False, semantic_independence_verified=False,
        builder_lf_utf8_sha256=hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode('utf-8')).hexdigest())
    report['artifact_sha256'] = {p.name: sha(p) for p in sorted(output.iterdir())}
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps({k: report[k] for k in ('draft_rows','approved_rows','families','group_count','reused_existing_groups','training_started')}))


if __name__ == '__main__':
    main()
