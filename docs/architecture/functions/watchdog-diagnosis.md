# WATCHDOG_ALERT与持续停车

上级：[安全](../modules/vehicle-safety.md)、[运行入口](../modules/vehicle-entry.md)。关联：[路线](route-control-progress.md)、[C/D](longitudinal-safety-contract.md)。基线fe1ba839，2026-09-20。

[runner](../../../integration/carla_runner.py)将watchdog_alerts具体原因保存到perception_sources['runtime_alerts']。来源可为感知、Qwen/bridge、路线不可行、控制来源错误或RUNTIME_WATCHDOG_TIMEOUT。汇总WATCHDOG_ALERT不能直接证明心跳超时。

定位顺序：首次告警前后的连续帧 → runtime_alerts/原始异常 → route progress/remaining和车速 → command/step → [ControlRuntime](../../../integration/runtime_loop.py)及安全锁存/恢复 → 最终brake。记录run身份、帧号、模拟时间与墙钟；停车可能是保护结果，路线不更新也可能是停车结果，需区分先后。

真实超时查心跳/阻塞；路线错误查建立/刷新/恢复；感知故障查同步/来源；锁存查明确恢复条件。不能为采集继续运行直接取消安全锁存。最终实际执行值应与D前raw control区分。

回归需要正常long、同故障注入、允许恢复/禁止恢复分支；本轮未执行闭环。S2约37.5m停滞来自成员报告，首次日志未取得；S2 GEN差异已发现，但与停车因果未证实，见[Wave2](wave2-audit.md)。
