import re


# 通常不影响车控指令核心含义的礼貌词
POLITE_WORDS = [
    "麻烦你",
    "麻烦",
    "请你",
    "请",
    "帮我",
    "帮忙",
    "劳驾",
]


# 将含义相同的表达统一成固定写法
SYNONYM_MAP = {
    # 变道相关
    "并一下线": "变道",
    "并个线": "变道",
    "并线": "变道",
    "换个车道": "变道",
    "换一下车道": "变道",
    "换道": "变道",

    # 方向相关
    "靠右停车": "靠右侧停车",
    "左边": "左侧",
    "右边": "右侧",

    # 停车相关
    "停下来": "停车",
    "停下去": "停车",
    "把车停住": "停车",
    "停一下": "停车",
    "刹住": "停车",

    # 加速相关
    "开快一点": "加速",
    "开快一些": "加速",
    "提高车速": "加速",
    "提点速": "加速",
    "加点速": "加速",

    # 减速相关
    "开慢一点": "减速",
    "开慢一些": "减速",
    "降低车速": "减速",
    "放慢速度": "减速",
    "减点速": "减速",
}



def normalize_text(text: str) -> str:
    """
    对ASR输出文本进行基础清洗和同义表达统一。

    参数:
        text: ASR识别得到的原始文本。

    返回:
        标准化后的文本。

    示例:
        输入：麻烦往左边并一下线。
        输出：往左侧变道
    """

    if not isinstance(text, str):
        raise TypeError("text 必须是字符串")

    # 删除首尾空格
    normalized = text.strip()

    # 删除标点符号、换行、空格
    normalized = re.sub(
        r"[\s，。！？、,.!?；;：:“”\"'（）()【】\[\]]",
        "",
        normalized,
    )

    # 长礼貌词优先删除，例如先处理“麻烦你”，再处理“麻烦”
    polite_words = sorted(
        POLITE_WORDS,
        key=len,
        reverse=True,
    )

    for word in polite_words:
        normalized = normalized.replace(word, "")

    # 长同义短语优先替换
    replacements = sorted(
        SYNONYM_MAP.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for source, target in replacements:
        normalized = normalized.replace(source, target)

    return normalized
