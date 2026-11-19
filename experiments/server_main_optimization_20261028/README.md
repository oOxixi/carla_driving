# main_optimization 历史优化交付

服务器 `carla-driving-main-optimization` 对应 `f92ac6fcc8e8c55e3b3a63825b6f4386d49b6d78`，相对冻结基线 `a05c8b76efcd4c176965223c661f40b153cb1836`。这里保留独立 [源码差分](source.patch) 和 [阶段报告](docs/reports/)，不将未晋级实验打开为生产默认。

收录场景合同、回归验证、Qwen 归因探针、组合指令抽取、数值/方向槽位矛盾校验、负结果和复现入口。开发 12 题的联合抽取基线为 **9/12**；分句及中文动作名方案各 **7/12**，均未晋级。四题探针为 **1/4**。详见[多步语义复盘](docs/reports/main_optimization_qwen_semantic_followup_20261028.md)。

在冻结基线的临时工作树上可用 `git apply --check /path/to/source.patch` 检查源文件差分；不要对当前生产工作树应用。生成的原始材料和历史终态以原报告为准。
