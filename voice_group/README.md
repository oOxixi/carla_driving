# 语音组交付包 · 使用说明（车辆控制组本地部署）

语音链路：音频 → SenseVoice 主识别 → 条件 Whisper 复核 → 意图(B1) → 槽位(B2) → **DrivingCommand**。
一句话调用：`from pipeline import audio_to_command`。

> ⚠️ 需要 **NVIDIA GPU + CUDA 驱动**（模型在 GPU 上跑）。纯 CPU 也能跑但很慢。

---

## 一、环境安装（照做）

**1. 建 Python 环境（推荐 conda，Python 3.10~3.12）**
```bash
conda create -n voice python=3.12 -y
conda activate voice
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

**2. 装 PyTorch —— 必须匹配你的显卡驱动！**
先看驱动支持的 CUDA 版本：`nvidia-smi`（右上角 CUDA Version）。
- 驱动支持 12.6：`pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu126`
- 驱动支持 12.1：把上面的 `cu126` 换成 `cu121`
> 装错 CUDA 版本会导致 `cuda.is_available()=False`。装完验证：
> `python -c "import torch; print(torch.cuda.is_available())"` 要输出 `True`。

**3. 装其余依赖**
```bash
pip install -r voice_group/requirements.txt
conda install -c conda-forge ffmpeg -y      # 音频解码需要
```

## 二、目录结构
```
voice_group/
├── pipeline.py              # 主入口（audio_to_command）
├── asr_vad.py               # A：识别+VAD+微调
├── asr_cascade.py           # 关键控制指令的条件复核与置信度校准
├── asr_lora.py              # A：识别（无VAD版，备用）
├── lora_dialect/            # ★ 当前生产 LoRA 权重，必须保留
├── lora_finetuned/          # 备用 LoRA，当前入口不加载
├── vehicle_nlu/src/         # B1：意图识别
├── nlu_b2/                  # B2：槽位提取
└── README.md                # 本文件
```

## 三、调用方式

**Python 调用（推荐，接进你们的 CARLA 代码）**
```python
from pipeline import audio_to_command

cmd = audio_to_command("指令音频.wav")     # 16kHz 单声道 wav 最佳
print(cmd["intent"], cmd["parameters"])   # 例：SLOW_DOWN {'mode':'RELATIVE',...}
```

**命令行测试**
```bash
python pipeline.py 指令音频.wav
```

首次运行会下载 SenseVoice、VAD 和 faster-whisper small。后续启动优先读取本地缓存；可用 `SENSEVOICE_MODEL_PATH`、`FSMN_VAD_MODEL_PATH` 显式指定离线 snapshot。级联评分策略与实测结果见 `docs/evaluation/CASCADE_ASR.md`。

## 四、输出：DrivingCommand
```json
{
  "command_id": "cmd_xxx",
  "source_text": "进入隧道了，减速哈。",
  "intent": "SLOW_DOWN",
  "parameters": {"mode": "RELATIVE", "action": "DECELERATE"},
  "intent_confidence": 0.95,
  "status": "valid",
  "confirm_required": false,
  "errors": [], "warnings": []
}
```
- `status != "valid"` 或 `confirm_required=true` → 请勿直接执行，做减速/停车/请求确认。
- 支持的意图：SET_SPEED / CHANGE_LANE / PULL_OVER / STOP / EMERGENCY_STOP / AVOID_OBSTACLE / KEEP_LANE / SLOW_DOWN / SPEED_UP / TURN / KEEP_LANE，及 UNKNOWN。

## 五、验收与证据

标准文本回归（完整读取 250 条清单，不启动 ASR）：

```bash
python -m pytest -q voice_group/tests
```

服务器真实音频：

```bash
python tools/evaluate_voice_audio.py \
  --condition clean \
  --output artifacts/voice_clean.json
```

经声级计校准的 50 dBA 噪声录音应保持与 manifest 相同的相对路径，再运行：

```bash
python tools/evaluate_voice_audio.py \
  --condition noise_50dba \
  --audio-root /data/voice_50dba \
  --noise-level-dba 50 \
  --calibration-log /data/voice_50dba/calibration.txt \
  --output artifacts/voice_noise_50dba.json
```

工具输出逐语言 ASR/意图/槽位准确率，以及 ASR、NLU、端到端的 mean/P95/P99/max 延迟。数字音频幅值不能证明绝对 50 dBA，因此没有校准记录时工具拒绝生成“50 dBA”证据。

历史机器结果不随源码保存。正式提交必须在目标机器重跑，并把原始报告写入
`artifacts/reports/voice/` 后再建立哈希索引。

注意：当前 SenseVoice/FunASR 返回 `asr_confidence=null`，置信度覆盖率为 0%。低置信度拦截逻辑已有自动测试，但生产后端必须实际提供经过校准的 score 才能生效。

## 六、常见问题
- `cuda.is_available()=False` → PyTorch 的 CUDA 版本和驱动不匹配，重装对应 cuXXX 版本。
- `No module named 'src'` / `'nlu_b2'` → 请从 voice_group 目录运行，别把文件挪散。
- 读不了 mp3 → `conda install -c conda-forge ffmpeg`。
- 首次运行卡在下载 → 需联网下模型，或配置 ModelScope 缓存。

## 七、字段与模型完整性

- 完整接口：`voice_group/docs/INTERFACE.md`
- 服务器音频验收：`voice_group/docs/evaluation/SERVER_AUDIO.md`
- Windows 本机环境：`voice_group/docs/evaluation/LOCAL_WINDOWS.md`
- 模型清单与 SHA-256：`voice_group/MODEL_MANIFEST.json`
- 校验命令：`python tools/verify_voice_weights.py`
- 许可证与归属：`voice_group/LICENSES.md`
