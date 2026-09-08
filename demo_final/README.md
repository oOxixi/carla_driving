# CARLA 语音 + Qwen-VL 集成驾驶决策演示

## 项目架构

```
语音组 (voice_group/)
  音频 -> VAD -> SenseVoice(ASR) -> B1意图 -> B2槽位 -> DrivingCommand
                    |
CARLA传感器           |  LiDAR (距离/TTC) + RGB摄像头 + 碰撞检测
                    |  |
                    v  v
              Qwen-VL API (安全优先prompt + 结构化感知数据 + RGB图像)
                    |
                    v
              D安全层 (TTC < 1.5s 或 前车距离 < 5m -> 强制紧急制动)
                    |
                    v
              最终驾驶决策
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `test_carla_timing.py` | 集成测试脚本：语音管线 + CARLA LiDAR感知 + Qwen-VL + D安全层 |
| `demo_scene.json` | 场景定义：25m处行人横穿 + 40m处障碍车 |
| `results/` | 自动生成：CARLA截图 + 每轮计时/决策JSON |

## 依赖（已在项目中，通过sys.path引用）

- `voice_group/pipeline.py` — audio_to_command (VAD + ASR + NLU)
- `voice_group/asr_vad.py` — SenseVoice ASR + LoRA适配器
- `voice_group/vehicle_nlu/` — B1意图分类器
- `voice_group/nlu_b2/` — B2槽位解析器
- `integration/qwen_remote_backend.py` — OpenAI兼容Qwen-VL后端
- `car_control_A/` `car_control_B/` `car_control_C/` `car_control_D/` — 控制模块

## 环境要求

```cmd
# 需预装 .venv-voice (Python 3.12)
.venv-voice\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu130
.venv-voice\Scripts\python.exe -m pip install -r voice_group\requirements.txt
.venv-voice\Scripts\python.exe -m pip install sounddevice opencv-python openai Pillow
.venv-voice\Scripts\python.exe -m pip install D:\CARLA_Latest\PythonAPI\carla\dist\carla-0.9.16-cp312-cp312-win_amd64.whl
```

## 模型路径

模型需预下载到纯ASCII路径（中文用户名会导致sentencepiece报错）：

```cmd
set SENSEVOICE_MODEL_PATH=D:\...\models\SenseVoiceSmall
set FSMN_VAD_MODEL_PATH=D:\...\models\FSMN_VAD\models\iic--speech_fsmn_vad_zh-cn-16k-common-pytorch\snapshots\master
set VOICE_CASCADE_ENABLED=0
```

## 快速启动

### 1. 启动 CARLA (PowerShell)

先清理可能残留的 CARLA 进程，再启动（只启动一个实例）：

```powershell
Get-Process CarlaUE4-Win64-Shipping -ErrorAction SilentlyContinue | Stop-Process -Force
D:\CARLA_Latest\CarlaUE4.exe -quality-level=Low -carla-port=2000 -nosound -dx12 -windowed -ResX=800 -ResY=600
```

等待约 30-60 秒，确认端口就绪：

```powershell
Test-NetConnection 127.0.0.1 -Port 2000
```

说明：

- 脚本会自动等待 CARLA 世界真正运行（快照帧推进）后再初始化传感器，无需手动精确计时；
- 若不需要查看 3D 窗口，可用离屏模式：`D:\CARLA_Latest\CarlaUE4.exe -quality-level=Low -carla-port=2000 -nosound -dx12 -RenderOffScreen`；
- 不要重复启动多个 CARLA 实例。

### 2. 设置API密钥 (CMD)

```cmd
set OPENAI_BASE_URL=https://api.siliconflow.cn/v1
set OPENAI_API_KEY=你的密钥
set QWEN_MODEL=Qwen/Qwen3-VL-32B-Instruct
```

### 3. 运行测试

```cmd
.venv-voice\Scripts\python.exe test_carla_timing.py
```

### 4. 选择测试场景（可选）

脚本启动时会先弹出场景选择菜单（Enter 默认选第 1 个），也支持直接指定：

```cmd
rem 按文件名或序号指定
.venv-voice\Scripts\python.exe test_carla_timing.py --scene DEMO_02_front_obstacle.json
.venv-voice\Scripts\python.exe test_carla_timing.py --scene 3

rem 通过环境变量指定
set DEMO_SCENE=DEMO_06_clear_road.json
.venv-voice\Scripts\python.exe test_carla_timing.py

rem 只列出场景，不启动
.venv-voice\Scripts\python.exe test_carla_timing.py --list-scenes
```

场景文件位于 `scenarios/` 目录，每个场景包含：地图/天气、自车出生点与初始速度（`ego_spawn.initial_speed_kph`，设为 0 则静止）、障碍物与行人（含行为：横穿/静止/匀速前进）、传感器配置、建议测试指令。

## 场景列表

| 文件 | 场景 | 天气 | 测试重点 |
|------|------|------|---------|
| `DEMO_01_pedestrian_crossing.json` | 行人15m横穿 + 障碍车40m | ClearNoon | 基础：语音“加速”被D安全层/Qwen拦截 |
| `DEMO_02_front_obstacle.json` | 前车静止25m | ClearNoon | 紧急制动 + Qwen变道判断 |
| `DEMO_03_overtake_slow_car.json` | 前方慢车30m匀速2.5m/s | ClearNoon | 动态跟车/超车、接近触发安全层 |
| `DEMO_04_multi_pedestrian.json` | 双行人错峰横穿(15m/25m) | CloudyNoon | 多障碍物连续感知 |
| `DEMO_05_night_rain.json` | 夜间大雨行人12m | HardRainNight | 恶劣天气感知 + 安全兜底 |
| `DEMO_06_clear_road.json` | 空旷直道无障碍物 | ClearSunset | 基础指令：加速/定速/减速/停车 |

## 测试流程

每次录音循环执行以下步骤：

1. **录音** — 按Enter开始/停止麦克风录制
2. **语音管线** — audio_to_command(): VAD -> SenseVoice ASR -> B1意图 -> B2槽位 -> DrivingCommand
3. **CARLA同步** — 世界tick + 读取LiDAR + RGB摄像头 + 碰撞传感器
4. **感知计算** — 前方距离(LiDAR)、TTC(距离/速度)、碰撞事件
5. **Qwen-VL** — 发送RGB图像 + 结构化感知数据 + 语音文本（含安全优先提示词）
6. **D安全层** — 独立代码级检查：TTC<1.5s 或 前车距离<5m -> 强制EMERGENCY_STOP
7. **最终决策** — D安全层触发时覆盖Qwen决策；否则采用Qwen决策

## 测试指令

| 说出 | 预期结果 |
|------|---------|
| "减速" | 简单指令 -> 语音直出 SLOW_DOWN |
| "加速" | 应触发D安全层 EMERGENCY_STOP（前方有行人） |
| "靠边停车" | Qwen评估安全位置，D安全层检查距离 |
| "变道" | 复杂指令 -> Qwen结合视觉场景判断 |

## 输出示例

```
  ==============================================================
  |  #1  Voice: SLOW    conf:95%  "加速。"
  |
  |  [Voice] ASR=109ms  NLU=15ms  Total=156ms
  |  [Perception] front=2.9m  ttc=0.8s  collision=False
  |
  |  Timing: voice=156ms  carla_tick=16ms  qwen=2640ms  total=2812ms
  |  [D-Safety] OVERRIDE: EMERGENCY_STOP (FRONT_OBSTACLE(2.9m))
  |  [Qwen-VL] EMERGENCY_STOP  conf:100%
  |  FINAL: EMERGENCY_STOP (D-SAFETY) conf:100%
  |  Reason: FRONT_OBSTACLE(2.9m)
  |  Snap: snap_08597e9b.jpg
  ==============================================================
```

## 结果保存

每次运行自动保存到 `results/`：
- `snapshots/*.jpg` — CARLA截图
- `run_YYYYMMDD_HHMMSS.json` — 每轮完整记录：音频时长、ASR文本、意图、置信度、语音延迟分解、感知数据(front_distance/TTC)、D安全层动作、Qwen决策、最终动作
- `run_YYYYMMDD_HHMMSS_summary.txt` — 可读摘要

## 安全架构

两层独立安全机制：

| 层级 | 机制 | 触发条件 |
|------|------|---------|
| **Qwen-VL提示词** | 安全优先指令 + 感知数据传入prompt | 视觉障碍物检测 |
| **D安全层代码** | 硬编码规则，本地运行 | TTC<1.5s、前车距离<5m、碰撞检测 |

D安全层**始终优先生效**。即使Qwen误判场景，本地TTC/距离检查也会强制执行EMERGENCY_STOP。

## 延迟分解

| 环节 | 典型耗时 | 说明 |
|------|---------|------|
| 语音 (VAD+ASR+NLU) | ~150ms | SenseVoice on RTX 4060 CUDA |
| CARLA tick + LiDAR | ~16ms | 同步模式 |
| Qwen-VL API | ~1500-3000ms | 取决于网络 (SiliconFlow免费版) |
| **合计** | **~1700-3200ms** | |

## 已知问题

1. **RTX 4060 驱动 580.88**：必须使用 `-dx12` 参数。`-dx11` 下 RGB 摄像头收不到任何帧（LiDAR 正常），带摄像头的 tick 会把 CARLA 服务端卡死（脚本超时、进程无响应）；`-vulkan` 亦不可用
2. **显存 (8GB)**：SenseVoice + CARLA共用GPU，推荐低分辨率 (800x600)
3. **Qwen级联验证器**：已禁用 (`VOICE_CASCADE_ENABLED=0`) — HuggingFace被墙
4. **ffmpeg**：未安装，使用torchaudio加载音频（功能正常，不影响识别质量）
5. **FsmnVADStreaming**：FunASR 1.4.0 API变更，模型名从 `fsmn-vad` 改为 `FsmnVADStreaming`
6. **PeftModel**：基础模型需先移至CUDA再包装PeftModel（已在asr_vad.py中修复）
7. **CARLA 启动初期不稳定**：新启动的 CARLA 需要等待世界真正开始运行（脚本已内置帧推进等待）；在加载完成前调用 tick 可能让服务端卡死，此时需重启 CARLA 再运行脚本
8. **地图加载**：本机加载新地图（如 Town03）会触发 shader 编译崩溃（`LOWLEVELFATALERROR ... SHADER COMPILATION FAILURE`），脚本默认使用当前地图（场景演员按自车相对位置生成，任意地图可跑）；确需切图时设 `DEMO_FORCE_MAP=1`（有崩溃风险）
