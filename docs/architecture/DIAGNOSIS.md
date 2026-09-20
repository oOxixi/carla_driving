# 从故障到代码与证据

返回[总索引](README.md)。基线 fe1ba839，2026-09-20。文档记录代码机制，不自动证明历史运行使用相同版本。

| 现象 | 首查对象 | 定位记录 |
|---|---|---|
| base正常、GEN失败 | 选中JSON及base版本、commands/oracle | [场景来源](functions/scenario-lineage.md) |
| STOP正确但目标失败 | 原始Plan是否有target，再查aliases | [目标身份](functions/target-grounding.md) |
| extension通过但最终FAILED | summary.acceptance.failed_keys及上游completion | [验收合成](functions/acceptance-diagnosis.md) |
| WATCHDOG_ALERT持续停车 | 首次runtime_alerts及告警前帧 | [故障停车](functions/watchdog-diagnosis.md) |
| 样本未进入训练 | release split、view排除记录、cohort资格 | [发布与视图](functions/dataset-release-view.md) |
| 模型成绩与部署不一致 | 实际权重SHA、config、dataset与报告身份 | [晋级](functions/checkpoint-and-promotion.md) |
| 时延异常 | 原始trace、重复阶段、时钟域 | [HIL](functions/hil-trace-semantics.md) |

## 定位顺序

1. 锁定实际Git SHA、模型manifest、启动参数、scenario/selection哈希。以run、command、request/plan身份和帧时间串联，不能按相似文件名关联。
2. 缺证据时沿collector输出参数、启动命令、宿主/容器路径映射及manifest来源查找，记录已查位置。远端运行文件不在本地不等于不存在。
3. 从失败判据的required/actual反查字段生产者，区分输入缺失、转换丢失、时序错配与消费者契约错误。
4. 纯函数复现只证明局部机制；实际run根因需版本对应和必要的同seed单变量对照。未知原因保持未知。
5. 将发现登记[AUDIT](AUDIT.md)，连接功能页、受影响消费者和回归入口；不是只补说明文字。

## 有效性验收

每项问题应能回答：谁产生、谁消费、哪项判据失败、原始证据在哪里、如何关联、修改影响谁、如何验证。缺项必须明确记录，不能称根因已闭合。链接有效与文件覆盖不等于诊断能力。

全项目见[追踪矩阵](TRACEABILITY.md)，真实案例见[Wave2记录](functions/wave2-audit.md)。
