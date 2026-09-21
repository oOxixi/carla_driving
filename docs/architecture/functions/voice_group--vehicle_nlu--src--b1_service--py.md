# b1_service：功能记录

上级模块：[模块说明](../modules/support-voice.md) · 实现：[voice_group/vehicle_nlu/src/b1_service.py](../../../voice_group/vehicle_nlu/src/b1_service.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [ASR、NLU、复核与命令交付](voice-command-production.md)

## 功能职责与范围

b1_service

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `process_asr_text`

源码位置：[voice_group/vehicle_nlu/src/b1_service.py 第 6 行](../../../voice_group/vehicle_nlu/src/b1_service.py#L6)。类型：`FunctionDef`。

```python
process_asr_text(request_id: str, text: str, asr_confidence: float | None=None) -> dict[str, Any]
```

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

## 内部调用与异常路径

- `process_asr_text` 调用：`TypeError`, `ValueError`, `classify_intent`, `float`, `isinstance`, `request_id.strip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `process_asr_text`，第 30 行：`TypeError('request_id 必须是字符串')`。
- `process_asr_text`，第 33 行：`ValueError('request_id 不能为空')`。
- `process_asr_text`，第 36 行：`TypeError('text 必须是字符串')`。
- `process_asr_text`，第 40 行：`TypeError('asr_confidence 必须是数字或None')`。
- `process_asr_text`，第 45 行：`ValueError('asr_confidence 必须在0到1之间')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [voice_group/vehicle_nlu/src/intent_classifier.py](../../../voice_group/vehicle_nlu/src/intent_classifier.py)

静态 import 消费者（含测试）：

- [integration/tests/test_voice_qwen_semantic_coverage.py](../../../integration/tests/test_voice_qwen_semantic_coverage.py)
- [tools/evaluate_saved_asr_nlu.py](../../../tools/evaluate_saved_asr_nlu.py)
- [tools/run_group1_voice_onnx_benchmark.py](../../../tools/run_group1_voice_onnx_benchmark.py)
- [tools/run_group1_voice_text_regression.py](../../../tools/run_group1_voice_text_regression.py)
- [voice_group/pipeline.py](../../../voice_group/pipeline.py)
- [voice_group/tests/test_manifest_regression.py](../../../voice_group/tests/test_manifest_regression.py)
- [voice_group/tests/test_safety_boundary.py](../../../voice_group/tests/test_safety_boundary.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-voice.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `voice_group/vehicle_nlu/src/b1_service.py`

来源 SHA256：`1f85b0153b974b7146d257cb881d2efbf6e4e5234f4379ee965dcb095f399e1d`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `process_asr_text` / 30 | `not isinstance(request_id, str)` | `raise TypeError('request_id 必须是字符串')` |
| `process_asr_text` / 33 | `not request_id.strip()` | `raise ValueError('request_id 不能为空')` |
| `process_asr_text` / 36 | `not isinstance(text, str)` | `raise TypeError('text 必须是字符串')` |
| `process_asr_text` / 40 | `asr_confidence is not None AND not isinstance(asr_confidence, (int, float))` | `raise TypeError('asr_confidence 必须是数字或None')` |
| `process_asr_text` / 45 | `asr_confidence is not None AND not 0 <= float(asr_confidence) <= 1` | `raise ValueError('asr_confidence 必须在0到1之间')` |
