import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
yaml = pytest.importorskip("yaml")

from challenge.distillation.a1_student import build_a1_input_packer  # noqa: E402
from challenge.distillation.dataset import DistillationDataset, load_jsonl, make_collate_fn  # noqa: E402
from challenge.distillation.preflight import preflight_datasets  # noqa: E402
from challenge.distillation.train import _audit_quarantined_hard_cases  # noqa: E402


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "challenge" / "distillation" / "b1_smoke_config.yaml"


def _config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_teacher_identity_is_unified_across_manifest_config_and_b1() -> None:
    cfg = _config()
    manifest = json.loads(
        (ROOT / "challenge" / "teacher_baseline_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["model_id"] == "Qwen/Qwen3.5-2B"
    assert cfg["teacher"]["model_id"] == manifest["model_id"]
    assert cfg["teacher"]["git_sha"] == manifest["git_sha"]
    assert cfg["teacher"]["model_revision"] == manifest["model_revision"]
    for split in ("train_path", "val_path", "hard_cases_path"):
        for record in load_jsonl(ROOT / cfg["dataset"][split]):
            assert record["metadata"]["teacher_model_id"] == manifest["model_id"]


def test_b1_smoke_preflight_and_rgb_use_a1_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    cfg = _config()
    dataset = cfg["dataset"]
    report = preflight_datasets(
        dataset["train_path"], dataset["val_path"],
        expected_version=dataset["version"],
        expected_teacher_git_sha=cfg["teacher"]["git_sha"],
        expected_teacher_model_id=cfg["teacher"]["model_id"],
        asset_root=dataset["asset_root"], require_rgb=True,
    )
    assert report["valid"] is True
    assert report["train"]["valid_records"] == 22
    assert report["validation"]["valid_records"] == 6

    records = load_jsonl(dataset["train_path"])
    sample = DistillationDataset(
        records, asset_root=dataset["asset_root"], require_rgb=True,
    )[0]
    assert Path(sample["request"]["rgb_ref"]).is_file()
    recorded = [step["target_pointer"] for step in records[0]["student_targets"]["steps"]]
    active = [value for value, mask in zip(
        sample["labels"]["target_pointer"], sample["labels"]["step_mask"], strict=True,
    ) if mask]
    assert active == recorded
    packed = make_collate_fn(input_packer=build_a1_input_packer())([sample])
    assert torch.count_nonzero(packed["model_inputs"]["rgb"]) > 0


def test_b1_hard_cases_are_audited_but_never_train_or_val(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    audit = _audit_quarantined_hard_cases(_config(), smoke=False)
    assert audit["count"] == 2
    assert len(audit["sample_ids"]) == 2
    assert audit["reasons"]["CLOSED_LOOP_COMMAND_FAILED"] == 2
