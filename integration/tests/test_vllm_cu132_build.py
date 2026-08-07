import json
from pathlib import Path
import subprocess
import tarfile

import pytest

from tools.verify_qwen_kernel import verify_kernel_log
from tools.verify_vllm_cu132_inputs import verify_source, verify_wheelhouse


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ARCHIVE = (
    ROOT
    / "release_assets/source/vllm-568afb3a13806beb53bb2e6bd518269357b237c0.tar.gz"
)
PATCH = ROOT / "docker/patches/vllm-cu132-torch.patch"
SOURCE_LOCK = ROOT / "third_party/vllm.lock.json"
WHEELHOUSE = ROOT / "release_assets/wheelhouse-build"
WHEELHOUSE_LOCK = ROOT / "third_party/vllm-cu132-wheelhouse.lock.json"
RESOLVED_REQUIREMENTS = ROOT / "docker/requirements-cu132-build.lock.txt"
OUTPUT_WHEELHOUSE = ROOT / "release_assets/wheelhouse"


def test_vllm_builder_targets_a800_and_rtx5070() -> None:
    text = (ROOT / "docker/Dockerfile.vllm-builder-cu132").read_text(encoding="utf-8")
    assert "nvidia/cuda:13.2.0-devel-ubuntu24.04@sha256:f9492f2eea77fbc3d0c14fa8738f35946b42da72917bf5959d284ca39b4f209a" in text
    assert 'TORCH_CUDA_ARCH_LIST="8.0;12.0+PTX"' in text
    assert "568afb3a13806beb53bb2e6bd518269357b237c0" in text
    assert "SETUPTOOLS_SCM_PRETEND_VERSION=" in text
    assert "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_VLLM=" in text
    assert "verify_inputs.py" in text
    assert "--require-hashes" in text
    assert "AS input-verify" in text


def test_release_locks_and_offline_inputs_are_exact() -> None:
    source_lock = json.loads(SOURCE_LOCK.read_text(encoding="utf-8"))
    assert source_lock["commit"] == "568afb3a13806beb53bb2e6bd518269357b237c0"
    assert source_lock["source_archive"] == {
        "filename": "vllm-568afb3a13806beb53bb2e6bd518269357b237c0.tar.gz",
        "bytes": 38222709,
        "sha256": "8b4f8a04c4313d54e42aabb372b8338609b60df1a5888e2146e46a5fc8da7f6a",
        "generated_from_commit": "568afb3a13806beb53bb2e6bd518269357b237c0",
    }
    assert source_lock["expected_wheel_version"].endswith(".cu132")
    assert "no .git metadata" in source_lock["scm_version_strategy"]
    output_wheels = list(OUTPUT_WHEELHOUSE.glob("vllm-*.whl"))
    assert [wheel.name for wheel in output_wheels] == [
        source_lock["output_wheel"]["filename"]
    ]
    assert output_wheels[0].stat().st_size == source_lock["output_wheel"]["bytes"]

    top_level = {
        line.strip()
        for line in (ROOT / "docker/requirements-cu132-build.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    }
    assert top_level == {
        "torch==2.12.1+cu132", "setuptools==78.1.0", "setuptools-scm==10.2.1",
        "setuptools-rust==1.13.0", "wheel==0.47.0", "cmake==4.4.0",
        "ninja==1.13.0", "packaging==26.2", "jinja2==3.1.6",
        "regex==2026.7.19", "protobuf==6.33.6", "build==1.5.0",
    }
    resolved = [line for line in RESOLVED_REQUIREMENTS.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
    assert len(resolved) == 42
    assert all("==" in line and " --hash=sha256:" in line for line in resolved)

    wheelhouse_lock = json.loads(WHEELHOUSE_LOCK.read_text(encoding="utf-8"))
    assert wheelhouse_lock["file_count"] == 46
    assert wheelhouse_lock["aggregate_manifest_sha256"] == "6614a720534b18bfeb3d8c5d8436ddf25c5412ec57a2a0fbb1e6621fa4ee0e85"
    assert len(wheelhouse_lock["files"]) == 46
    assert len(wheelhouse_lock["resolved_files"]) == 42
    wheel_hashes = {entry["path"]: entry["sha256"] for entry in wheelhouse_lock["files"]}
    assert all(
        f"--hash=sha256:{wheel_hashes[name]}" in "\n".join(resolved)
        for name in wheelhouse_lock["resolved_files"]
    )
    assert set(wheelhouse_lock["excluded_candidates"]) == {
        "filelock-3.29.0-py3-none-any.whl", "fsspec-2026.4.0-py3-none-any.whl",
        "setuptools-81.0.0-py3-none-any.whl", "typing_extensions-4.15.0-py3-none-any.whl",
    }
    assert SOURCE_ARCHIVE.is_file(), "release source archive is required for Task 5 verification"
    assert WHEELHOUSE.is_dir(), "release build wheelhouse is required for Task 5 verification"
    verify_source(SOURCE_ARCHIVE, source_lock)
    verify_wheelhouse(WHEELHOUSE, wheelhouse_lock)


def test_torch_patch_applies_to_clean_locked_source(tmp_path: Path) -> None:
    assert SOURCE_ARCHIVE.is_file(), "release source archive is required for patch verification"

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
    begin = (
        "QWEN_LAUNCH_BEGIN launch_id=launch-1 profile=qwen3vl-2b-int4 "
        "model=h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4\n"
    )
    end = "QWEN_LAUNCH_END launch_id=launch-1\n"
    invalid = tmp_path / "server.log"
    invalid.write_text(
        begin + "quantization=auto_gptq\nUsing ExllamaLinearKernel\n" + end,
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="auto_gptq and Marlin"):
        verify_kernel_log(invalid)

    valid = tmp_path / "marlin.log"
    valid.write_text(
        begin
        + "quantization=auto_gptq\n"
        + "Using MarlinLinearKernel for AutoGPTQLinearMethod\n"
        + end,
        encoding="utf-8",
    )
    evidence = verify_kernel_log(valid)
    assert evidence["quantization"] == "auto_gptq"
    assert evidence["linear_kernel"] == "MarlinLinearKernel"

    wrong_model = tmp_path / "wrong-model.log"
    wrong_model.write_text(
        "QWEN_LAUNCH_BEGIN launch_id=launch-1 profile=qwen3vl-2b-int4 "
        "model=not-h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4\n"
        "quantization=auto_gptq\nUsing MarlinLinearKernel\n"
        + end,
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="BEGIN"):
        verify_kernel_log(wrong_model)

    spliced = tmp_path / "spliced.log"
    spliced.write_text(
        begin + "quantization=auto_gptq\n" + end
        + "QWEN_LAUNCH_BEGIN launch_id=launch-2 profile=qwen3vl-2b-int4 "
        "model=h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4\n"
        "Using MarlinLinearKernel\nQWEN_LAUNCH_END launch_id=launch-2\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="complete Qwen launch"):
        verify_kernel_log(spliced)

    mismatched_end = tmp_path / "mismatched-end.log"
    mismatched_end.write_text(
        begin + "quantization=auto_gptq\nUsing MarlinLinearKernel\n"
        "QWEN_LAUNCH_END launch_id=launch-2\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not match"):
        verify_kernel_log(mismatched_end)

    outside_gemv = tmp_path / "outside-gemv.log"
    outside_gemv.write_text(
        "batch1_path=gemv\n" + begin + "quantization=auto_gptq\n"
        "Using MarlinLinearKernel\n" + end,
        encoding="utf-8",
    )
    assert verify_kernel_log(outside_gemv)["batch1_path"] == "marlin_batch1"

    inside_gemv = tmp_path / "inside-gemv.log"
    inside_gemv.write_text(
        begin + "quantization=auto_gptq\nUsing MarlinLinearKernel\n"
        "batch1_path=gemv\n" + end,
        encoding="utf-8",
    )
    assert verify_kernel_log(inside_gemv)["batch1_path"] == "gemv"

    two_ready = tmp_path / "two-ready.log"
    two_ready.write_text(
        begin + "quantization=auto_gptq\nUsing MarlinLinearKernel\n" + end
        + "QWEN_LAUNCH_BEGIN launch_id=launch-2 profile=qwen3vl-2b-int4 "
        "model=h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4\n"
        "quantization=auto_gptq\nUsing MarlinLinearKernel\n"
        "QWEN_LAUNCH_END launch_id=launch-2\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="exactly one"):
        verify_kernel_log(two_ready)
