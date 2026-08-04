from pathlib import Path


def verify_kernel_log(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if "quantization=auto_gptq" not in text:
        raise ValueError("Qwen launch did not prove auto_gptq quantization")
    if "Using MarlinLinearKernel" not in text:
        raise ValueError("Qwen launch did not select MarlinLinearKernel")
    mode = "gemv" if "gemv" in text.lower() else "marlin_batch1"
    return {
        "quantization": "auto_gptq",
        "linear_kernel": "MarlinLinearKernel",
        "batch1_path": mode,
    }
