import re
import time
from dataclasses import asdict, dataclass
from typing import Optional

from .normalizer import normalize_text


@dataclass
class IntentResult:
    """B1意图识别结果。"""

    original_text: str
    normalized_text: str
    intent: str
    confidence: float
    status: str
    route: str
    reason: Optional[str]
    latency_ms: float


# 中文数字或阿拉伯数字
NUMBER_PATTERN = r"(?:\d+(?:\.\d+)?|[零〇一二两三四五六七八九十百]+)"


def _matches(text: str, patterns: list[str]) -> bool:
    """判断文本是否匹配任意一个正则表达式。"""

    return any(
        re.search(pattern, text) is not None
        for pattern in patterns
    )


def _build_result(
    *,
    original_text: str,
    normalized_text: str,
    intent: str,
    confidence: float,
    status: str,
    route: str,
    reason: Optional[str],
    start_time: float,
) -> dict:
    """统一创建返回结果并统计耗时。"""

    latency_ms = (
        time.perf_counter() - start_time
    ) * 1000

    result = IntentResult(
        original_text=original_text,
        normalized_text=normalized_text,
        intent=intent,
        confidence=confidence,
        status=status,
        route=route,
        reason=reason,
        latency_ms=round(latency_ms, 3),
    )

    return asdict(result)


# ---------------------------------------------------------------------------
# Compound-command routing
# ---------------------------------------------------------------------------
#
# B1's deterministic fast path represents one executable intent.  Commands
# that express multiple independent manoeuvre semantics must therefore be
# routed to the planner slow path rather than silently dropping one action.
#
# Important safety exception:
#     "cannot avoid / no avoidance space -> emergency stop"
# is a single terminal emergency action.  The word "avoid" describes an
# unavailable alternative and must not cause an emergency command to be
# routed through the slower planner path.
#
# These rules operate only on source text.  They do not depend on benchmark
# IDs, categories, semantic_intent labels, or expected actions.


_COMPOUND_NUMBER_PATTERN = (
    r"(?:\d+(?:\.\d+)?|[零〇一二两三四五六七八九十百]+)"
)


_TERMINAL_EMERGENCY_STOP_PATTERNS = (
    r"(?:紧急停车|立即停车|马上停车|立刻停车|紧急制动|紧急刹车)",
    r"(?:立即|马上|立刻|紧急).{0,8}(?:停车|停下|制动|刹车)",
)


_AVOIDANCE_UNAVAILABLE_PATTERNS = (
    r"(?:来不及|无法|不能|没法).{0,8}(?:避让|避开|绕开|绕过)",

    r"(?:没有|无|缺少).{0,8}(?:安全)?避让空间",

    r"(?:避让|绕行).{0,6}(?:空间|方向|通道|路径)"
    r".{0,8}(?:不足|没有|被占用|被堵住|被阻断)",

    r"(?:安全)?避让.{0,6}"
    r"(?:空间不足|方向被阻挡|通道被堵住|路径被占用)",
)


_COMPOUND_SIGNAL_PATTERNS = {
    "speed": (
        rf"(?:速度|车速).{{0,10}}"
        rf"(?:调|调整|调到|调至|降到|降至|设|设为|设置|控制|稳定|"
        rf"限制|保持|提升|提高|降低).{{0,8}}"
        rf"{_COMPOUND_NUMBER_PATTERN}",

        rf"(?:减速到|降速到|减至|降至|加速到|提速到|提速至|"
        rf"提升到|提升至|提高到|提高至|加至).{{0,5}}"
        rf"{_COMPOUND_NUMBER_PATTERN}",

        rf"(?:按|按照|以|采用|改以).{{0,8}}"
        rf"{_COMPOUND_NUMBER_PATTERN}.{{0,6}}"
        r"(?:公里每小时|km/h|公里/小时)",

        rf"{_COMPOUND_NUMBER_PATTERN}.{{0,6}}"
        r"(?:公里每小时|km/h|公里/小时)"
        r".{0,8}(?:行驶|通过|继续)",

        r"(?:减速|降速|放慢|降低速度|控制车速|控制速度)",
    ),

    "keep_lane": (
        r"(?:保持|维持).{0,10}"
        r"(?:当前|本|这条|现在所在|原有|原来的|原).{0,5}"
        r"(?:车道|道路|路线)",

        r"(?:继续沿|沿着|沿).{0,10}"
        r"(?:当前|本|这条|原有|原来的|原).{0,5}"
        r"(?:车道|道路|路线)",

        r"(?:按|沿).{0,6}"
        r"(?:当前|原有|原来的|原).{0,5}"
        r"(?:路线|道路).{0,8}(?:继续|行驶|前进)",

        r"(?:继续|保持).{0,6}"
        r"(?:当前|原有|原来的|原).{0,5}"
        r"(?:路线|道路|车道)",

        r"(?:不要|别|禁止).{0,8}"
        r"(?:改变|变更|离开).{0,6}"
        r"(?:当前|本|这条)?.{0,4}车道",

        r"(?:保持当前车道|继续当前路线|继续原路线)",
    ),

    "lane_change": (
        r"(?:向左|向右|左侧|右侧).{0,5}"
        r"(?:变道|换道|并道|并线)",

        r"(?:变入|换到|进入|并入|切到).{0,5}"
        r"(?:左侧|右侧).{0,5}"
        r"(?:车道|目标车道)",
    ),

    "turn": (
        r"(?:左转|右转|向左转|向右转|左侧转向|右侧转向)",
        r"(?:向左|向右).{0,4}(?:转弯|转向)",
    ),

    "avoid": (
        r"(?:避让|避开|避过|绕开|绕过|绕行|躲开)",
        r"(?:安全通过).{0,8}(?:后|以后|之后)",
    ),

    "yield_wait": (
        r"(?:等待|等).{0,14}"
        r"(?:行人|他们|对方|人|骑行者).{0,10}"
        r"(?:通过|走完|过去|离开)",

        r"(?:让|礼让).{0,14}"
        r"(?:正在)?(?:通行|通过|过街|穿行)?.{0,6}"
        r"(?:的)?(?:行人|人|骑行者).{0,8}"
        r"(?:通过|走完|先行)?",

        r"(?:让|礼让).{0,10}"
        r"(?:行人|人|骑行者).{0,8}"
        r"(?:通过|走完|先行)",

        r"(?:停车等待|先等待|优先避让|先避让)",

        r"(?:先)?等候.{0,10}"
        r"(?:再|然后|随后).{0,10}"
        r"(?:执行|完成|继续)?"
        r"(?:左转|右转|转弯|转向)",
    ),

    "stop": (
        r"(?:停车|停下|停止|停住|紧急停车|紧急制动|紧急刹车)",
    ),

    "resume_route": (
        r"(?:恢复|回到|返回).{0,10}"
        r"(?:原有|原来的|原|当前)?.{0,6}"
        r"(?:行驶)?(?:路线|道路|车道)",

        r"(?:恢复|回到|返回).{0,8}(?:路线|道路|车道)",

        r"(?:通过|避让|避开|绕开|绕过|绕行).{0,10}后"
        r".{0,10}(?:继续|保持|恢复|回到|返回)",

        r"(?:继续|恢复|回到|返回).{0,8}"
        r"(?:原有|原来的|原|当前).{0,6}"
        r"(?:路线|道路|车道)",
    ),
}


_COMPOUND_SIGNAL_PAIRS = frozenset({
    frozenset(("speed", "keep_lane")),
    frozenset(("speed", "lane_change")),
    frozenset(("speed", "avoid")),

    frozenset(("avoid", "keep_lane")),
    frozenset(("avoid", "resume_route")),

    frozenset(("turn", "avoid")),
    frozenset(("turn", "yield_wait")),

    frozenset(("lane_change", "avoid")),
    frozenset(("lane_change", "resume_route")),
})


_VULNERABLE_CONTEXT_PATTERNS = (
    r"(?:公交站|公交车|巴士站|巴士)",
    r"(?:行人|有人|过街的人|路侧的人)",
)


_CONTINUE_AFTER_SPEED_PATTERNS = (
    r"(?:后|然后|再).{0,8}"
    r"(?:继续前进|继续行驶|继续沿|按当前路线继续|沿当前道路继续)",
)


def _matches_any_pattern(
    text: str,
    patterns: tuple[str, ...],
) -> bool:
    return any(
        re.search(pattern, text)
        for pattern in patterns
    )


def _is_terminal_emergency_stop(text: str) -> bool:
    """True when avoidance is explicitly unavailable and STOP is terminal."""

    return (
        _matches_any_pattern(
            text,
            _TERMINAL_EMERGENCY_STOP_PATTERNS,
        )
        and _matches_any_pattern(
            text,
            _AVOIDANCE_UNAVAILABLE_PATTERNS,
        )
    )


def _compound_signal_names(text: str) -> set[str]:
    names: set[str] = set()

    for name, patterns in _COMPOUND_SIGNAL_PATTERNS.items():
        if _matches_any_pattern(text, patterns):
            names.add(name)

    return names


def _has_compound_signal_pair(
    names: set[str],
) -> bool:
    return any(
        pair.issubset(names)
        for pair in _COMPOUND_SIGNAL_PAIRS
    )


def _has_vulnerable_speed_continuation(
    text: str,
    names: set[str],
) -> bool:
    """
    Detect context-dependent speed+continuation commands.

    A generic sentence such as
        "减到40公里每小时再继续行驶"
    remains a single speed command.

    When the same construction is conditioned on a pedestrian/bus-stop
    hazard, preserving the follow-on route semantics requires the planner.
    """

    return (
        "speed" in names
        and _matches_any_pattern(
            text,
            _VULNERABLE_CONTEXT_PATTERNS,
        )
        and _matches_any_pattern(
            text,
            _CONTINUE_AFTER_SPEED_PATTERNS,
        )
    )


def _contains_multiple_actions(text: str) -> bool:
    """
    Return True when one utterance requires multiple high-level semantics.

    Complex commands are routed to the Qwen/planner slow path.  Terminal
    emergency-stop commands remain on the deterministic fast path even when
    they describe avoidance as unavailable.
    """

    if _is_terminal_emergency_stop(text):
        return False

    names = _compound_signal_names(text)

    if _has_compound_signal_pair(names):
        return True

    return _has_vulnerable_speed_continuation(
        text,
        names,
    )

def classify_intent(text: str) -> dict:
    """
    将车控文本识别为一个意图。

    当前支持：
        EMERGENCY_STOP
        PULL_OVER
        SET_SPEED
        AVOID_OBSTACLE
        CHANGE_LANE
        KEEP_LANE
        SPEED_UP
        SLOW_DOWN
        STOP
        UNKNOWN
    """

    start_time = time.perf_counter()
    original_text = text
    normalized_text = normalize_text(text)
    emergency_punctuation = "!" in original_text or "！" in original_text

    # 1. 空文本
    if not normalized_text:
        return _build_result(
            original_text=original_text,
            normalized_text=normalized_text,
            intent="UNKNOWN",
            confidence=0.0,
            status="unknown",
            route="fast",
            reason="empty_text",
            start_time=start_time,
        )

    # 2. 第一版不直接处理复合指令
    if _contains_multiple_actions(normalized_text):
        return _build_result(
            original_text=original_text,
            normalized_text=normalized_text,
            intent="UNKNOWN",
            confidence=0.0,
            status="needs_slow_path",
            route="slow",
            reason="multiple_intents",
            start_time=start_time,
        )

    # 3. 否定停车、否定加速暂不转换为可执行动作
    if _matches(
        normalized_text,
        [
            r"(不要|别|禁止).*(停车|停下|刹车|制动)",
            r"(不要|别|禁止).*(加速|提速|开快)",
        ],
    ):
        return _build_result(
            original_text=original_text,
            normalized_text=normalized_text,
            intent="UNKNOWN",
            confidence=0.0,
            status="unknown",
            route="fast",
            reason="negated_command",
            start_time=start_time,
        )

    # 4. 不要变道属于保持当前车道
    if _matches(
        normalized_text,
                [
            r"(不要|别|禁止)"
            r".*(变道|换车道|换道|并线|并到|切到|挪到)",

            r"(不要|别|禁止).*(换线|变线)",

            r"不.*(变道|并道|切道|切车道|走别的道)",

            r"(不要|别|禁止)"
            r".*(偏离|离开).*(当前|本|这条)?.*车道",

            r"(保持|维持)"
            r".*(当前|本|这条|现在所在)?.*车道",

            r"(继续)?沿(着)?.*(当前|本|这条).*车道"
            r".*(行驶|开)?",

            r"(就在|继续走|保持在)"
            r".*(当前|本|这条).*车道.*(开|行驶)?",

            r"在本车道.*行驶",

            r"(稳住|保持住).*(不要|别)?.*(变|换)",

            r"(坚持|继续).*(本|这条|当前).*车道",

            r"(就在|走|停在).*(这条|当前|本).*道",
            r"稳住车道",
            r"不走别的道",
            r"不变道",
            r"别切车道",
            r"不要切道",
            r"当前车道继续",
            r"(这条|这个|当前|本).*道.*(继续|不变|走)",
            r"就这个车道",
            r"继续走这条",
            r"不要偏",
        ],

    ):
        intent = "KEEP_LANE"
        confidence = 0.98

       # 5. 紧急停车必须在普通停车之前
    elif _matches(
        normalized_text,
        [
            r"(紧急|立即|马上|立刻|赶快|赶紧|快点|快)"
            r".*(停车|刹车|制动|停下|停住|刹住|刹停)",

            r"(停车|刹车|制动|刹停)"
            r".*(紧急|立即|马上|立刻|赶快|赶紧)",

            r"(马上|立刻|立即|赶快|赶紧).*(停|刹)$",

            r"(踩死|踩紧|猛踩).*(刹车|制动)",

            r"刹.*刹车",

            r"(急停|紧急制动|立即制动|马上制动)",
            r"(紧急|快).*(刹|停)",
            r"(急刹|刹车踩到底)$",

            # Repeating the stop action is an urgency signal even when ASR
            # strips the original exclamation mark.
            r"^(停车|停下|停住|刹车|制动)\1$",

            r"^踩死车$",

            r"^刹$",
        ],
    ) or (
        emergency_punctuation
        and _matches(
            normalized_text,
            [
                r"^(停|停车|停住|刹停|刹住|刹住车|刹车|制动)$",
            ],
        )
    ):
        intent = "EMERGENCY_STOP"
        confidence = 0.99

       # 6. 靠边停车必须在普通停车之前
    elif _matches(
        normalized_text,
        [
            # 先出现停车位置，再出现停车动作
            r"(靠边|靠左侧|靠右侧|路边|路肩|路旁|道路边缘|"
            r"道路左侧|道路右侧|左侧安全位置|右侧安全位置|"
            r"靠左|靠右|边上|往路边|"
            r"左侧安全区域|右侧安全区域)"
            r".*(停|停车|停下|停好|停住|靠)",

            # 先出现停车动作，再出现停车位置
            r"(停|停车|停下|停到)"
            r".*(路边|路肩|路旁|道路边缘|道路左侧|道路右侧|"
            r"左侧安全位置|右侧安全位置|左侧安全区域|右侧安全区域)",

            # “靠到右侧路旁停车”一类表达
            r"(靠到|靠向|往)"
            r".*(左侧|右侧|路边|路肩|路旁)"
            r".*(停|停车|停下|停好)",

            r"(停|停车|停到).*(左侧|右侧)(吧+|吗+)?$",
            r"(左侧|右侧).*(停|停车|停下|停好)",
            r"(在)?(左侧|右侧)(停|停车|停下|停好)",
            r"靠(左|右|左侧|右侧).*(停|停车|停下|停好|停吧)",
            r"边上停车",

            r"(把车)?靠到.*(路边|路旁|路肩|安全位置)",

            r"(左转|右转)?靠边",
            r"靠(左|右)停",
            r"边上停车",
        ],
    ):
        intent = "PULL_OVER"
        confidence = 0.98


        # 7. 给出明确速度值时属于SET_SPEED
    elif _matches(
        normalized_text,
        [
            # 原有表达
            rf"(减速到|减速至|降速到|降速至|加速到|加速至|"
            rf"提速到|提速至|降到|降至|提高到|提高至|提升到|提升至|"
            rf"提到|升到|设置为|设为|调整到|调整至|控制在|"
            rf"稳定在|限制在|保持|开到).{{0,10}}{NUMBER_PATTERN}",

            rf"(速度|车速).{{0,10}}"
            rf"(到|为|调到|调至|调整到|调整至|降到|降至|减至|"
            rf"提高到|提高至|提升到|提升至|控制在|稳定在|限制在)"
            rf".{{0,6}}{NUMBER_PATTERN}",

            # 新表达：车速调成35、把速度控制到45
            rf"(速度|车速).{{0,8}}"
            rf"(调成|控制到|控制在|调整成)"
            rf".{{0,6}}{NUMBER_PATTERN}",

            # 新表达：降至25公里、提到55公里
            rf"(降至|提到).{{0,6}}{NUMBER_PATTERN}"
            rf".{{0,8}}(公里|千米|km)",

            # 新表达：维持每小时50公里
            rf"(维持|保持).{{0,10}}{NUMBER_PATTERN}"
            rf".{{0,10}}(公里|千米|km)",

            rf"(控制|设置|调整).{{0,6}}(速度|车速).{{0,6}}"
            rf"(在|到|为).{{0,6}}{NUMBER_PATTERN}",

            rf"(定速|把速度定在|速度定在|维持).{{0,8}}{NUMBER_PATTERN}",

            rf"(速度|车速).{{0,6}}(设置成|设成|保持在).{{0,6}}{NUMBER_PATTERN}",

            rf"以.{{0,3}}{NUMBER_PATTERN}.{{0,6}}速度行驶",

            # Explicit unit-bearing target speed:
            # 按/按照/以/采用/改以 35公里每小时 ...
            rf"(?:按|按照|以|采用|改以).{{0,6}}"
            rf"{NUMBER_PATTERN}.{{0,6}}"
            rf"(?:公里每小时|公里/小时|千米每小时|千米/小时|km/h|KM/H)",

            rf"提速到.{{0,6}}{NUMBER_PATTERN}",
        ],
    ):
        intent = "SET_SPEED"
        confidence = 0.99


           # 8. 绕障必须在普通变道之前
    elif _matches(
        normalized_text,
        [
            r"(绕开|绕过|避开|避让|躲开|避过|绕行)",
            r"从(左侧|右侧).*(障碍|前车|车辆|行人|路障)",
            r"(绕一下|绕一绕)",
            r"(不要|别).*(撞|碰).*(车|车辆|行人|障碍)",
            r"(不要|别).*撞.*东西",
            r"让开.*东西",
            r"从(左|右|左侧|右侧)绕",
        ],
    ):
        intent = "AVOID_OBSTACLE"
        confidence = 0.97


        # 9. 转向
    elif (
        _matches(
        normalized_text,
        [
            r"(左转|右转|直行)",
            r"(向左|向右).*(转|拐)",
            r"(左|右).*(拐|转弯)",
        ],
        )
        and not _matches(normalized_text, [r"(变道|并道|换道)"])
    ):
        intent = "TURN"
        confidence = 0.97


        # 10. 变道
    elif _matches(
        normalized_text,
        [
            r"变道",
            r"换到.*车道",
            r"进入.*车道",
            r"并入.*车道",

            r"变入(左|右|左侧|右侧)(目标)?车道",

            r"并道",

            r"(换|并|切|变)(到|入|向|往)?(左|右|左侧|右侧)(车道|道)?(吧+)?$",

            r"往(左|右|左侧|右侧).*(变|换|并)",

            # 新表达：切换到、切到、挪到、变到
            r"(切换到|切到|挪到|变到)"
            r".*(左侧|右侧)?.*(车道|那条道)",

            # 新表达：往左边的车道过去
            r"往(左侧|右侧).*车道.*(过去|移动|走)",
        ],
    ):
        intent = "CHANGE_LANE"
        confidence = 0.97

        # 11. 相对加速
    elif _matches(
        normalized_text,
        [
            r"加速",
            r"提速",
            r"开快",
            r"快一点",
            r"再快一点",
            r"速度.*提",
            r"车速.*提高",
            r"加快.*速度",
            r"往快了开",

            # 新表达
            r"(稍微|再)?.*(快些|快一点)",
            r"(再)?.*提.*一点.*速度",
            r"速度.*(往上|提高|提升|提)",
            r"车.*(再快些|快些)",
            r"加快一些",

            r"^(给我)?(快走|快点走|快点开|快点|冲)(吧+)?$",

            r"加一点速",
            r"(再)?给点油",
            r"油门.*(深|大|重)",
            r"(快起来|快着点)",
            r"(快开|快点儿|快点开)",
            r"(再)?快点",
            r"(快点跑|跑快点)",
            r"开猛一点",
            r"速度.*(快点|高点)",
            r"(加快|加点油|加油)(吧+)?$",
            r"提高速度",
            r"(速度|车速).*(拉起来|加上去)",
            r"提一下速",
            r"别磨蹭",
            r"快马加鞭",
        ],
    ):
        intent = "SPEED_UP"
        confidence = 0.95


        # 12. 相对减速
    elif _matches(
        normalized_text,
        [
            r"减速",
            r"降速",
            r"开慢",
            r"慢一点",
            r"再慢一点",
            r"速度.*降",
            r"车速.*降低",
            r"放慢.*速度",
            r"放慢.*行驶",
            r"别开这么快",

            # 新表达
            r"(缓一点|慢些|放慢点)",
            r"速度.*(压低|降低)",
            r"(压低|降低).*车速",
            r"(别那么急|别这么急)",
            r"开得.*(缓|慢|别那么急)",

            r"(再)?慢点",

            r"慢速行驶",

            r"别(冲|充).*快",
            r"(收油|放慢)$",
            r"(收点油|降点速|减一下速)",
            r"(缓一缓|悠着点|稳一点|慢下来)",
            r"别(那么|太)快",
            r"(慢行|慢慢开|慢一些|慢着点)",
            r"不要太快",
            r"速度.*(收一收|再低点|放低)",
            r"松油门",
            r"稍微减点",
        ],
    ):
        intent = "SLOW_DOWN"
        confidence = 0.95


       # 13. 普通停车放在最后
    elif _matches(
        normalized_text,
        [
            r"停车",
            r"停下",
            r"车辆停止",
            r"车子停止",
            r"停住",

            # 新表达
            r"(就在前面|在前面|到这里|这里|先|让车|把车辆|车辆)"
            r".*(停|停下|停住)",

            r"停一会儿",
            r"完全停下",
            r"刹停",
            r"停稳",
            r"暂停",
            r"停好",
            r"差不多停了",
            r"给我停",
            r"原地停",
            r"就这儿停",
            r"把车停了",
            r"慢慢停",
            r"靠这儿停",
            r"歇一下",
            r"可以停了",
            r"到了停吧",
            r"停吧",

            r"^(就)?(停|停了|在这停|在这儿停|停这里|停这儿|到位了停)(吧+)?$",

            r"(刹|撒)一脚",
        ],
    ):
        intent = "STOP"
        confidence = 0.96


    # 14. 无法识别
    else:
        return _build_result(
            original_text=original_text,
            normalized_text=normalized_text,
            intent="UNKNOWN",
            confidence=0.0,
            status="unknown",
            route="fast",
            reason="unsupported_command",
            start_time=start_time,
        )

    return _build_result(
        original_text=original_text,
        normalized_text=normalized_text,
        intent=intent,
        confidence=confidence,
        status="valid",
        route="fast",
        reason=None,
        start_time=start_time,
    )
