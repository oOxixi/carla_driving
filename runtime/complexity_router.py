"""Deterministic, explainable routing for simple and complex driving commands.

The router never calls a model and never grants vehicle-control authority.  It
only decides whether a command can use the local fast path, needs a constrained
Qwen planner, or must fail closed and ask for clarification.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import re
from typing import Any


FAST_LOCAL = "FAST_LOCAL"
QWEN_PLAN = "QWEN_PLAN"
CONFIRM_SAFE = "CONFIRM_SAFE"

_FAST_INTENTS = frozenset({
    "START", "STOP", "EMERGENCY_STOP", "SET_SPEED", "SLOW_DOWN", "KEEP_LANE",
})
_EMERGENCY_INTENTS = frozenset({"STOP", "EMERGENCY_STOP"})
_MANEUVER_INTENTS = frozenset({
    "FOLLOW", "YIELD", "CHANGE_LANE", "TURN", "PULL_OVER", "AVOID_OBSTACLE",
})

_SEQUENCE_RE = re.compile(
    r"(?:先|再|然后|随后|之后|通过后|确认后|接着|最后|等到|直到|"
    r"\bthen\b|\bafter\b|\bbefore\b|\buntil\b|\bnext\b)", re.IGNORECASE,
)
_CONDITION_RE = re.compile(
    r"(?:如果|若|假如|看到|等到|直到|确认.*后|否则|只要|除非|"
    r"\bif\b|\bwhen\b|\bonce\b|\bunless\b|\botherwise\b)", re.IGNORECASE,
)
_VISUAL_RE = re.compile(
    r"(?:那辆|那台|那个|那位|右前方|左前方|前面.*(?:车|行人|锥桶)|"
    r"白色|蓝色|红衣|SUV|锥桶|障碍物|行人|(?<!当)前车|目标车|"
    r"\bthat\b|\bvisible\b|\bwhite (?:car|vehicle)\b|\bblue (?:car|vehicle)\b|"
    r"\bpedestrian\b|\bcone\b|\bvehicle ahead\b)", re.IGNORECASE,
)
_ROUTE_RE = re.compile(
    r"(?:路口|第[一二三四五六七八九十\d]+个|出口|匝道|斑马线|停车区|"
    r"\bintersection\b|\bjunction\b|\bnext (?:left|right)\b|\bexit\b)",
    re.IGNORECASE,
)
_ILLEGAL_RE = re.compile(
    r"(?:闯红灯|逆行|撞开|撞过去|不管有没有人|无视行人|压实线|超速通过|"
    r"\brun (?:the )?red light\b|\bwrong way\b|\bhit (?:the )?car\b|"
    r"\bignore (?:the )?pedestrian\b)", re.IGNORECASE,
)
_SEVERE_AMBIGUITY_RE = re.compile(
    r"^(?:从那边(?:走|过去)?|往那边(?:走|开)?|跟着它|随便变个道|快一点|"
    r"走那边|gothere|followit|gothatway|speedup)$", re.IGNORECASE,
)

_ACTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("START", re.compile(r"(?:启动|起步|开始行驶|\bstart\b|\bgo\b)", re.IGNORECASE)),
    ("STOP", re.compile(r"(?:停车|停下|停止|刹车|\bstop\b|\bbrake\b)", re.IGNORECASE)),
    ("SET_SPEED", re.compile(r"(?:速度|公里每小时|千米每小时|米每秒|km/?h|m/?s|\bspeed\b)", re.IGNORECASE)),
    ("SLOW_DOWN", re.compile(r"(?:减速|慢一点|降到|\bslow down\b)", re.IGNORECASE)),
    ("KEEP_LANE", re.compile(r"(?:保持.*车道|继续直行|沿.*车道|\bkeep (?:the )?lane\b|\bstraight\b)", re.IGNORECASE)),
    ("FOLLOW", re.compile(r"(?:跟随|跟着|保持.*时距|\bfollow\b)", re.IGNORECASE)),
    ("YIELD", re.compile(r"(?:让行|避让|让.*通过|\byield\b|\bgive way\b)", re.IGNORECASE)),
    ("TURN_LEFT", re.compile(r"(?:左转|向左转|\bturn left\b|\btake the (?:next )?left\b)", re.IGNORECASE)),
    ("TURN_RIGHT", re.compile(r"(?:右转|向右转|\bturn right\b|\btake the (?:next )?right\b)", re.IGNORECASE)),
    ("CHANGE_LANE_LEFT", re.compile(r"(?:向左变道|变到左|进入左侧车道|\bchange lanes? left\b|\bmove to the left lane\b)", re.IGNORECASE)),
    ("CHANGE_LANE_RIGHT", re.compile(r"(?:向右变道|变到右|进入右侧车道|靠右行驶|\bchange lanes? right\b|\bmove to the right lane\b)", re.IGNORECASE)),
    ("AVOID_OBSTACLE", re.compile(r"(?:绕过|绕开|避开|绕行|\bavoid\b|\bgo around\b)", re.IGNORECASE)),
    ("RETURN_TO_LANE", re.compile(r"(?:回到.*车道|返回.*车道|回归.*车道|\breturn to (?:the )?(?:original )?lane\b)", re.IGNORECASE)),
    ("PULL_OVER", re.compile(r"(?:靠边停车|靠右停车|路边停车|\bpull over\b)", re.IGNORECASE)),
)


@dataclass(frozen=True, slots=True)
class ComplexityFeatures:
    atomic_action_count: int
    has_sequence: bool
    has_condition: bool
    has_visual_reference: bool
    has_route_reference: bool
    target_candidate_count: int
    target_is_unique: bool
    has_scene_conflict: bool
    has_modality_disagreement: bool
    requires_maneuver: bool
    parameters_complete: bool
    command_confidence: float
    perception_fresh: bool
    requires_replan: bool
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


@dataclass(frozen=True, slots=True)
class QwenRoutingDecision:
    disposition: str
    score: int
    reasons: tuple[str, ...]
    features: ComplexityFeatures
    safe_wait_behavior: str
    expected_qwen_calls: int


class ComplexityRouter:
    """Apply safety gates, hard routing triggers, then an explainable score."""

    def __init__(self, *, minimum_confidence: float = 0.80, qwen_score: int = 3) -> None:
        if not 0.0 <= float(minimum_confidence) <= 1.0:
            raise ValueError("minimum_confidence must be in [0, 1]")
        if type(qwen_score) is not int or qwen_score < 1:
            raise ValueError("qwen_score must be a positive integer")
        self.minimum_confidence = float(minimum_confidence)
        self.qwen_score = qwen_score

    def decide(
        self,
        command: Mapping[str, Any],
        perception: Mapping[str, Any],
        runtime_state: Mapping[str, Any] | None = None,
    ) -> QwenRoutingDecision:
        if not isinstance(command, Mapping) or not isinstance(perception, Mapping):
            raise TypeError("command and perception must be mappings")
        runtime = {} if runtime_state is None else runtime_state
        if not isinstance(runtime, Mapping):
            raise TypeError("runtime_state must be a mapping or None")

        text = str(command.get("source_text", "")).strip()
        intent = str(command.get("intent", "UNKNOWN")).upper()
        confidence = _confidence(command.get("confidence", 0.0))
        perception_fresh = (
            not bool(perception.get("stale", False))
            and bool(_nested(perception, "sync", "within_tolerance", default=True))
            and bool(_nested(perception, "modality_valid", "vehicle_state", default=True))
        )
        emergency = (
            intent == "EMERGENCY_STOP"
            or str(perception.get("risk_level", "UNKNOWN")).upper() == "EMERGENCY"
            or bool(runtime.get("emergency", False))
        )
        illegal = bool(_ILLEGAL_RE.search(text))
        severe_ambiguity = bool(_SEVERE_AMBIGUITY_RE.fullmatch(_normalized_text(text)))
        actions = _actions(text, intent)
        has_sequence = bool(_SEQUENCE_RE.search(text))
        has_condition = bool(_CONDITION_RE.search(text))
        has_visual = bool(_VISUAL_RE.search(text))
        has_route = bool(_ROUTE_RE.search(text))
        requires_maneuver = intent in _MANEUVER_INTENTS or any(
            item in {
                "FOLLOW", "YIELD", "TURN_LEFT", "TURN_RIGHT", "CHANGE_LANE_LEFT",
                "CHANGE_LANE_RIGHT", "AVOID_OBSTACLE", "RETURN_TO_LANE", "PULL_OVER",
            }
            for item in actions
        )
        candidate_count, target_unique = _target_candidates(
            command, perception, runtime, text, has_visual,
        )
        scene_conflict = _scene_conflict(command, perception, runtime, text, illegal)
        modality_disagreement = bool(
            runtime.get("has_modality_disagreement", False)
            or runtime.get("modality_disagreement", False)
        )
        replan_reason = str(runtime.get("replan_reason", "")).strip().upper()
        requires_replan = bool(replan_reason)
        parameters_complete = _parameters_complete(command)

        reasons: list[str] = []
        if len(actions) >= 2:
            reasons.append("MULTI_ACTION")
        if has_sequence:
            reasons.append("SEQUENCE")
        if has_condition:
            reasons.append("CONDITION")
        if has_visual:
            reasons.append("VISUAL_REFERENCE")
        if has_route:
            reasons.append("ROUTE_REFERENCE")
        if requires_maneuver:
            reasons.append("COMPLEX_MANEUVER")
        if scene_conflict:
            reasons.append("SCENE_CONFLICT")
        if modality_disagreement:
            reasons.append("MODALITY_DISAGREEMENT")
        if requires_replan:
            reasons.extend(("REPLAN_REQUIRED", f"REPLAN_{replan_reason}"))
        if not parameters_complete:
            reasons.append("PARAMETERS_INCOMPLETE")
        if confidence < self.minimum_confidence:
            reasons.append("LOW_CONFIDENCE")

        score = (
            (3 if len(actions) >= 2 else 0)
            + (3 if has_sequence or has_condition else 0)
            + (3 if has_visual or candidate_count > 1 else 0)
            + (2 if requires_maneuver else 0)
            + (2 if scene_conflict or modality_disagreement else 0)
            + (2 if requires_replan else 0)
            + (1 if not parameters_complete else 0)
        )
        safe_wait = _safe_wait_behavior(perception, runtime)

        if emergency or intent in _EMERGENCY_INTENTS:
            reason = "LOCAL_SAFETY" if emergency else "CLEAR_ATOMIC"
            return self._decision(
                FAST_LOCAL, -5, (reason,), actions, has_sequence, has_condition,
                has_visual, has_route, candidate_count, target_unique, scene_conflict,
                modality_disagreement, requires_maneuver, parameters_complete,
                confidence, perception_fresh, requires_replan, safe_wait,
            )
        if not perception_fresh:
            return self._decision(
                CONFIRM_SAFE, score, ("PERCEPTION_INVALID",), actions, has_sequence,
                has_condition, has_visual, has_route, candidate_count, target_unique,
                scene_conflict, modality_disagreement, requires_maneuver,
                parameters_complete, confidence, perception_fresh, requires_replan,
                "STOP",
            )
        if illegal:
            return self._decision(
                CONFIRM_SAFE, score, ("SAFETY_CONFLICT", "ILLEGAL_REQUEST"), actions,
                has_sequence, has_condition, has_visual, has_route, candidate_count,
                target_unique, True, modality_disagreement, requires_maneuver,
                parameters_complete, confidence, perception_fresh, requires_replan,
                "STOP",
            )
        if severe_ambiguity:
            return self._decision(
                CONFIRM_SAFE, score, ("INSUFFICIENT_GROUNDING",), actions,
                has_sequence, has_condition, has_visual, has_route, candidate_count,
                target_unique, scene_conflict, modality_disagreement, requires_maneuver,
                parameters_complete, confidence, perception_fresh, requires_replan,
                safe_wait,
            )
        if has_visual and candidate_count > 1 and not target_unique:
            return self._decision(
                CONFIRM_SAFE, score, ("TARGET_AMBIGUOUS", "VISUAL_REFERENCE"), actions,
                has_sequence, has_condition, has_visual, has_route, candidate_count,
                target_unique, scene_conflict, modality_disagreement, requires_maneuver,
                parameters_complete, confidence, perception_fresh, requires_replan,
                safe_wait,
            )
        clear_atomic = (
            intent in _FAST_INTENTS
            and len(actions) <= 1
            and not has_sequence
            and not has_condition
            and not has_visual
            and not has_route
            and not scene_conflict
            and not modality_disagreement
            and parameters_complete
            and confidence >= self.minimum_confidence
            and not bool(command.get("requires_confirmation", False))
        )
        if clear_atomic:
            return self._decision(
                FAST_LOCAL, -4, ("CLEAR_ATOMIC",), actions, has_sequence,
                has_condition, has_visual, has_route, candidate_count, target_unique,
                scene_conflict, modality_disagreement, requires_maneuver,
                parameters_complete, confidence, perception_fresh, requires_replan,
                safe_wait,
            )
        hard_qwen = (
            len(actions) >= 2 or has_sequence or has_condition or has_visual
            or has_route or requires_maneuver or modality_disagreement or requires_replan
        )
        if hard_qwen or score >= self.qwen_score:
            qwen_reasons = tuple(reasons) or ("COMPLEXITY_THRESHOLD",)
            return self._decision(
                QWEN_PLAN, score, qwen_reasons, actions, has_sequence, has_condition,
                has_visual, has_route, candidate_count, target_unique, scene_conflict,
                modality_disagreement, requires_maneuver, parameters_complete,
                confidence, perception_fresh, requires_replan, safe_wait,
            )
        return self._decision(
            CONFIRM_SAFE, score, tuple(reasons) or ("INSUFFICIENT_GROUNDING",),
            actions, has_sequence, has_condition, has_visual, has_route,
            candidate_count, target_unique, scene_conflict, modality_disagreement,
            requires_maneuver, parameters_complete, confidence, perception_fresh,
            requires_replan, safe_wait,
        )

    @staticmethod
    def _decision(
        disposition: str,
        score: int,
        reasons: tuple[str, ...],
        actions: set[str],
        has_sequence: bool,
        has_condition: bool,
        has_visual: bool,
        has_route: bool,
        candidate_count: int,
        target_unique: bool,
        scene_conflict: bool,
        modality_disagreement: bool,
        requires_maneuver: bool,
        parameters_complete: bool,
        confidence: float,
        perception_fresh: bool,
        requires_replan: bool,
        safe_wait: str,
    ) -> QwenRoutingDecision:
        unique_reasons = tuple(dict.fromkeys(reasons))
        features = ComplexityFeatures(
            atomic_action_count=len(actions),
            has_sequence=has_sequence,
            has_condition=has_condition,
            has_visual_reference=has_visual,
            has_route_reference=has_route,
            target_candidate_count=candidate_count,
            target_is_unique=target_unique,
            has_scene_conflict=scene_conflict,
            has_modality_disagreement=modality_disagreement,
            requires_maneuver=requires_maneuver,
            parameters_complete=parameters_complete,
            command_confidence=confidence,
            perception_fresh=perception_fresh,
            requires_replan=requires_replan,
            reason_codes=unique_reasons,
        )
        return QwenRoutingDecision(
            disposition=disposition,
            score=score,
            reasons=unique_reasons,
            features=features,
            safe_wait_behavior=safe_wait,
            expected_qwen_calls=1 if disposition == QWEN_PLAN else 0,
        )


def _normalized_text(text: str) -> str:
    return re.sub(r"[，。！？、,.!?\s]+", "", text.strip()).lower()


def _confidence(value: Any) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _nested(payload: Mapping[str, Any], outer: str, inner: str, *, default: Any) -> Any:
    value = payload.get(outer)
    return value.get(inner, default) if isinstance(value, Mapping) else default


def _actions(text: str, intent: str) -> set[str]:
    found = {name for name, pattern in _ACTION_PATTERNS if pattern.search(text)}
    intent_action = {
        "START": "START",
        "STOP": "STOP",
        "EMERGENCY_STOP": "STOP",
        "SET_SPEED": "SET_SPEED",
        "SLOW_DOWN": "SLOW_DOWN",
        "KEEP_LANE": "KEEP_LANE",
        "FOLLOW": "FOLLOW",
        "YIELD": "YIELD",
        "PULL_OVER": "PULL_OVER",
        "AVOID_OBSTACLE": "AVOID_OBSTACLE",
    }.get(intent)
    if intent_action is not None:
        found.add(intent_action)
    if intent == "TURN" and not {"TURN_LEFT", "TURN_RIGHT"}.intersection(found):
        found.add("TURN")
    if intent == "CHANGE_LANE" and not {
        "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT",
    }.intersection(found):
        found.add("CHANGE_LANE")
    if "SLOW_DOWN" in found:
        # A numeric destination in "slow down to 3 m/s" parameterizes the
        # single SLOW_DOWN action; it is not a second SET_SPEED action.
        found.discard("SET_SPEED")
    # SET_SPEED wording often contains "保持", but that is not a separate
    # KEEP_LANE action unless the text actually names a lane/straight motion.
    return found


def _parameters_complete(command: Mapping[str, Any]) -> bool:
    intent = str(command.get("intent", "UNKNOWN")).upper()
    parameters = command.get("parameters")
    parameters = parameters if isinstance(parameters, Mapping) else {}
    if intent == "SET_SPEED":
        return "target_speed_mps" in parameters
    if intent in {"TURN", "CHANGE_LANE"}:
        return str(parameters.get("direction", "")).upper() in {"LEFT", "RIGHT", "STRAIGHT"}
    if intent == "FOLLOW" and "target_id" in parameters:
        return bool(str(parameters["target_id"]).strip())
    return intent not in {"UNKNOWN"}


def _target_candidates(
    command: Mapping[str, Any],
    perception: Mapping[str, Any],
    runtime: Mapping[str, Any],
    text: str,
    has_visual: bool,
) -> tuple[int, bool]:
    explicit_count = runtime.get("target_candidate_count", perception.get("target_candidate_count"))
    explicit_unique = runtime.get("target_is_unique", perception.get("target_is_unique"))
    if type(explicit_count) is int and not isinstance(explicit_count, bool) and explicit_count >= 0:
        unique = bool(explicit_unique) if explicit_unique is not None else explicit_count == 1
        return explicit_count, unique
    parameters = command.get("parameters")
    target_id = parameters.get("target_id") if isinstance(parameters, Mapping) else None
    objects = perception.get("objects", ())
    objects = objects if isinstance(objects, Sequence) and not isinstance(objects, (str, bytes)) else ()
    if target_id:
        found = sum(
            1 for item in objects
            if isinstance(item, Mapping) and item.get("track_id") == target_id
        )
        return found, found == 1
    if not has_visual:
        return 0, False
    lower = text.lower()
    wanted_class = None
    if any(token in lower for token in ("行人", "pedestrian", "红衣")):
        wanted_class = "pedestrian"
    elif any(token in lower for token in ("车", "suv", "vehicle", "car", "前车")):
        wanted_class = "vehicle"
    elif any(token in lower for token in ("锥桶", "障碍", "cone", "obstacle")):
        wanted_class = "obstacle"
    candidates: list[Mapping[str, Any]] = []
    for item in objects:
        if not isinstance(item, Mapping):
            continue
        if wanted_class is not None and str(item.get("class", "unknown")).lower() != wanted_class:
            continue
        position = item.get("position_m", (0.0, 0.0, 0.0))
        if not isinstance(position, Sequence) or len(position) < 2:
            position = (0.0, 0.0, 0.0)
        x, y = float(position[0]), float(position[1])
        if "右前" in text and not (x >= 0.0 and y < -1.0):
            continue
        if "左前" in text and not (x >= 0.0 and y > 1.0):
            continue
        candidates.append(item)
    count = len(candidates)
    return count, count == 1


def _scene_conflict(
    command: Mapping[str, Any],
    perception: Mapping[str, Any],
    runtime: Mapping[str, Any],
    text: str,
    illegal: bool,
) -> bool:
    if illegal or bool(runtime.get("has_scene_conflict", False)):
        return True
    traffic = str(perception.get("traffic_light", "UNKNOWN")).upper()
    progression = not re.search(r"(?:停车|停止|stop|brake)", text, re.IGNORECASE)
    if traffic in {"RED", "YELLOW"} and progression and any(
        token in text.lower() for token in ("走", "通过", "转", "go", "turn", "proceed")
    ):
        return True
    return False


def _safe_wait_behavior(perception: Mapping[str, Any], runtime: Mapping[str, Any]) -> str:
    risk = str(perception.get("risk_level", "UNKNOWN")).upper()
    if risk == "EMERGENCY" or bool(runtime.get("emergency", False)):
        return "EMERGENCY_STOP"
    if (
        bool(perception.get("stale", False))
        or not bool(_nested(perception, "sync", "within_tolerance", default=True))
        or risk in {"HIGH", "UNKNOWN"}
    ):
        return "STOP"
    if risk == "CAUTION" or bool(runtime.get("approaching_conflict", False)):
        return "SLOW_DOWN"
    return "KEEP_LANE_LIMITED"


__all__ = [
    "CONFIRM_SAFE",
    "FAST_LOCAL",
    "QWEN_PLAN",
    "ComplexityFeatures",
    "ComplexityRouter",
    "QwenRoutingDecision",
]
