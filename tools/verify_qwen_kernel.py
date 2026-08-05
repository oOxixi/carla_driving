from pathlib import Path


def verify_kernel_log(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    profile_lines = [
        index
        for index, line in enumerate(lines)
        if "qwen3vl-2b-int4" in line.lower()
        or "h2oai/qwen3-vl-2b-instruct-gptq-int4" in line.lower()
    ]
    quantization_lines = [
        index for index, line in enumerate(lines) if "quantization=auto_gptq" in line
    ]
    marlin_lines = [
        index for index, line in enumerate(lines) if "Using MarlinLinearKernel" in line
    ]
    if not profile_lines:
        raise ValueError("Qwen default 2B GPTQ profile or model identity is required")
    if not quantization_lines:
        raise ValueError("Qwen launch did not prove auto_gptq quantization")
    if not marlin_lines:
        raise ValueError("Qwen launch did not select MarlinLinearKernel")
    evidence_lines = profile_lines + quantization_lines + marlin_lines
    if max(evidence_lines) - min(evidence_lines) > 20:
        raise ValueError("Qwen profile, quantization, and Marlin evidence are not one launch")
    mode = "gemv" if any("gemv" in line.lower() for line in lines) else "marlin_batch1"
    return {
        "quantization": "auto_gptq",
        "linear_kernel": "MarlinLinearKernel",
        "batch1_path": mode,
    }
