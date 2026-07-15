from typing import Any

from src.intent_classifier import classify_intent


def process_asr_text(
    request_id: str,
    text: str,
    asr_confidence: float | None = None,
) -> dict[str, Any]:
    """
    B1 对外统一接口。

    参数:
        request_id:
            每条指令的唯一编号，由A或D生成。

        text:
            A模块输出的ASR识别文本。

        asr_confidence:
            A模块提供的语音识别置信度。
            如果A暂时不提供，可以传None。

    返回:
        交给B2的统一字典。
    """

    if not isinstance(request_id, str):
        raise TypeError("request_id 必须是字符串")

    if not request_id.strip():
        raise ValueError("request_id 不能为空")

    if not isinstance(text, str):
        raise TypeError("text 必须是字符串")

    if asr_confidence is not None:
        if not isinstance(asr_confidence, (int, float)):
            raise TypeError(
                "asr_confidence 必须是数字或None"
            )

        if not 0 <= float(asr_confidence) <= 1:
            raise ValueError(
                "asr_confidence 必须在0到1之间"
            )

    classification = classify_intent(text)

    return {
        "request_id": request_id,
        "original_text": classification[
            "original_text"
        ],
        "normalized_text": classification[
            "normalized_text"
        ],
        "intent": classification["intent"],
        "intent_confidence": classification[
            "confidence"
        ],
        "asr_confidence": (
            float(asr_confidence)
            if asr_confidence is not None
            else None
        ),
        "status": classification["status"],
        "route": classification["route"],
        "reason": classification["reason"],
        "b1_latency_ms": classification[
            "latency_ms"
        ],
    }
