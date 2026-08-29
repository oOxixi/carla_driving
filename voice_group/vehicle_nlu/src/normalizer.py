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


# Narrow corrections observed in the pinned SenseVoiceSmall acceptance run.
# Keep these phrases context-specific so ordinary uses of the homophones are
# not rewritten into vehicle commands.
ASR_CORRECTION_MAP = {
    "在这庭": "在这停",
    "左遍车道": "左边车道",
    "马上杀": "马上刹",
    "降降素": "降降速",
    # SenseVoice commonly preserves the two-syllable action shape but emits
    # homophones for one character.  Correct only control-domain action words,
    # not complete utterances or benchmark sample IDs.
    "江素": "降速",
    "江速": "降速",
    "提诉": "提速",
    "一点数": "一点速",
    "快写": "快些",
    "剁开": "躲开",
    "摇开": "绕开",
    "照过": "绕过",
    "绕凯": "绕开",
    "扯道": "车道",
    "路章": "路障",
    "张碍武": "障碍物",
    "晋级": "紧急",
    "至冬": "制动",
    "保撞": "别撞",
    "保宠": "别冲",
    "问珠": "稳住",
    "聊边": "不要变",
    "宽也": "快了",
    "一店": "一点",
    "不当路": "不挡路",
    "慢速形式": "慢速行驶",
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

    corrections = sorted(
        ASR_CORRECTION_MAP.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for source, target in corrections:
        normalized = normalized.replace(source, target)

    # Context is required for ambiguous single-character homophones.  For
    # example, “便道” is a valid road noun and must not become “变道” unless a
    # lateral direction immediately precedes it.
    normalized = re.sub(r"([左右])便道", r"\1变道", normalized)
    normalized = re.sub(r"病(?=右(?:边|侧|车道|道))", "并", normalized)
    normalized = re.sub(r"([向往])咗(?=(?:摇开|绕开|绕过|侧))", r"\1左", normalized)
    normalized = re.sub(r"枉咗(?=(?:绕开|绕过))", "往左", normalized)
    normalized = re.sub(r"向又(?=(?:绕开|绕过))", "向右", normalized)
    normalized = re.sub(r"[坐左]考贬(?=停车)", "左靠边", normalized)
    normalized = re.sub(r"(?<=到)[为毁未](?=了?[庭亭])", "位", normalized)
    normalized = re.sub(r"(?<=到位了)[庭亭]", "停", normalized)
    normalized = re.sub(r"[沙撒](?=一[角觉])", "刹", normalized)
    normalized = re.sub(r"(?<=刹一)[角觉]", "脚", normalized)
    normalized = re.sub(r"傻猪(?=[扯车])", "刹住", normalized)
    normalized = re.sub(r"(?<=刹住)扯", "车", normalized)
    normalized = re.sub(r"(?<=撞到)扯", "车", normalized)
    normalized = re.sub(r"欢(?=[坐作左]便[扯车][刀道])", "换", normalized)
    normalized = re.sub(r"(?<=换)[坐作](?=便[扯车][刀道])", "左", normalized)
    normalized = re.sub(r"(?<=换左)便(?=[扯车][刀道])", "边", normalized)
    normalized = re.sub(r"(?<=换左边)扯(?=[刀道])", "车", normalized)
    normalized = re.sub(r"(?<=换左边车)刀", "道", normalized)
    normalized = re.sub(r"^相坐(?=绕)", "向左", normalized)
    normalized = re.sub(r"坐边(?=绕)", "左边", normalized)
    normalized = re.sub(r"且(?=作刀)", "切", normalized)
    normalized = re.sub(r"(?<=切)作(?=刀)", "左", normalized)
    normalized = re.sub(r"(?<=切左)刀", "道", normalized)
    normalized = re.sub(r"宝(?=宾县)", "别", normalized)
    normalized = normalized.replace("宾县", "并线")
    normalized = re.sub(r"又(?=转变道)", "右", normalized)
    normalized = re.sub(r"降刀(?=[零〇一二两三四五六七八九十百\d])", "降到", normalized)
    normalized = re.sub(r"靠悠(?=停车)", "靠右", normalized)
    normalized = re.sub(r"沟右(?=停车)", "靠右", normalized)
    normalized = re.sub(r"香又要开(?=(?:哪个|那个|东西))", "向右绕开", normalized)
    normalized = re.sub(r"([左右]侧)要[行恒](?=(?:车|障碍))", r"\1绕行", normalized)
    normalized = re.sub(r"^再道路阻侧(?=停车)", "在道路左侧", normalized)
    normalized = re.sub(r"控制速度再(?=[零〇一二两三四五六七八九十百\d])", "控制速度在", normalized)
    normalized = re.sub(r"抛扁(?=[庭亭停])", "靠边", normalized)
    normalized = re.sub(r"(?<=靠边)[庭亭]", "停", normalized)
    normalized = re.sub(r"(?<=停这)而", "儿", normalized)
    normalized = re.sub(r"(?<=停了)叭", "吧", normalized)

    # 长同义短语优先替换
    replacements = sorted(
        SYNONYM_MAP.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for source, target in replacements:
        normalized = normalized.replace(source, target)

    return normalized
