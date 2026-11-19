"""Triage public Train references and author a small, explicitly unapproved review batch."""
import argparse
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re

from .audit_public_slu import records
from .batches.boundaries_v2.build import step
from .data import output_directory, text_hash
from .proposals import draft_packets, draft_markdown
from .release import write_rows


def proposals():
    # Original Train texts, not paraphrases or copied evaluation commands.
    return [
        ('plain_turn', 'lane_choice', '向左转', [step('TURN_LEFT', '向左转', direction='LEFT')]),
        ('plain_turn', 'lane_choice', '嗯向右转', [step('TURN_RIGHT', '向右转', direction='RIGHT')]),
        ('distance_gate', 'conditional_resume', '九百米后左转',
            [step('TURN_LEFT', '左转', direction='LEFT', condition='九百米后')]),
        ('distance_gate', 'conditional_resume', '前方四百五十米右转',
            [step('TURN_RIGHT', '右转', direction='RIGHT', condition='前方四百五十米')]),
        ('junction_gate', 'conditional_resume', '走到底右转',
            [step('TURN_RIGHT', '右转', direction='RIGHT', condition='走到底')]),
        ('junction_gate', 'conditional_resume', '前方在十字路口右转',
            [step('TURN_RIGHT', '右转', direction='RIGHT', condition='前方在十字路口')]),
        ('junction_gate', 'conditional_resume', '在第二个红绿灯路口左转',
            [step('TURN_LEFT', '左转', direction='LEFT', condition='在第二个红绿灯路口')]),
        ('junction_gate', 'conditional_resume', '下一个红绿灯路口左转',
            [step('TURN_LEFT', '左转', direction='LEFT', condition='下一个红绿灯路口')]),
        ('junction_gate', 'conditional_resume', '将在前方路口左转',
            [step('TURN_LEFT', '左转', direction='LEFT', condition='前方路口')]),
        ('repeated_turn', 'multi_step', '左转然后左转',
            [step('TURN_LEFT', '左转', direction='LEFT'),
             step('TURN_LEFT', '然后左转', direction='LEFT')]),
        ('junction_gate', 'conditional_resume', '你好红绿灯路口左转',
            [step('TURN_LEFT', '左转', direction='LEFT', condition='红绿灯路口')]),
        ('yield_background', 'yield_follow', '十米处有违章拍照请注意礼让行人',
            [step('YIELD', '礼让行人', target_text='行人')]),
    ]


def triage_tags(row):
    """Review routing only: none of these tags is a semantic training label."""
    text = row['source_text']
    tags = []
    if not row['upstream_frames']:
        tags.append('NO_UPSTREAM_DRIVING_LABEL')
    if re.search(r'=>|intent=|车载控制:intent', text):
        tags.append('ANNOTATION_TEXT_IN_SOURCE')
    if re.search('闭锁|关窗|关天窗|音随车速|音量|环视退出|窗帘|空调|舒享|转向灯|停车灯', text):
        tags.append('CABIN_OR_FEATURE_TRIGGER_NOT_VEHICLE_SPEED_OR_TURN')
    if re.search('巡航|ACC|ALC|NOA|LIM|变道辅助|换道辅助|变道确认|变道提醒|变道警示|自动停车|停车助手|自动泊车', text, re.I):
        tags.append('ASSIST_FEATURE_OR_SETTING_REQUIRES_SEPARATE_CAPABILITY')
    if any(f['domain'] == '地图' for f in row['upstream_frames']) or '停车场' in text:
        tags.append('NAVIGATION_POI_NOT_AUTOMATIC_PARK_ACTION')
    if re.search('歌曲|歌单|向左转向右转|左转右转小池', text):
        tags.append('CONTENT_TITLE_OR_MIXED_DOMAIN_REVIEW')
    if ('恢复' in text and '巡航' in text and any(
            s.get('name') == '操作' and s.get('value') == '关闭'
            for f in row['upstream_frames'] for s in f['slots'])):
        tags.append('UPSTREAM_OPERATION_CONTRADICTS_SOURCE_REVIEW')
    if not tags:
        tags.append('OTHER_UNRESOLVED_REVIEW')
    return tags


def unresolved_cases(by_hash):
    cases = {
        '前方路口左转走左侧三车道': '指定多条/序数车道不能降格为一次CHANGE_LANE_LEFT；需先澄清车道选择语义。',
        '前方红绿灯右转进入翠屏西路前走最右侧车道': '转弯、进入指定道路与车道选择混合，不能靠删除后半句获得完整解析标签。',
        '开始导航前方调头然后一百五十米左转': '包含导航功能与掉头；当前14动作没有对应UTURN，不能换成普通左转。',
        '这里还能左转吗': '询问道路许可/可行性，不能等同要求立刻左转；需场景关联或确认口径。',
        '打开LIM并设置最高车速为30公里每小时': '限速上界不等于请求立即开到30；当前只有绝对设速字段，不能抹掉限定词。',
        '设置自适应巡航车距为2档': '2档不是2米；原始档位语义不能硬填gap_m。',
        '设置ACC跟车距为4': '原句未明确4的单位，且原语义为空；不能推断4米。',
        '请给我把巡航调整快到60公里': '原文公里不是公里每小时；缺少速度单位且有巡航功能语义，不能直接补60km/h。',
        '限速偏移设置为负10公里每小时': '负10为限速偏移，不是绝对目标车速；不能截成0或改作减速10。',
        '替我把巡航恢复': '原句恢复与上游关闭标签相冲突；不把错误上游槽位当监督，也不编造恢复车速。',
        '打开智能变道辅助 => 1:车载控制:intent=车身控制,功能=智慧巡航,子功能=自动变道辅助,操作=打开':
            '输入含疑似答案串；保持污染隔离，不把清理后原句悄悄当新样本。',
    }
    result = []
    for text, reason in cases.items():
        matches = by_hash.get(text_hash(text), [])
        if not matches:
            raise ValueError('expected original unresolved case is missing: ' + text)
        result.append(dict(source_text=text, references=matches, reason=reason,
            current_task_label=None, status='ISOLATED_FOR_CONTRACT_OR_ANNOTATION_REVIEW'))
    return result


def verify_manifest(path):
    manifest = json.loads(path.read_text(encoding='utf-8'))
    for item in manifest['artifacts'] + manifest['implementation'] + manifest['scoring_sources']:
        if hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('sealed input changed: ' + item['path'])


def build_packets(by_hash, protected, previous):
    seeds, labels, provenance, neighbors = [], [], [], []
    old_texts = {text_hash(r['source_text']) for r in previous}
    for i, (group, family, text, steps) in enumerate(proposals(), 1):
        digest = text_hash(text)
        if digest in protected or digest in old_texts:
            raise ValueError('proposal overlaps protected or existing reviewed text: ' + text)
        matches = by_hash.get(digest, [])
        if not matches or any(r['dataset'] != 'mivs' or r['member'] != 'aispeech/train/null_data/null.json'
                              or r['source_text'] != text or r['upstream_frames'] for r in matches):
            raise ValueError('expected exact original, unlabeled public Train provenance: ' + text)
        identifier = f'PUBLIC_DRIVING_V1_{i:03d}'
        seeds.append(dict(sample_id=identifier, source_text=text, semantic_family=family,
            group_id='public_driving_v1_' + group))
        labels.append(dict(sample_id=identifier, source_text=text, contract_gap=False,
            label=dict(steps=steps, prohibited_actions={}, requires_confirmation=False),
            review_notes=[
                '原句来自MIVS Train/null_data；原标注为空，不是经验证的负类或Teacher驾驶真值。',
                '当前标签为AI新草稿；需负责人逐条核对，不是本次继续所隐含批准的标签。',
                '距离/路口是转弯前提，不是跟车gap_m，也不能立即在当前帧转弯。',
                '行人例子的十米处拍照是背景，不自动等同行人位置或让行触发距离。',
                '尚有MIVS数据授权范围及跨批近义组审计阻塞；即使标签获批也不直接开训。']))
        provenance.append(dict(sample_id=identifier, source_text=text, source_kind='PUBLIC_MIVS_TRAIN_TEXT',
            references=matches, original_upstream_labels_empty=True, label_author='AI_ASSISTANT',
            automatic_group_is_only_a_review_suggestion=True))
        ranked = sorted(previous, key=lambda r: SequenceMatcher(None, text, r['source_text']).ratio(), reverse=True)[:3]
        neighbors.append(dict(sample_id=identifier, same_semantic_family_groups=sorted({r['group_id'] for r in previous
            if r['semantic_family'] == family}), nearest_existing=[dict(sample_id=r['sample_id'],
                source_text=r['source_text'], group_id=r['group_id'], split=r['split'],
                lexical_similarity=round(SequenceMatcher(None, text, r['source_text']).ratio(), 4)) for r in ranked],
            status='ADVISORY_NOT_PROOF_OF_GROUP_INDEPENDENCE'))
    packets = draft_packets(seeds, labels)
    for packet in packets:
        packet['origin']['kind'] = 'EXTRACTED_EXISTING_TRAIN_REQUIRES_REVIEW'
    return packets, provenance, neighbors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-dir', type=Path, required=True)
    parser.add_argument('--release-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    verify_manifest(args.audit_dir / 'artifact_manifest.json')
    out = output_directory(args.output_dir)
    source = args.audit_dir / 'driving_lexeme_review.jsonl'
    rows = records(source.read_bytes())
    by_hash = defaultdict(list)
    for row in rows:
        if text_hash(row['source_text']) != row['normalized_text_sha256']:
            raise ValueError('text/hash mismatch in audit input')
        by_hash[row['normalized_text_sha256']].append(row)
    protected = {r['normalized_text_sha256'] for r in records((args.audit_dir / 'eval_exclusion_hashes.jsonl').read_bytes())}
    previous_path = args.release_dir / 'reviewed_rows.jsonl'
    previous = records(previous_path.read_bytes())
    packets, provenance, neighbors = build_packets(by_hash, protected, previous)
    unresolved = unresolved_cases(by_hash)
    selected = {text_hash(p['source_text']) for p in packets}
    triage = [dict(source_text=rs[0]['source_text'], normalized_text_sha256=digest,
        references=rs, review_tags=triage_tags(rs[0]),
        selected_for_label_review=digest in selected,
        selection_kind='AI_DRAFT_NOT_APPROVED' if digest in selected else 'REVIEW_ROUTING_NOT_FINAL_REJECTION',
        current_task_label=None) for digest, rs in by_hash.items()]
    out.mkdir(parents=True)
    for filename, values in [('triage.jsonl', triage), ('draft_review_queue.jsonl', packets),
                             ('source_provenance.jsonl', provenance), ('cross_batch_neighbors.jsonl', neighbors),
                             ('unresolved_contract_cases.jsonl', unresolved)]:
        write_rows(out / filename, values)
    (out / 'REVIEW.md').write_text(draft_markdown(packets), encoding='utf-8')
    report = dict(scope='PUBLIC_TRAIN_TRIAGE_AND_AI_DRAFTS_NOT_TRAINING_RELEASE',
        original_rows=len(rows), unique_texts=len(by_hash), draft_rows=len(packets),
        isolated_contract_or_annotation_examples=len(unresolved),
        group_suggestions=dict(Counter(p['group_id'] for p in packets)),
        review_tags_overlap=dict(Counter(tag for r in triage for tag in r['review_tags'])),
        input_manifest_sha256=hashlib.sha256((args.audit_dir / 'artifact_manifest.json').read_bytes()).hexdigest(),
        previous_reviewed_sha256=hashlib.sha256(previous_path.read_bytes()).hexdigest(),
        input_path=str(source.resolve()), input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        exclusion_registry_path=str((args.audit_dir / 'eval_exclusion_hashes.jsonl').resolve()),
        exclusion_registry_sha256=hashlib.sha256((args.audit_dir / 'eval_exclusion_hashes.jsonl').read_bytes()).hexdigest(),
        approved_rows=0, ready_for_training=False, production_changed=False, training_started=False,
        blockers=['Owner label and cross-batch group approval missing',
            'MIVS data-specific permission scope not independently established',
            'No new frozen release, no independent validation result'],
        limits=['Triage tags are mechanical review routing, not a manual verdict on every utterance.',
            'The selected 12 are driving-language texts, not recorded driver-to-vehicle commands; role/audio unverified.',
            'Small turn-heavy batch does not close complex conditional, prohibition or emergency coverage gaps.'])
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    document = Path(__file__).with_name('PUBLIC_DRIVING_REVIEW_20261108.md')
    (out / 'README.md').write_bytes(document.read_bytes())
    manifest = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(out.iterdir()) if p.is_file()}
    for path in (Path(__file__), document, Path(__file__).parent / 'proposals.py',
                 Path(__file__).parent / 'data.py',
                 Path(__file__).parent / 'batches/boundaries_v2/build.py',
                 Path(__file__).parent / 'tests/test_public_driving_review.py'):
        manifest[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'artifact_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
