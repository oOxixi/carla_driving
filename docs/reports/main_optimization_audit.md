# main_optimization 优化审计

## 基线与原则

- 冻结基线：`origin/main@a05c8b76efcd4c176965223c661f40b153cb1836`。
- 本分支从该 SHA 直接创建，未改写 `main`。
- 不针对某一个已通过场景调 A/B/C/D 控制参数，不把延迟或准确率代理结果写成正式成绩。
- 优化集中在模型身份、决策输入准确性、失败关闭、可操作性和可审计性。

## 发现并解决的问题

| 问题 | 风险 | 处理 |
|---|---|---|
| 正式 runner 默认 Qwen3.5-2B，但远程 profile 仍默认旧 GPTQ | 不同入口实际使用不同模型 | 建立唯一生产 profile，固定 model、revision、artifact 指纹、224 图像和 64 token |
| 返回 token 与 logprob 不对应时借用首个 logprob | 错误置信度可能被当成可信决策 | token 不匹配立即失败关闭，并增加反例测试 |
| 多目标拼图只按距离选两个目标 | 语音点名的较远目标可能不进入重点画面 | 明确语义目标优先，再按距离和置信度排序 |
| 健康检查只看 production-ready | 错模型、错 revision、错模式也可能放行 | 严格核对 exact model、revision、artifact、planner_v2 与 CARLA |
| S2/S3 启动脚本只检查连通或“名称含 2B” | 无法证明正式模型与服务模式 | 正式运行前执行严格健康门禁并保存 JSON |
| Qwen 服务与 runtime 测试未被默认 pytest 收集 | 局部服务回归可能被隐藏 | 纳入 pytest testpaths，并恢复可嵌入 HTTP server 工厂 |
| 文档仍描述“简单命令不调用 Qwen” | 与当前全指令 Qwen 合同冲突 | 统一场景说明、技术方案和远程运行手册 |
| 缺少一次命令的评委验收入口 | 现场证据分散、难复查 | 新增静态/在线一键验收，输出 JSON 与 Markdown |

## 当前生产模型合同

| 字段 | 值 |
|---|---|
| profile | qwen3.5-2b |
| model | Qwen/Qwen3.5-2B |
| exact revision | 15852e8c16360a2fea060d615a32b45270f8a8fc |
| artifact SHA-256 | 4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa |
| protocol | planner_v2 / ManeuverPlan V2 |
| visual budget | 224 x 224 / 64 tokens |

旧 Qwen3-VL GPTQ/FP8 仅保留为 RTX 5070 历史诊断资料，不能用于新的正式证据。

## 本地静态验证

本分支修改后已完成：

- `python -m pytest -q`：1167 passed，4 skipped。
- `python tools/validate_scenarios.py`：155 checked，0 failed。
- `python tools/validate_official_scenes.py`：S1、S2、S3 全部 PASS。
- PowerShell 官方场景入口的 ValidateOnly：PASS。

这些结果证明代码、接口和场景合同未回归，不等于真实 CARLA 里程、真实 Qwen
准确率或正式延迟成绩。

## 评委验收命令

仅检查仓库静态交付：

```bash
python tools/validate_judge_readiness.py
```

Qwen 与 CARLA 均启动后执行在线门禁：

```bash
python tools/validate_judge_readiness.py --require-live
```

正式报告位于 `artifacts/review/main_optimization_readiness.json` 及同名 Markdown。
正式提交时应同时保留各场景 runner 生成的原始 JSONL、场景结果和评分报告。

## 尚未冒充完成的工作

- 当前 Windows 本地没有运行 CARLA 物理闭环，因此没有生成新的 S1/S2/S3 里程成绩。
- 当前分支没有声称模型准确率百分比提高；语义目标优先是可测试的输入改进，实际收益
  仍应在冻结数据和服务器闭环上比较。
- 服务器启动新代码后必须显式提交已核验的 revision 与 artifact 指纹，否则生产
  Qwen 服务拒绝启动。
