import re
import time
from dataclasses import asdict, dataclass
from typing import Optional

from src.normalizer import normalize_text


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


def _contains_multiple_actions(text: str) -> bool:
    """
    初步检测复合指令。

    示例：
        先减速到40，然后向左变道
    """

    has_connector = (
        _matches(
            text,
            [
                r"然后",
                r"接着",
                r"同时",
                r"并且",
                r"随后",
                r"先.*再",
            ],
        )
    )

    if not has_connector:
        return False

    action_groups = [
        r"(紧急|立即|马上|立刻).*(停车|刹车|制动)",
        r"(靠边|路边|道路左侧|道路右侧).*(停|停车)",
        r"(减速到|加速到|设置为|设为|调整到|控制在)"
        + rf".*{NUMBER_PATTERN}",
        r"(绕开|绕过|避开|避让)",
        r"(变道|换到.*车道|进入.*车道|并入.*车道)",
        r"(保持|维持).*(当前|本|这条)?.*车道",
        r"(加速|提速|开快|加快)",
        r"(减速|降速|开慢|放慢)",
        r"(停车|停下|停止|停住)",
    ]

    matched_count = sum(
        1
        for pattern in action_groups
        if re.search(pattern, text)
    )

    return matched_count >= 2


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

            r"(不要|别|禁止)"
            r".*(偏离|离开).*(当前|本|这条)?.*车道",

            r"(保持|维持)"
            r".*(当前|本|这条|现在所在)?.*车道",

            r"(继续)?沿(着)?.*(当前|本|这条).*车道"
            r".*(行驶|开)?",

            r"(就在|继续走|保持在)"
            r".*(当前|本|这条).*车道.*(开|行驶)?",

            r"在本车道.*行驶",
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
        ],
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
            r"左侧安全区域|右侧安全区域)"
            r".*(停|停车|停下|停好)",

            # 先出现停车动作，再出现停车位置
            r"(停|停车|停下|停到)"
            r".*(路边|路肩|路旁|道路边缘|道路左侧|道路右侧|"
            r"左侧安全位置|右侧安全位置|左侧安全区域|右侧安全区域)",

            # “靠到右侧路旁停车”一类表达
            r"(靠到|靠向|往)"
            r".*(左侧|右侧|路边|路肩|路旁)"
            r".*(停|停车|停下|停好)",
        ],
    ):
        intent = "PULL_OVER"
        confidence = 0.98


        # 7. 给出明确速度值时属于SET_SPEED
    elif _matches(
        normalized_text,
        [
            # 原有表达
            rf"(减速到|加速到|降到|提高到|设置为|设为|调整到|"
            rf"控制在|保持|开到).{{0,10}}{NUMBER_PATTERN}",

            rf"(速度|车速).{{0,10}}"
            rf"(到|为|降到|提高到|调整到|控制在)"
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
        ],
    ):
        intent = "AVOID_OBSTACLE"
        confidence = 0.97


        # 9. 变道
    elif _matches(
        normalized_text,
        [
            r"变道",
            r"换到.*车道",
            r"进入.*车道",
            r"并入.*车道",

            # 新表达：切换到、切到、挪到、变到
            r"(切换到|切到|挪到|变到)"
            r".*(左侧|右侧)?.*(车道|那条道)",

            # 新表达：往左边的车道过去
            r"往(左侧|右侧).*车道.*(过去|移动|走)",
        ],
    ):
        intent = "CHANGE_LANE"
        confidence = 0.97

        # 10. 相对加速
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
        ],
    ):
        intent = "SPEED_UP"
        confidence = 0.95


        # 11. 相对减速
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
        ],
    ):
        intent = "SLOW_DOWN"
        confidence = 0.95


       # 12. 普通停车放在最后
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
        ],
    ):
        intent = "STOP"
        confidence = 0.96


    # 13. 无法识别
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
