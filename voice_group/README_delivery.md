# 语音组交付包 · 使用说明（车辆控制组本地部署）

语音链路：音频 → 识别(A) → 意图(B1) → 槽位(B2) → **DrivingCommand**。
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
pip install funasr modelscope peft soundfile openpyxl
conda install -c conda-forge ffmpeg -y      # 音频解码需要
```

## 二、目录结构
```
voice_group/
├── pipeline.py              # 主入口（audio_to_command）
├── asr_vad.py               # A：识别+VAD+微调
├── asr_lora.py              # A：识别（无VAD版，备用）
├── lora_finetuned/          # ★ 微调权重，必须保留
├── vehicle_nlu/src/         # B1：意图识别
├── nlu_b2/                  # B2：槽位提取
└── README_delivery.md       # 本文件
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

首次运行会自动下载 SenseVoice + VAD 模型（约几百 MB，需联网一次；国内走 ModelScope 较快）。

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

## 五、性能实测（语音组环境）
- 普通话识别：干净 99.5% / 带噪 99.2%
- 解析延时（B1+B2）：约 8ms
- 端到端：约 135ms

## 六、常见问题
- `cuda.is_available()=False` → PyTorch 的 CUDA 版本和驱动不匹配，重装对应 cuXXX 版本。
- `No module named 'src'` / `'nlu_b2'` → 请从 voice_group 目录运行，别把文件挪散。
- 读不了 mp3 → `conda install -c conda-forge ffmpeg`。
- 首次运行卡在下载 → 需联网下模型，或配置 ModelScope 缓存。

## 七、字段对接（★ 请与语音组确认）
若你们期望的字段名/槽位键与上面不同，告诉语音组，我们改 `pipeline.py` 的组装部分即可。
