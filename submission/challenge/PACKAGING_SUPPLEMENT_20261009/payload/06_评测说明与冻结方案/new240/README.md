# 可选新 240 槽补采入口

GitHub 补丁仅包含本说明和执行脚本，须先安装至原完整材料目录。冻结／cases 资料不在补丁内：脚本实际读取同目录 `freeze/` 下的锁、slots、policy 和 `scenarios/`。该目录须已由原完整材料保留或从其原冻结 ZIP 原样取出；未补齐不能运行，不能以空模板代替。

这是团队可选补采材料，不阻塞现有材料整理。官方已有自建评测数据足以说明当前提交范围；新 240 槽方案不能写成已采数据或已通过的评测。

`freeze/` 从既有 `B2_PROSPECTIVE_BENCHMARK_FREEZE_V1_20261008.zip` 原样安全解出，共 248 个文件，包含 Seen／Variant／Unseen 各 80 个场景合同、原 seed、slot、policy 与冻结锁。该目录仍为 `ACQUISITION_AND_POLICY_FROZEN_AWAITING_COLLECTION`；不要修改冻结文件、阈值、分母、场景或采集顺序。

## 静态列出任务

在本目录执行：

```powershell
python run_frozen_collection.py --list-only
```

此命令只读取冻结文件、核对关键文件与场景哈希，列出 240 槽，不启动 CARLA、Teacher 或模型，不生成采集数据。

## 有真实环境后执行

需要 CARLA、源码依赖，以及支持 `ModelRequest → ManeuverPlan`、提供 `/infer` 的固定 Teacher v4 服务。`--teacher-url` 填规划服务基地址，不能填裸 vLLM `/v1`。需要现有真实服务身份 JSON，字段值应与 `freeze/FREEZE_LOCK.json` 中 `collection_requirements` 一致：`teacher_git_sha`、`teacher_model_id`、`teacher_model_revision`、`teacher_profile`、`teacher_artifact_fingerprint_sha256`。不要为通过检查而编造身份文件。脚本只比较该证据，不替服务端提供独立身份认证，也不向运行日志强行注入 Teacher 身份或标注。

```powershell
python run_frozen_collection.py --host 127.0.0.1 --port 2000 --teacher-url http://真实Teacher规划服务:8100 --teacher-identity 真实服务身份.json --realtime --follow-spectator
```

脚本以本包 `02_源码与部署/source` 为工作目录，逐槽使用冻结场景与 seed 调用 `integration.carla_runner`，记录命令、退出码、控制台输出和原始 JSONL。完成后调用 `challenge.dataset.collector`，每个日志单独使用可重复的 `--input-log`。输出默认写入 `new240/collection_runs/时间戳/`；自定义 `--output-dir` 也必须是 new240 下的新目录且不得位于 freeze 中。已有输出不会覆盖，不自动重试失败槽。

`collector_accepted_raw.jsonl` 仅为 collector 接受的原始记录，并不自动成为冻结 case set。正式评测前还须按原 policy 检查真实 Teacher 身份、每槽命令序号、第一条质量有效结果、槽位完整性及泄漏；失败记录、原始分母必须保留。禁止看到模型结果后替换或排除槽，禁止用存储 Teacher 计划冒充本轮实际采集。本入口不运行 Student、不签发 Gate、不声称通过 240 场。

当前机器无 CARLA／固定 Teacher 环境，只进行了静态检查及 `--list-only`；未实际采集、未生成新标签或新评测结果。源 ZIP、原报告及现有材料保持原样，未创建 ZIP。
