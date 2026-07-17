"""
ASR 模块（LoRA 微调版，A 的最终交付）—— 加载基座 + LoRA 适配器

和 asr.py 完全相同的 transcribe() 接口，D 可直接替换使用。
用微调后的模型（普通话已达 99%+），延时几乎不变。

前置：lora_finetuned/ 已训练好；pip 有 peft
用法：
    from asr_lora import ASR
    asr = ASR()
    out = asr.transcribe("test.wav")   # {text, asr_confidence, 时间戳, latency_ms}
"""
import time, re
from pathlib import Path
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
from peft import PeftModel

LORA_DIR = Path(__file__).resolve().parent / "lora_finetuned"

_EMOJI = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2190-\u21FF\u2B00-\u2BFF]")
def _strip_tags(text):
    text = re.sub(r"<\|[^|]*\|>", "", text)
    return _EMOJI.sub("", text).strip()

CORRECTION_MAP = {"施工去":"施工区","考边停车":"靠边停车","掉投":"掉头"}
def _apply_correction(text):
    for w,r in CORRECTION_MAP.items(): text=text.replace(w,r)
    return text

class ASR:
    def __init__(self, device="cuda:0", lora_dir=LORA_DIR):
        self.am = AutoModel(model="iic/SenseVoiceSmall", device=device, disable_update=True)
        # 套上 LoRA 适配器
        lora_path = Path(lora_dir)
        if not lora_path.is_dir():
            raise FileNotFoundError(f"local LoRA directory not found: {lora_path}")
        self.am.model = PeftModel.from_pretrained(self.am.model, str(lora_path)).to(device)
        self.am.model.eval()
        # 预热
        try:
            import numpy as np
            self.am.generate(input=np.zeros(16000, dtype="float32"), language="auto", use_itn=True)
        except Exception:
            pass

    def transcribe(self, audio, correct=True, t_audio_start_ns=None):
        if t_audio_start_ns is None:
            t_audio_start_ns = time.monotonic_ns()
        t0 = time.monotonic_ns()
        res = self.am.generate(input=audio, language="auto", use_itn=True)
        t_asr_end_ns = time.monotonic_ns()
        text = _strip_tags(rich_transcription_postprocess(res[0]["text"]))
        if correct: text = _apply_correction(text)
        return {
            "text": text,
            "asr_confidence": res[0].get("score", None),
            "t_audio_start_ns": t_audio_start_ns,
            "t_asr_end_ns": t_asr_end_ns,
            "latency_ms": round((t_asr_end_ns - t0)/1e6, 1),
        }

if __name__ == "__main__":
    import sys
    asr = ASR()
    path = sys.argv[1] if len(sys.argv) > 1 else "test.wav"
    # 测 5 次取平均延时（更能代表真实短指令延时）
    outs = [asr.transcribe(path) for _ in range(5)]
    print(f"识别结果: {outs[-1]['text']}")
    lats = [o['latency_ms'] for o in outs]
    print(f"5次延时(ms): {lats}")
    print(f"平均延时: {sum(lats)/len(lats):.1f} ms  (目标≤50ms)")
