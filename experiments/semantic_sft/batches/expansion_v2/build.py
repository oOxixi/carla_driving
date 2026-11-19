"""216 constructed drafts, never Teacher evidence or automatic approvals."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from qwen_service.task_understanding import _example_step as step
from experiments.semantic_sft.data import PLAN, audit_rows, baseline_guard, load_jsonl, output_directory, text_hash
from experiments.semantic_sft.prepare import external_registry, registry_groups
from experiments.semantic_sft.proposals import draft_packets,draft_markdown,draft_summary

SPECS={
 'lane_choice':[
  ['KEEP_LANE','CHANGE_LANE_LEFT','FOLLOW'],['SLOW_DOWN','CHANGE_LANE_RIGHT','SET_SPEED'],
  ['CHANGE_LANE_LEFT','PULL_OVER'],['STOP','CHANGE_LANE_RIGHT'],['SET_SPEED','TURN_LEFT','CHANGE_LANE_LEFT'],
  ['FOLLOW','TURN_RIGHT','KEEP_LANE'],['CHANGE_LANE_RIGHT','FOLLOW','TURN_LEFT','PULL_OVER'],['KEEP_LANE','SET_SPEED','TURN_RIGHT']],
 'conditional_resume':[
  ['STOP','SET_SPEED','FOLLOW'],['SLOW_DOWN','KEEP_LANE','PULL_OVER'],['FOLLOW','STOP','SET_SPEED'],
  ['YIELD','SET_SPEED','CHANGE_LANE_LEFT'],['SET_SPEED','STOP','PULL_OVER'],['SLOW_DOWN','CHANGE_LANE_RIGHT','FOLLOW'],
  ['KEEP_LANE','SLOW_DOWN','FOLLOW'],['FOLLOW','YIELD','KEEP_LANE']],
 'overtake_return':[
  ['AVOID_OBSTACLE','STOP'],['YIELD','AVOID_OBSTACLE','RETURN_TO_LANE'],['FOLLOW','AVOID_OBSTACLE','SET_SPEED','RETURN_TO_LANE'],
  ['STOP','AVOID_OBSTACLE','RETURN_TO_LANE'],['SLOW_DOWN','AVOID_OBSTACLE','FOLLOW'],['AVOID_OBSTACLE','RETURN_TO_LANE','PULL_OVER'],
  ['AVOID_OBSTACLE','SET_SPEED','PULL_OVER'],['KEEP_LANE','AVOID_OBSTACLE','RETURN_TO_LANE','FOLLOW']],
 'negative_instruction':[
  ['STOP','FOLLOW'],['YIELD','KEEP_LANE','FOLLOW'],['FOLLOW','PULL_OVER'],['SLOW_DOWN','FOLLOW','STOP'],
  ['SLOW_DOWN','CHANGE_LANE_LEFT','PULL_OVER'],['FOLLOW','KEEP_LANE','SET_SPEED'],['AVOID_OBSTACLE','CHANGE_LANE_LEFT','KEEP_LANE'],['CHANGE_LANE_RIGHT','SET_SPEED']],
 'yield_follow':[
  ['FOLLOW','YIELD','FOLLOW'],['YIELD','CHANGE_LANE_RIGHT','FOLLOW'],['YIELD','FOLLOW','YIELD','PULL_OVER'],
  ['SLOW_DOWN','YIELD','FOLLOW','CHANGE_LANE_LEFT'],['YIELD','FOLLOW','RETURN_TO_LANE'],['FOLLOW','YIELD','CHANGE_LANE_LEFT','KEEP_LANE'],
  ['YIELD','STOP','FOLLOW'],['FOLLOW','YIELD','SET_SPEED']],
}
CONDITIONS=[{1:'绿灯亮起后'},{1:'确认前方路段清空后'},{1:'前车停稳后',2:'道路恢复畅通后'},
 {1:'确认行人通过后'},{1:'红灯亮起时',2:'路边停靠位置空出后'},{1:'右侧安全间隙出现后'},
 {1:'进入雾区后'},{1:'斑马线有人时',2:'确认行人离开后'}]
NEG=[['CHANGE_LANE_LEFT'],['CHANGE_LANE_RIGHT'],['TURN_LEFT'],['TURN_RIGHT'],['FOLLOW'],['PULL_OVER'],['RETURN_TO_LANE'],['CHANGE_LANE_LEFT','TURN_RIGHT']]
NEG_TEXT={'CHANGE_LANE_LEFT':'不要向左变道','CHANGE_LANE_RIGHT':'禁止向右变道','TURN_LEFT':'不要左转','TURN_RIGHT':'禁止右转',
          'FOLLOW':'不要跟车','PULL_OVER':'禁止靠边停车','RETURN_TO_LANE':'不要返回原车道'}


def atom(action,v,j,condition=None):
    speed=16+v*3+j
    target=['白色厢式货车','蓝色轿车','前方小客车','右前方的摩托车','前方小货车'][(v+j)%5]
    person=['斑马线上的行人','右侧骑行者','推行自行车的人','路边准备横穿的行人','前方行人'][(v+j)%5]
    obstacle=['停在路中的货车','施工护栏','占道车辆','前方路障','故障轿车'][(v+j)%5]
    if action=='FOLLOW':
        text=f'跟随{target}并保持{4+v}米距离'
        item=step(text,action,target_text=target,gap_m=4+v)
    elif action=='YIELD':
        item=step(f'让{person}先通过',action,target_text=person)
    elif action=='AVOID_OBSTACLE':
        side='左' if v%2==0 else '右'
        item=step(f'从{side}侧绕过{obstacle}',action,target_text=obstacle,direction='LEFT' if side=='左' else 'RIGHT')
    elif action in ['SET_SPEED','SLOW_DOWN']:
        text=f'将车速设为{speed}公里每小时' if action=='SET_SPEED' else f'减速至{speed}公里每小时'
        item=step(text,action,speed_kph=speed)
    elif action.startswith('CHANGE_LANE_'):
        side='左' if action.endswith('LEFT') else '右'
        item=step(f'向{side}变道',action,direction='LEFT' if side=='左' else 'RIGHT')
        condition=condition or ('左侧安全间隙足够时' if side=='左' else '右侧安全间隙足够时')
    elif action in ['TURN_LEFT','TURN_RIGHT']:
        side='左' if action=='TURN_LEFT' else '右'
        item=step(f'在前方路口向{side}转',action,direction='LEFT' if side=='左' else 'RIGHT')
    else:
        text={'KEEP_LANE':['保持当前车道行驶','沿本车道继续行驶','留在所在车道行驶','继续保持当前车道','维持本车道行驶'],
              'STOP':['停车等候','停下等待','把车停住','停车等待','停稳车辆'],
              'PULL_OVER':['靠边停车','在路边停好','靠边停稳','将车靠边停下','到路边停车'],
              'RETURN_TO_LANE':['返回原车道','回到原来的车道','并回原车道','返回先前车道','回原来的行驶车道']}[action][v]
        item=step(text,action)
    item['condition']=condition
    return (condition or '')+item['evidence'],item


def ambiguity(i,v):
    values=[
        f'按照之前那条路线继续，但我还没有给出之前的路线，先保持{18+v}公里每小时的意图待确认',
        ['同时向左转和向右转','既左转又右转，两者同时执行','在同一时刻左转并右转','同时执行向左转与向右转','一边左转一边右转'][v],
        ['跟着那辆车继续，具体哪辆我还没有说明','照着它的方向跟车，但还没说它是哪辆','先跟随那辆，目标身份还没确定','跟上那一辆车，具体指谁还不确定','按照那辆车走，我没有指出是哪辆'][v],
        f'与前车的距离必须同时恰好是{4+v}米和{9+v}米',
        ['停车并同时保持车辆向前行驶','同一时刻停稳车辆又继续前进','把车停住但要求同时继续行驶','保持停车状态并同时向前行驶','同时停稳和继续向前开'][v],
        ['回到原车道，但又禁止返回原车道','返回原车道与不要返回原车道这两个要求同时执行','请回原车道，同时不许返回原车道','先要求回原车道，又要求不能返回原车道','返回原来车道，但禁止执行返回原车道'][v],
        ['请加速并同时保持车速不变','提升速度，但速度数值不能改变','提高车速同时维持当前速度数值'],
        ['到那个地方停车，位置我还没有告诉你','请在指定地点停下，但具体地点尚未说明','抵达那个位置后停车，尚未指定是哪里'],
    ]
    text=values[i][v] if i>=6 else values[i]
    label={'steps':[step(text,'HOLD')],'prohibited_actions':{'RETURN_TO_LANE':True} if i==5 else {},'requires_confirmation':True}
    return text,label


def build_batch():
    seeds,proposals,cohorts=[],[],{}
    families=PLAN['data_smoke_thresholds']['required_families']
    for family in families:
        for i in range(8):
            cohort='train' if i<6 else 'val'
            group=f'expansion_v2_{family}_{i+1:02d}'
            if family=='ambiguity' and i==2:group='unspecified_vehicle_reference_01'
            if family=='ambiguity' and i==6:group='contradictory_speed_02'
            cohorts[group]=cohort
            for v in range(5 if cohort=='train' else 3):
                if family=='ambiguity':
                    text,label=ambiguity(i,v)
                else:
                    pieces,steps=[],[]
                    for j,action in enumerate(SPECS[family][i]):
                        condition=CONDITIONS[i].get(j) if family=='conditional_resume' else None
                        piece,item=atom(action,v,j,condition)
                        pieces.append(piece);steps.append(item)
                    forbidden=NEG[i] if family=='negative_instruction' else []
                    prefix='，'.join(NEG_TEXT[a] for a in forbidden)
                    text=(prefix+'，' if prefix else '')+['，然后','，接着','；随后','，再','，之后'][v].join(pieces)
                    label={'steps':steps,'prohibited_actions':{a:True for a in forbidden},'requires_confirmation':False}
                identifier=f'EXP_V2_{family}_{i+1:02d}_{v+1:02d}'
                seeds.append({'sample_id':identifier,'source_text':text,'semantic_family':family,'group_id':group})
                proposals.append({'sample_id':identifier,'source_text':text,'label':label,'contract_gap':False,
                    'review_notes':['AI模板构造的待审数据，不是Qwen推理、Teacher采集或真实闭环证据。',
                                    '同一模板的词面/参数变体保留同组；新组的跨批语义关系还需负责人审核。']})
    return draft_packets(seeds,proposals),cohorts


def review_index(rows,cohorts):
    lines=['# 扩充批次分组复核入口','','216条均为待审草稿，不是Teacher采集或已批准金标。',
           '按48个模板槽位逐组查看；每组3或5条变体都需核对。拟定Train/Val在看模型成绩之前声明，尚未冻结。',
           '特别核对跨批近义组：若同一语义模板被拆成两个ID，必须合组并同侧分配，不能只为凑206/51保留当前分组。',
           '下列动作链仅是该组第一条的概览；逐条目标、参数、条件、禁止事项和证据见[完整复核表](draft_review_sheet.md)。','']
    for group,cohort in cohorts.items():
        members=[r for r in rows if r['group_id']==group]
        label=members[0]['proposal']['label']
        lines.extend([f'## {group}','','拟定集合：'+cohort+'；动作链候选：'+
                      ' → '.join(s['action'] for s in label['steps'])+'。',''])
        for row in members:
            lines.append(f"- [{row['sample_id']}](draft_review_sheet.md#{row['sample_id'].lower()})：{row['source_text']}")
        lines.extend(['','- [ ] 已逐条核对，并检查与旧批次/保护集的语义近重复；有异议则保留待审。',''])
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--existing-split',type=Path,required=True)
    parser.add_argument('--test-registry',type=Path,required=True)
    parser.add_argument('--supplemental-registry',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if not baseline_guard()['passed']:raise ValueError('baseline guard failed')
    previous=load_jsonl(args.existing_split)
    test=external_registry(args.test_registry)
    supplement=external_registry(args.supplemental_registry,role='INDEPENDENT_VALIDATION')
    groups=registry_groups(args.test_registry)|registry_groups(args.supplemental_registry)
    audit=audit_rows(previous,external_protected=test,supplemental_protected=supplement,protected_groups=groups)
    if audit['issues'] or len(previous)!=41:raise ValueError('expected the unchanged 41 approved candidate records')
    rows,cohorts=build_batch()
    known={text_hash(r['source_text']) for r in previous}
    known_ids={r['sample_id'] for r in previous}
    planned={r['group_id']:r['split'] for r in previous}
    for row in rows:
        if row['sample_id'] in known_ids or text_hash(row['source_text']) in known|test|supplement or row['group_id'] in groups:
            raise ValueError('draft overlaps protected material')
        if row['group_id'] in planned and planned[row['group_id']]!=cohorts[row['group_id']]:
            raise ValueError('existing paraphrase group would leak across splits')
    assert len(rows)==len({text_hash(r['source_text']) for r in rows})==216
    counts=Counter(cohorts[r['group_id']] for r in rows)
    assert counts=={'train':180,'val':36}
    output=output_directory(args.output_dir);output.mkdir(parents=True,exist_ok=False)
    with (output/'draft_review_queue.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
        for row in rows:stream.write(json.dumps(row,ensure_ascii=False)+'\n')
    (output/'draft_review_sheet.md').write_text(draft_markdown(rows),encoding='utf-8',newline='\n')
    (output/'review_index.md').write_text(review_index(rows,cohorts),encoding='utf-8',newline='\n')
    (output/'planned_groups.json').write_text(json.dumps(cohorts,indent=2),encoding='utf-8',newline='\n')
    report=draft_summary(rows)
    report.update(scope='CONSTRUCTED_EXPANSION_DRAFTS_NOT_APPROVED_OR_TEACHER_DATA',planned_new_counts=dict(counts),
                  planned_total_counts={k:audit['splits'][k]+counts[k] for k in ['train','val']},
                  template_slots=48,reused_existing_groups=2,new_proposed_groups=46,semantic_independence_verified=False,
                  existing_split_sha256=hashlib.sha256(args.existing_split.read_bytes()).hexdigest())
    report['input_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [args.existing_split,args.test_registry,args.supplemental_registry]}
    report['builder_lf_utf8_sha256']=hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode('utf-8')).hexdigest()
    report['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps(report))


if __name__=='__main__':main()
