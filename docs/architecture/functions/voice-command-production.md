# 音频到驾驶命令：识别、语义解析与复核

上级：[语音模块](../modules/support-voice.md)。

## 真实入口与运行状态

[pipeline.audio_to_command](../../../voice_group/pipeline.py) 支持音频路径或 16kHz 单声道数组，并可接收采音起点 `t_audio_start_ns`。ASR、verifier 与 cascade config 缓存在模块级变量中，首次调用与预热后延时不能混为一谈。

`preload_voice_models` 预先加载主 ASR、以文本预热 NLU，并按 cascade enabled 决定是否预热复核器。它记录各阶段加载耗时，目的在于把加载成本与实际指令处理分开。

## 输入转命令的分层

主 ASR 转写 → B1 `process_asr_text` → B2 `parse_command` → 按 cascade 条件复核 → DrivingCommand envelope。B1/B2 的角色名属于语音组内部，不等于挑战赛道 B1 数据采集/B2 评测。

解析槽位会进入 parameters，但是否授权仍由下游 voice adapter 判定。NLU 返回 intent 并不保证 status valid、参数齐全或无需确认；改变解析规则时不能只断言 intent 字符串正确。

## 维护时需要特别查的行为

- 文本路径与音频路径共享部分 NLU，但音频有 ASR confidence、复核、模型加载与时间戳；文本回归通过不能替代音频噪声/方言验证。
- 复核不可用与复核一致是不同结果，不能静默当成已经二次确认。
- 时间戳记录延时；valid_duration_s 决定命令有效期，二者不能混用。
- 直接运行脚本与包导入有两组 import 分支，这是保留的兼容入口，不宜删一组后只测另一组。

## 修改一个意图的阅读顺序

先定位语义分类/slot parser，再查 pipeline 输出 envelope，接着查 integration.voice_adapter 和 canonical 转换，最后检查该 intent 是否能映射执行行为。需要确认的命令不得通过放宽 confidence/status 校验来“支持”。

测试定位：[voice_group/tests](../../../voice_group/tests)、[voice adapter tests](../../../integration/tests/test_voice_adapter.py)、[compound routing](../../../integration/tests/test_voice_compound_routing.py)。当前全量发现中两个音频测试缺 soundfile 环境依赖，不能将此问题归为 NLU 实现错误。
