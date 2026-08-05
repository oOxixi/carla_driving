from pathlib import Path
import subprocess
import tarfile

import pytest

from tools.verify_qwen_kernel import verify_kernel_log


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ARCHIVE = (
    ROOT
    / "release_assets/source/vllm-568afb3a13806beb53bb2e6bd518269357b237c0.tar.gz"
)
PATCH = ROOT / "docker/patches/vllm-cu132-torch.patch"


def test_vllm_builder_targets_a800_and_rtx5070() -> None:
    text = (ROOT / "docker/Dockerfile.vllm-builder-cu132").read_text(encoding="utf-8")
    assert "nvidia/cuda:13.2.0-devel-ubuntu24.04" in text
    assert 'TORCH_CUDA_ARCH_LIST="8.0;12.0+PTX"' in text
    assert "568afb3a13806beb53bb2e6bd518269357b237c0" in text


def test_torch_patch_applies_to_clean_locked_source(tmp_path: Path) -> None:
    if not SOURCE_ARCHIVE.is_file():
        pytest.skip("clean locked vLLM source archive is a release asset")

    source_paths = (
        "pyproject.toml",
        "requirements/build/cuda.txt",
        "requirements/cuda.txt",
    )
    with tarfile.open(SOURCE_ARCHIVE, "r:gz") as archive:
        for source_path in source_paths:
            source = archive.extractfile(source_path)
            assert source is not None
            destination = tmp_path / source_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read())

    check = subprocess.run(
        ["git", "apply", "--check", str(PATCH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert check.returncode == 0, check.stderr
    subprocess.run(["git", "apply", str(PATCH)], cwd=tmp_path, check=True)

    cuda_requirements = (tmp_path / "requirements/cuda.txt").read_text(
        encoding="utf-8"
    )
    assert "torch==2.11.0" not in cuda_requirements
    assert "torchaudio==2.11.0" not in cuda_requirements
    assert "torchvision==0.26.0" not in cuda_requirements
    assert "torchcodec >= 0.14" not in cuda_requirements
    assert "PyNvVideoCodec==2.0.4" in cuda_requirements


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
