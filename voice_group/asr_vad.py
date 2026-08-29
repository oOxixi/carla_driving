"""
ASR + VAD 模块（A 的最终交付，含语音活动检测）—— 东风智能驾驶语音项目

作用：
  1) VAD 先检测有效语音段，截掉静音，只送有效音频给识别 → 压延时
  2) 还原真实车载流程：连续音频流 → VAD 切出指令 → 识别
用微调后的 SenseVoice（普通话99%+）。接口与 asr.py 一致，D 可直接替换。

前置：lora_finetuned/ 已训练好；FunASR 会自动下载 FSMN-VAD 模型
用法：
    from asr_vad import ASR
    asr = ASR()
    out = asr.transcribe("test.wav")   # 自动 VAD 截静音后识别
"""
import os
import time, re
from pathlib import Path
import numpy as np
import soundfile as sf
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

DEVICE = "cuda:0"
# Resolve against this source file, not the caller's working directory.  The
# controller runs from the repository root while this adapter lives here.
LORA_DIR = Path(__file__).resolve().parent / "lora_dialect"

_EMOJI = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2190-\u21FF\u2B00-\u2BFF]")
_TRUTHY = {"1", "true", "yes", "on"}


def _env_flag(name, default=True):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUTHY


def _strip(t):
    t = re.sub(r"<\|[^|]*\|>", "", t)
    return _EMOJI.sub("", t).strip()

CORRECTION = {"施工去":"施工区","考边停车":"靠边停车","掉投":"掉头"}
def _corr(t):
    for w,r in CORRECTION.items(): t=t.replace(w,r)
    return t


def _local_model_or_id(environment_name: str, cache_name: str, model_id: str):
    """Prefer an explicit/local ModelScope snapshot for offline startup."""
    configured = os.getenv(environment_name)
    if configured:
        path = Path(configured).expanduser()
        if not path.is_dir():
            raise FileNotFoundError(
                f"{environment_name} does not point to a model directory: {path}"
            )
        return str(path)
    cached = (
        Path.home()
        / ".cache"
        / "modelscope"
        / "models"
        / cache_name
        / "snapshots"
        / "master"
    )
    return str(cached) if cached.is_dir() else model_id


class ASR:
    def __init__(self, device=DEVICE, lora_dir=LORA_DIR):
        self.use_vad = _env_flag("VOICE_VAD_ENABLED", default=True)
        self.use_itn = _env_flag("VOICE_USE_ITN", default=True)
        self.language = os.getenv("VOICE_ASR_LANGUAGE", "auto")
        use_lora = _env_flag("VOICE_USE_LORA", default=True)
        # 识别模型（微调版）
        sensevoice_model = _local_model_or_id(
            "SENSEVOICE_MODEL_PATH",
            "iic--SenseVoiceSmall",
            "iic/SenseVoiceSmall",
        )
        self.am = AutoModel(
            model=sensevoice_model,
            device=device,
            disable_update=True,
        )
        if use_lora:
            try:
                from peft import PeftModel
                from peft.tuners.lora import model as peft_lora_model
                from peft.tuners.lora import awq as peft_lora_awq
            except ImportError as error:
                raise RuntimeError(
                    "peft is required when VOICE_USE_LORA=1; set VOICE_USE_LORA=0 "
                    "to run the base SenseVoice model in environments without peft"
                ) from error
            # This process can share a Python installation with the quantized
            # Qwen service.  PEFT otherwise probes an unrelated GPTQModel/AWQ
            # installation and imports quantizer internals even though
            # SenseVoice is a regular fp32 model.  GPTQ dispatch is both
            # unnecessary here and version-fragile, so disable only that
            # optional dispatcher before injecting the ASR adapter.
            peft_lora_model.is_gptqmodel_available = lambda: False
            peft_lora_awq.is_gptqmodel_available = lambda: False
            lora_path = Path(lora_dir)
            if not lora_path.is_dir():
                raise FileNotFoundError(f"local LoRA directory not found: {lora_path}")
            self.am.model = PeftModel.from_pretrained(self.am.model, str(lora_path)).to(device)
        self.am.model.eval()
        self.vad = None
        if self.use_vad:
            # VAD 模型（FunASR 自带的 FSMN-VAD）
            vad_model = _local_model_or_id(
                "FSMN_VAD_MODEL_PATH",
                "iic--speech_fsmn_vad_zh-cn-16k-common-pytorch",
                "fsmn-vad",
            )
            self.vad = AutoModel(
                model=vad_model,
                device=device,
                disable_update=True,
            )
        # 预热
        try:
            self.am.generate(
                input=np.zeros(16000, dtype="float32"),
                language=self.language,
                use_itn=self.use_itn,
            )
        except Exception:
            pass

    def _load(self, audio):
        # audio 可以是文件路径(str)，也可以是 numpy 数组(实时音频流)
        if isinstance(audio, str):
            wav, sr = sf.read(audio, dtype="float32")
        else:
            wav, sr = np.asarray(audio, dtype="float32"), 16000   # 数组默认已是16k
        if wav.ndim > 1: wav = wav.mean(1)
        if sr != 16000:
            n = int(len(wav) * 16000 / sr)
            wav = np.interp(np.linspace(0, len(wav), n, endpoint=False),
                            np.arange(len(wav)), wav).astype("float32")
        return wav

    def transcribe(self, audio, correct=True, t_audio_start_ns=None):
        if t_audio_start_ns is None:
            t_audio_start_ns = time.monotonic_ns()
        wav = self._load(audio)
        t0 = time.monotonic_ns()

        spans = []
        if self.use_vad and self.vad is not None:
            # 1) VAD：找出有效语音段 [[start_ms, end_ms], ...]
            seg = self.vad.generate(input=wav, fs=16000)
            spans = seg[0]["value"] if seg and "value" in seg[0] else []
            if spans:
                s_ms = spans[0][0]                    # 第一段起点
                e_ms = spans[-1][1]                   # 最后一段终点
                s, e = int(s_ms/1000*16000), int(e_ms/1000*16000)
                clip = wav[max(0,s):e] if e > s else wav
            else:
                clip = wav                            # VAD 没检出就用整段
        else:
            clip = wav

        # 2) 只识别截出来的有效段
        res = self.am.generate(
            input=clip,
            language=self.language,
            use_itn=self.use_itn,
        )
        t_asr_end_ns = time.monotonic_ns()

        text = _strip(rich_transcription_postprocess(res[0]["text"]))
        if correct: text = _corr(text)

        return {
            "text": text,
            "asr_confidence": res[0].get("score", None),
            "t_audio_start_ns": t_audio_start_ns,
            "t_asr_end_ns": t_asr_end_ns,
            "latency_ms": round((t_asr_end_ns - t0)/1e6, 1),
            "vad_span_ms": [spans[0][0], spans[-1][1]] if spans else None,
        }


if __name__ == "__main__":
    import sys
    asr = ASR()
    path = sys.argv[1] if len(sys.argv) > 1 else "test.wav"
    outs = [asr.transcribe(path) for _ in range(5)]
    print(f"识别结果: {outs[-1]['text']}")
    print(f"VAD 有效段(ms): {outs[-1]['vad_span_ms']}")
    lats = [o['latency_ms'] for o in outs]
    print(f"5次延时(ms): {lats}")
    print(f"平均延时: {sum(lats)/len(lats):.1f} ms  (目标≤50ms)")
