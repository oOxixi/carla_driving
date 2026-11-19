"""Conservative language-to-track evidence and independent plan verification."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import re
from typing import Any, Mapping


@dataclass(frozen=True)
class TargetQuery:
    target_class: str | None = None
    subtype: str | None = None
    side: str | None = None
    longitudinal: str | None = None
    distance_relation: str | None = None
    max_distance_m: float | None = None
    visual_description: bool = False
    same_lane: bool = False


@dataclass(frozen=True)
class SceneEvidence:
    request_id: str
    frame_id: int
    query: TargetQuery
    candidate_ids: tuple[str, ...]
    status: str
    reason: str
    resolved_id: str | None = None
    uncertain_geometry: bool = False

    def to_dict(self):
        return asdict(self)


def parse_target_query(text: str, intent: str = '') -> TargetQuery | None:
    text = text.lower()
    if intent.upper() not in {'FOLLOW', 'AVOID_OBSTACLE', 'CHANGE_LANE', 'YIELD'}:
        return None
    match = re.search(r'行人|pedestrian|公交车|巴士|bus|卡车|货车|truck|出租车|taxi|自行车|骑行者|cyclist|车辆|汽车|轿车|前车|那辆车|这辆车|车(?!道|速|辆)|vehicle|\bcar\b|障碍物|障碍|路障|锥桶|obstacle', text)
    if not match:
        return None
    word = match.group()
    category = ('pedestrian' if word in ('行人', 'pedestrian') else
                'cyclist' if word in ('自行车', '骑行者', 'cyclist') else
                'obstacle' if word in ('障碍物', '障碍', '路障', '锥桶', 'obstacle') else 'vehicle')
    subtype = ('bus' if word in ('公交车', '巴士', 'bus') else
               'truck' if word in ('卡车', '货车', 'truck') else
               'taxi' if word in ('出租车', 'taxi') else None)
    # Only direction phrases immediately modifying the object are target location.
    prefix = text[max(0, match.start()-16):match.start()]
    position = re.search(r'(左前|右前|左侧|右侧|左边|右边|左方|右方|前方|前面|后方|后面|left|right|ahead|behind)(?:那辆|这辆|一辆|那位|这位|较近的|最近的|的|\s)*$', prefix)
    after = re.match(r'(?:在|位于)(左前|右前|左侧|右侧|左边|右边|前方|后方)', text[match.end():])
    pos = position.group(1) if position else after.group(1) if after else ('前方' if word == '前车' else '')
    side = 'LEFT' if '左' in pos or pos == 'left' else 'RIGHT' if '右' in pos or pos == 'right' else None
    longitudinal = 'AHEAD' if pos in ('左前', '右前', '前方', '前面', 'ahead') else 'BEHIND' if pos in ('后方', '后面', 'behind') else None
    relation = 'NEAREST' if re.search(r'最近|closest|nearest', prefix) else 'NEAR' if re.search(r'较近|比较近|靠近|nearer', prefix) else None
    meters = re.search(r'(\d+(?:\.\d+)?)\s*(?:米|m\b)', prefix)
    visual = bool(subtype or re.search(r'白色|黑色|红色|蓝色|黄色|绿色|白车|黑车|红车|蓝车|黄色|white|black|red|blue|yellow|green|suv', text))
    return TargetQuery(category, subtype, side, longitudinal, relation, float(meters.group(1)) if meters else None, visual, bool(re.search(r"同车道|本车道|当前车道|same lane", text)))


def _geometry_reliable(obj: Mapping[str, Any]) -> bool:
    return obj.get('geometry_source') != 'IMAGE_ESTIMATE' and bool({'RADAR', 'LIDAR'} & {str(x).upper() for x in obj.get('sources', [])})


def _match(obj: Mapping[str, Any], query: TargetQuery) -> tuple[bool, bool]:
    if str(obj.get('class', '')).lower() != query.target_class:
        return False, False
    if query.same_lane:
        if obj.get('lane_relation') == 'OTHER': return False, False
        if obj.get('lane_relation') != 'SAME': return True, True
    p = obj.get('position_m', ())
    if len(p) < 2:
        return True, True
    if (query.side or query.longitudinal or query.max_distance_m is not None or query.distance_relation == 'NEAREST' or query.same_lane) and not _geometry_reliable(obj):
        return True, True
    x, y = float(p[0]), float(p[1])
    if query.side == 'LEFT' and y < -0.5 or query.side == 'RIGHT' and y > 0.5:
        return False, False
    if query.side and abs(y) <= 0.5:
        return True, True
    if query.longitudinal == 'AHEAD' and x < -0.5 or query.longitudinal == 'BEHIND' and x > 0.5:
        return False, False
    if query.longitudinal and abs(x) <= 0.5:
        return True, True
    if query.max_distance_m is not None and float(obj.get('distance_m', math.inf)) > query.max_distance_m:
        return False, False
    return True, False


def build_evidence(command: Mapping[str, Any], scene: Mapping[str, Any], request_id: str = '', *, geometry_trusted: bool = True, ids_reliable: bool = True) -> SceneEvidence | None:
    query = parse_target_query(str(command.get('source_text', '')), str(command.get('intent', '')))
    if query is None:
        return None
    candidates, uncertain, low_confidence, world_excluded = [], False, False, False
    if not geometry_trusted and (query.side or query.longitudinal or query.max_distance_m is not None or query.distance_relation == 'NEAREST'):
        uncertain = True
    explicit_id = command.get('parameters', {}).get('target_id')
    for obj in scene.get('objects', []):
        if explicit_id and obj.get('track_id') != explicit_id:
            continue
        sources = {str(source).upper() for source in obj.get('sources', [])}
        if sources == {'WORLD'}:
            world_excluded = True
            continue
        matched, unknown = _match(obj, query) if geometry_trusted else (str(obj.get('class', '')).lower() == query.target_class, bool(query.side or query.longitudinal or query.max_distance_m is not None or query.distance_relation == 'NEAREST'))
        if matched:
            candidates.append(obj)
            uncertain |= unknown
            low_confidence |= float(obj.get('confidence', 0)) < 0.8
    candidates.sort(key=lambda item: (float(item.get('distance_m', math.inf)), str(item.get('track_id'))))
    if query.distance_relation == 'NEAREST' and len(candidates) > 1 and not uncertain:
        if all(_geometry_reliable(item) for item in candidates) and float(candidates[1]['distance_m']) - float(candidates[0]['distance_m']) > 1.0:
            candidates = candidates[:1]
        else:
            uncertain = True
    ids = tuple(str(item['track_id']) for item in candidates)
    invalid = scene.get('stale', False) or not scene.get('sync', {}).get('within_tolerance', True)
    if invalid:
        status, reason = 'UNRESOLVED', 'PERCEPTION_STALE'
    elif not ids_reliable:
        status, reason = 'UNRESOLVED', 'TRACK_ID_UNSTABLE'
    elif not ids:
        status, reason = 'UNRESOLVED', 'WORLD_ONLY_NOT_SENSOR_EVIDENCE' if world_excluded else 'TARGET_NOT_FOUND_OR_NOT_VISIBLE'
    elif low_confidence:
        uncertain = True
        status, reason = 'AMBIGUOUS', 'LOW_TARGET_CONFIDENCE'
    elif query.visual_description:
        status, reason = 'AMBIGUOUS', 'VISUAL_ATTRIBUTE_UNVERIFIED'
    elif uncertain:
        status, reason = 'AMBIGUOUS', 'GEOMETRY_UNCERTAIN'
    elif len(ids) > 1:
        status, reason = 'AMBIGUOUS', 'MULTIPLE_CANDIDATES'
    else:
        status, reason = 'RESOLVED', 'UNIQUE_SENSOR_CANDIDATE'
    return SceneEvidence(request_id, int(scene.get('frame_id', 0)), query, ids, status, reason,
                         ids[0] if status == 'RESOLVED' else None, uncertain)


def select_targets(scene: Mapping[str, Any], evidence: SceneEvidence | None, limit: int) -> list[Mapping[str, Any]]:
    ordered = sorted(scene['objects'], key=lambda o: (float(o['distance_m']), -float(o['confidence']), o['track_id']))
    if evidence is None:
        return ordered[:limit]
    # Closest three are retained as collision-relevant safety context.
    def risk_key(o):
        ttc = o.get('ttc_s')
        urgent = isinstance(ttc, (int, float)) and 0 <= ttc <= 5
        return (0 if urgent else 1, float(ttc) if urgent else float(o['distance_m']))
    safety = sorted(ordered, key=risk_key)[:min(3, limit)]
    task = [o for o in ordered if o['track_id'] in evidence.candidate_ids]
    selected = []
    for obj in safety + task + ordered:
        if obj not in selected and len(selected) < limit:
            selected.append(obj)
    return selected


def verify_evidence(evidence: SceneEvidence | None, plan: Mapping[str, Any], current: Mapping[str, Any] | None,
                    *, now_ns: int, rgb_available: bool, command: Mapping[str, Any] | None = None, visible_ids: set[str] | None = None, visualized_ids: set[str] | None = None, max_age_ns: int = 500_000_000) -> tuple[str, str]:
    steps = plan.get('steps', [])
    behaviors = [str(s.get('behavior', '')).upper() for s in steps]
    if not any(b not in {'STOP', 'HOLD', 'SLOW_DOWN', 'YIELD'} for b in behaviors):
        return 'PASS', 'SAFE_ACTION'
    command = command or {}
    text = str(command.get('source_text', '')).lower()
    intent = str(command.get('intent', '')).upper()
    if intent == 'FOLLOW' and any(b.startswith('CHANGE_LANE') for b in behaviors) and not re.search(r'变道|换道|change lane', text):
        return 'REJECT', 'ACTION_CONTRADICTS_FOLLOW'
    if re.search(r'(?:先|首先).*(?:减速|慢下).*(?:再|然后).*(?:变道|换道)', text):
        first_lane = next((i for i, b in enumerate(behaviors) if b.startswith('CHANGE_LANE')), None)
        if first_lane is not None and not any(b == 'SLOW_DOWN' for b in behaviors[:first_lane]):
            return 'REJECT', 'REQUIRED_DECELERATION_MISSING'
    direction = str(command.get('parameters', {}).get('direction', '')).upper()
    if direction in {'LEFT', 'RIGHT'}:
        opposite = 'RIGHT' if direction == 'LEFT' else 'LEFT'
        if intent in {'CHANGE_LANE', 'AVOID_OBSTACLE'} and f'CHANGE_LANE_{opposite}' in behaviors and f'CHANGE_LANE_{direction}' not in behaviors:
            return 'REJECT', 'ACTION_DIRECTION_MISMATCH'
        if intent == 'AVOID_OBSTACLE':
            for step in steps:
                if str(step.get('behavior', '')).upper() != 'AVOID_OBSTACLE':
                    continue
                lane = step.get('target', {}).get('target_lane')
                if lane == f'{opposite}_ADJACENT':
                    return 'REJECT', 'ACTION_DIRECTION_MISMATCH'
                if lane != f'{direction}_ADJACENT':
                    return 'CONFIRM', 'ACTION_DIRECTION_UNSPECIFIED'
    if evidence is None:
        return 'PASS', 'NO_TARGET_QUERY'
    if current is None or current.get('stale', False) or not current.get('sync', {}).get('within_tolerance', True):
        return 'CONFIRM', 'PERCEPTION_STALE'
    captured = int(current.get('captured_at_ns', 0))
    if captured > now_ns + max_age_ns or now_ns - captured > max_age_ns:
        return 'CONFIRM', 'PERCEPTION_EXPIRED'
    ids = [str(s['target']['target_id']) for s in steps if s.get('target', {}).get('target_id') is not None and str(s.get('behavior', '')).upper() not in {'STOP', 'HOLD', 'SLOW_DOWN', 'YIELD'}]
    if any(b in {'FOLLOW', 'AVOID_OBSTACLE'} for b in behaviors) and not ids:
        return 'CONFIRM', 'TARGET_ID_REQUIRED'
    if not ids:
        return 'CONFIRM', 'TARGET_BINDING_REQUIRED'
    if evidence.status == 'UNRESOLVED':
        return 'CONFIRM', evidence.reason
    if evidence.status == 'AMBIGUOUS' and (not rgb_available or not current.get('modality_valid', {}).get('rgb', False)):
        return 'CONFIRM', 'VISUAL_UNAVAILABLE'
    if evidence.uncertain_geometry:
        return 'CONFIRM', evidence.reason if evidence.reason in {'GEOMETRY_UNCERTAIN', 'LOW_TARGET_CONFIDENCE'} else 'GEOMETRY_UNCERTAIN'
    current_by_id = {str(o['track_id']): o for o in current.get('objects', [])}
    for target_id in ids:
        if visible_ids is not None and target_id not in visible_ids:
            return 'REJECT', 'TARGET_NOT_IN_MODEL_INPUT'
        if target_id not in evidence.candidate_ids or evidence.resolved_id and target_id != evidence.resolved_id:
            return 'REJECT', 'TARGET_ID_MISMATCH'
        obj = current_by_id.get(target_id)
        if obj is None:
            return 'CONFIRM', 'TARGET_LOST'
        matched, unknown = _match(obj, evidence.query)
        if not matched:
            return 'REJECT', 'TARGET_RELATION_MISMATCH'
        if unknown:
            return 'CONFIRM', 'GEOMETRY_UNCERTAIN'
    if evidence.status == 'AMBIGUOUS':
        if visualized_ids is not None and not set(evidence.candidate_ids).issubset(visualized_ids):
            return 'CONFIRM', 'VISUAL_CANDIDATES_INCOMPLETE'
        model_grounding = plan.get('model_grounding', {})
        if (not isinstance(model_grounding, Mapping)
            or model_grounding.get('selection_source') != 'MODEL_VISUAL'
            or model_grounding.get('abstained')
            or model_grounding.get('target_id') not in ids):
            return 'CONFIRM', 'MODEL_VISUAL_SELECTION_MISSING'
    if evidence.query.distance_relation == 'NEAREST':
        matching = [o for o in current.get('objects', []) if _match(o, evidence.query) == (True, False)]
        matching.sort(key=lambda o: float(o.get('distance_m', math.inf)))
        if matching and str(matching[0]['track_id']) != ids[0]:
            return 'CONFIRM', 'NEAREST_CHANGED'
    return 'PASS', 'HARD_EVIDENCE_CONSISTENT'
