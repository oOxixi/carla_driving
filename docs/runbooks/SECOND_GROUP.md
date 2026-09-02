# 第二组正式运行手册

## 1. 前置条件

- CARLA 0.9.16 已启动，Python 3.12 可导入对应 CARLA API。
- 项目现有 Qwen 7B 生产服务已启动，`GET /health` 返回 `READY` 和
  `production_ready=true`。
- 从仓库根目录运行命令，运行输出写入 `artifacts/`。

```bash
export QWEN_SERVICE_URL=http://127.0.0.1:18000
python tools/validate_scenarios.py
python tools/validate_official_scenes.py
```

## 2. 正式长里程场景

Linux 上成员 3 的 S2 全链：

```bash
bash scripts/run_official_s2_member3.sh --validate
bash scripts/run_official_s2_member3.sh --smoke
bash scripts/run_official_s2_member3.sh --run
```

Windows 上运行任意正式场景：

```powershell
$env:QWEN_SERVICE_URL = 'http://127.0.0.1:18000'
powershell -ExecutionPolicy Bypass -File scripts/run_official_scenes.ps1 -Scene S2 -ValidateOnly
powershell -ExecutionPolicy Bypass -File scripts/run_official_scenes.ps1 -Scene S2 -Smoke
powershell -ExecutionPolicy Bypass -File scripts/run_official_scenes.ps1 -Scene S2
```

`--smoke`/`-Smoke` 只检查地图、Actor、传感器和 Qwen 请求链路，不代表完成规定里程。

## 3. 通用服务脚本

需要启动仓库兼容服务并运行普通场景时使用：

```bash
bash scripts/run_full_pipeline.sh start
bash scripts/run_full_pipeline.sh check
bash scripts/run_full_pipeline.sh strict-check
bash scripts/run_full_pipeline.sh status
bash scripts/run_full_pipeline.sh run --scenario-file scenarios/smoke/S01_set_speed_20.json
bash scripts/run_full_pipeline.sh stop
```

正式场景优先使用上一节的专用脚本，因为它会强制检查生产后端并生成场景验收报告。

## 4. 验收证据

每次正式运行至少保留：

- 原始逐帧 `.jsonl` 和同名 `.summary.json`；
- 模型 ID、服务健康状态、代码提交、场景 ID/map/seed；
- RGB/LiDAR/Radar 来源与帧状态；
- 每条指令的路由、Qwen 请求/计划/步骤/终态；
- 碰撞、违规侵线、路线偏差、最小距离、TTC、安全覆盖与里程完成情况。

S2 还必须运行：

```bash
python tools/validate_s2_member3_evidence.py artifacts/logs/official_competition/<run>.jsonl
```

S3 成员4使用现有 7B Qwen 服务并运行：

```bash
export QWEN_MODEL=Qwen/Qwen2.5-VL-7B-Instruct-AWQ
bash scripts/run_official_s3_member4.sh --validate
bash scripts/run_official_s3_member4.sh --smoke
bash scripts/run_official_s3_member4.sh --run
```

S3 会生成同名 `.member4.json`，并硬检查加塞/行人的五阶段应急时间戳、P95 ≤100ms、
最大值 ≤120ms、2 次 Qwen + 2 次本地快速链、停车保持、零碰撞和零违规。

不要把确定性测试后端、短时冒烟或本地代理集结果写成正式比赛闭环成绩。
