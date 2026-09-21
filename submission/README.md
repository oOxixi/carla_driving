# 比赛提交材料

> 本目录现有模板主要面向基础赛道。挑战赛道 Student/J6P 的 Candidate 台账、Final Freeze、
> Release Manifest、Docker 和提交包门禁见
> [`docs/modules/B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md`](../docs/modules/B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md)。
> 在挑战赛道专用 validator 实现并通过前，现有打包检查 PASS 不能表示挑战赛道 Final 完整。

- `current/technical_solution.md`：当前技术方案源文件。
- `templates/DEMO_RECORD.md`：每个正式场景的人工演示记录模板。
- `templates/EVIDENCE_INDEX.json`：证据文件、哈希、范围和结果索引模板。

真实运行日志先生成到 `artifacts/`。只有已核对场景 ID、代码提交、模型版本、原始文件
哈希和声明范围的材料才能进入最终提交包。本地代理集通过不能表述为官方隐藏测试通过。
