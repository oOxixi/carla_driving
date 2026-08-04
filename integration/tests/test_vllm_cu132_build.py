from pathlib import Path

import pytest

from tools.verify_qwen_kernel import verify_kernel_log


ROOT = Path(__file__).resolve().parents[2]


def test_vllm_builder_targets_a800_and_rtx5070() -> None:
    text = (ROOT / "docker/Dockerfile.vllm-builder-cu132").read_text(encoding="utf-8")
    assert "nvidia/cuda:13.2.0-devel-ubuntu24.04" in text
    assert 'TORCH_CUDA_ARCH_LIST="8.0;12.0+PTX"' in text
    assert "568afb3a13806beb53bb2e6bd518269357b237c0" in text


def test_kernel_log_requires_real_marlin_selection(tmp_path: Path) -> None:
    invalid = tmp_path / "server.log"
    invalid.write_text("quantization=auto_gptq\nUsing ExllamaLinearKernel\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Marlin"):
        verify_kernel_log(invalid)

    valid = tmp_path / "marlin.log"
    valid.write_text(
        "quantization=auto_gptq\nUsing MarlinLinearKernel for AutoGPTQLinearMethod\n",
        encoding="utf-8",
    )
    evidence = verify_kernel_log(valid)
    assert evidence["quantization"] == "auto_gptq"
    assert evidence["linear_kernel"] == "MarlinLinearKernel"
