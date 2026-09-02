# 官方三场景构建包（第二组成员1）

本目录将比赛文件中的三类场景落实为 CARLA 0.9.16 场景合同，并接入仓库唯一正式入口
`python -m integration.carla_runner`。本包负责地图、天气、路线、传感器、真实 Actor、固定
随机种子、事件触发和证据字段，不修改 B/C/D 控制算法。

正式运行强制使用 `--qwen-mode planner_v2`。S1/S2 的每条正常业务指令必须经过 Qwen；
S3 的雨夜安全车速与施工组合指令经过 Qwen，而加塞和行人 `EMERGENCY_STOP` 按安全架构
直接走本地快速链路，不能为等待模型而延迟制动。Qwen 只输出高层 ManeuverPlan，最终控制
仍须经过状态机、横纵向控制和安全仲裁。

## 本地是否需要 CARLA

只构建和检查场景 JSON 时不需要 CARLA。在当前电脑运行下面的命令即可完成静态检查：

```powershell
py -3.12 tools/validate_official_scenes.py
powershell -ExecutionPolicy Bypass -File scripts/run_official_scenes.ps1 -ValidateOnly
```

只有以下工作需要另一套已安装 CARLA 0.9.16 且已启动生产 Qwen 服务的系统：地图/蓝图
实物检查、Actor 穿模检查、完整里程闭环、事件实触发，以及截图或视频录制。确定性测试
后端只能用于开发，不能生成正式比赛证据。

## 三个场景最终效果

### S1 基础语音操控（Town05，5km）

- 画面是晴天正午、视野清晰的城市主干道；场景不生成任何背景车辆或行人，保证无动态干扰。
- 运行器在 Town05 中选择可支持右转的真实道路拓扑，路线总合同长度为 5000m。
- 依次触发保持车道并提速至 60km/h、右转前减速至 25km/h、出弯回正、向左变道、减速至 40km/h。
- 车上挂载前视 RGB、LiDAR、Radar、碰撞和压线传感器；日志必须包含速度、方向盘、车道偏差、路线偏差、碰撞、压线和红灯违规。
- 最终演示应看到车辆在空旷道路上平稳提速，进入首个可用右转路口，转向后自动回正，再完成一次平顺左变道，持续跑满 5km。

### S2 复杂避障（Town03，8km）

- 画面是阴天傍晚低光的城市次干道和十字路口，前 150m 内集中布置公交站交互、横穿行人、慢车、相邻车和自行车。
- 公交车会停在道路前方，两名乘客在站点侧活动；随后一名行人横穿道路。更远处有慢车和右前方低速自行车，形成连续组合任务。
- 指令链覆盖公交站减速与继续、行人减速让行、左变道超越慢车并回归、非机动车安全避让并回归。
- 使用前/左/右/后四视角 RGB 的严格同帧采集，按“前/左、右/后”拼成 Qwen 视觉输入；
  同时把 LiDAR、Radar 与车辆状态融合为结构化感知送入 Qwen。
- 最终演示应看到自车先在公交站前把速度降稳，等行人清空驾驶走廊，再检查相邻车道、超越慢车、回到原路线，最后以不小于 3m 的间距通过自行车，之后继续完成 8km。

### S3 极限应急（Town04，6km）

- 画面是强降雨夜间：100% 湿滑路面、明显雨雾、低太阳高度角和道路反光；道路选在 Town04 城市快速路。
- 五个实体锥桶从车道右侧逐渐向内收拢，配合施工警示牌形成可见的车道收窄。
- 一辆实体车辆在自车接近至 32m 后才从左侧相邻车道按确定性转向窗口向右切入；之后一名行人以 2.4m/s 临时横穿。
- 指令链覆盖雨夜安全车速、施工减速左并道、加塞紧急制动、行人紧急停车和 STOP hold。
- 同样使用四视角 RGB + LiDAR + Radar；低光视觉不稳定时，LiDAR 距离和 TTC 仍是硬安全依据。
- 最终演示应看到自车在锥桶前减速并向左并道，遇到加塞立即制动而不继续加速，遇到行人后完全停车并保持制动，危险解除后才能由后续控制逻辑恢复，随后完成 6km。

## 对象与事件速查

| 场景 | 固定 seed | 路线 | 实体对象 | 关键触发 |
|---|---:|---:|---|---|
| S1 | 20260101 | 5km | 无动态对象 | 右转、左变道、提速/减速 |
| S2 | 20260202 | 8km | 公交车、2名乘客、横穿行人、慢车、相邻私家车、自行车 | 距离公交/行人/慢车/自行车阈值 |
| S3 | 20260303 | 6km | 施工牌、5个锥桶、加塞车、横穿行人 | 施工距离、加塞距离、行人距离 |

## 在另一套 CARLA 系统验证

先启动 CARLA 0.9.16 和生产 Qwen Planner V2 服务。Qwen 服务与 runner 共享仓库根目录作为
`--image-root`，并确认 `GET /health` 返回 `status=READY`、`production_ready=true`。然后从
仓库根目录执行：

```powershell
$env:QWEN_SERVICE_URL = 'http://127.0.0.1:18000'

# 每个场景先跑30秒冒烟测试，检查地图、传感器和Actor是否成功生成
powershell -ExecutionPolicy Bypass -File scripts/run_official_scenes.ps1 -Scene S1 -Smoke
powershell -ExecutionPolicy Bypass -File scripts/run_official_scenes.ps1 -Scene S2 -Smoke
powershell -ExecutionPolicy Bypass -File scripts/run_official_scenes.ps1 -Scene S3 -Smoke

# 冒烟通过后再完整运行；完整里程会耗时
powershell -ExecutionPolicy Bypass -File scripts/run_official_scenes.ps1 -Scene S1
powershell -ExecutionPolicy Bypass -File scripts/run_official_scenes.ps1 -Scene S2
powershell -ExecutionPolicy Bypass -File scripts/run_official_scenes.ps1 -Scene S3
```

运行日志位于 `artifacts/logs/official_competition/`。每次验证请保留 JSONL 和同名 summary，
并录制带 spectator 视角的短视频。建议在下列时刻各截一张图：场景刚加载、关键对象出现、
安全动作生效、事件结束/回归路线。

## 首轮实机检查清单

1. 控制台显示正确的 `scenario_id / map / seed / sensor_profile`。
2. Ego、所有声明 Actor 和传感器均生成成功，无 `blueprint not found` 或 `cannot spawn`。
3. S1 所选道路确为同向至少3车道，且右转路口位置与“前方300米”语义相符。
4. S2 公交与乘客不穿模，横穿行人确实进入驾驶走廊，慢车和自行车均在可检测范围内。
5. S3 锥桶形成连续收窄但保留左侧可行空间，加塞车真实跨入自车车道，行人能完整横穿。
6. 四视角场景日志中存在 `rgb_left/rgb_right/rgb_rear` 的同帧来源标记。
7. S1/S2 每条指令均有 `QWEN_PLAN` 路由、请求、计划、步骤和唯一终态；S3 恰有2次 Qwen
   请求，两个 `EMERGENCY_STOP` 为 `FAST_LOCAL`，并有安全抢占原因。
8. 碰撞、压线、TTC、最小距离、路线偏差、Qwen 延时、sensor-to-control、指令终态和
   安全覆盖均写入结果日志。

如出现生成失败，请把控制台最后 100 行、对应场景 JSON、CARLA 服务端版本和生成的
`.summary.json` 一并带回；这些信息足以定位是地图锚点、蓝图、碰撞盒还是触发阈值问题。

## 第二组成员3：S2 服务器验收

Linux 服务器从仓库根目录执行下列命令。`--smoke` 只验证启动、传感器、Actor 和 Qwen
请求链路；8km 正式结果必须使用 `--run`。脚本会拒绝非生产 Qwen 后端，正式运行结束后
自动生成同名 `.member3.json` 验收报告。

```bash
export QWEN_SERVICE_URL=http://127.0.0.1:18000
bash scripts/run_official_s2_member3.sh --validate
bash scripts/run_official_s2_member3.sh --smoke
bash scripts/run_official_s2_member3.sh --run
```

成员3报告只有在以下证据同时满足时才通过：5条正常指令全部经 `QWEN_PLAN`；公交站减速、
行人避让、慢车超越、自行车避让五阶段全部完成；两个避障计划均出现驶出、通过、返回并恢复
原8km任务路线；自行车观测最小距离不低于3m；路线偏差不超过1m；碰撞和非计划车道侵入
均为0；Qwen sensor-to-trajectory 最大延迟不超过150ms。原始合法车道线跨越次数另存为
`lane_marking_crossing_count`，不会混同为违规侵线。

## 第二组成员4：S3 服务器验收

成员4只运行 S3，继续使用项目现有 7B Qwen Planner V2 服务：

```bash
export QWEN_SERVICE_URL=http://127.0.0.1:18000
export QWEN_MODEL=Qwen/Qwen2.5-VL-7B-Instruct-AWQ
bash scripts/run_official_s3_member4.sh --validate
bash scripts/run_official_s3_member4.sh --smoke
bash scripts/run_official_s3_member4.sh --run
```

正式报告要求四阶段全部完成、2 次 `QWEN_PLAN` 与 2 次 `FAST_LOCAL` 路由正确，加塞和
行人事件均具备危险、感知、决策、安全接管、控制生效时间戳；应急响应 P95 不超过100ms、
最大值不超过120ms；碰撞和违规为0，最终停车保持。详细字段与故障复现见
`docs/member4_s3_acceptance.md`。
