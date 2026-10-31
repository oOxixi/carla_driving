from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from experiments.semantic_sft.data import (
    HERE, PLAN, ROOT, audit_rows, baseline_guard, canonical_hash, chat_record,
    load_jsonl, output_directory, protected_hashes, review_packet, text_hash,
    validate_plan_safety,
    source_hash,
)
from experiments.semantic_sft.environment import assistant_token_mask, inventory
from experiments.semantic_sft.prepare import external_registry


def approved(identifier="UNIT_A", split="train", family="lane_choice"):
    # Synthetic UNIT TEST approval metadata, never real training material.
    source = f"到标记{identifier}处停车"
    row = review_packet({"sample_id": identifier, "source_text": source,
                         "semantic_family": family, "group_id": identifier})
    row.update(split=split, annotation_status="APPROVED", label={
        "steps": [{"action": "STOP", "evidence": "停车", "target_text": None,
                   "direction": None, "speed_kph": None, "gap_m": None, "condition": None}],
        "prohibited_actions": {}, "requires_confirmation": False})
    row["reviews"] = [{"reviewer_id": name, "approved": True,
                       "source_sha256": row["source_sha256"],
                       "label_sha256": canonical_hash(row["label"]), "reviewed_at": "2026-10-28T10:00:00+08:00"}
                      for name in ("UNIT_ONLY_REVIEWER_A", "UNIT_ONLY_REVIEWER_B")]
    return row


def errors(report):
    return [error for issue in report["issues"] for error in issue["errors"]]


def test_all_seeds_remain_unapproved_and_do_not_overlap_old_evaluation():
    seeds = load_jsonl(HERE / "seeds.jsonl")
    assert len(seeds) == 24
    packets = [review_packet(s) for s in seeds]
    assert len({p["sample_id"] for p in packets}) == 24
    assert all(p["label"] is None and p["reviews"] == [] and p["split"] == "UNASSIGNED" for p in packets)
    assert not {text_hash(p["source_text"]) for p in packets}.intersection(protected_hashes())
    report = audit_rows(packets)
    assert report["issue_counts"]["HUMAN_REVIEW_NOT_APPROVED"] == 24
    assert report["ready_for_training"] is False
    assert report["data_ready_for_tokenization"] is False


def test_baseline_is_not_changed_outside_the_experiment_directory():
    assert baseline_guard()["passed"]


def test_source_and_label_changes_invalidate_reviews():
    row = approved()
    row["label"]["requires_confirmation"] = True
    assert "TWO_INDEPENDENT_LABEL_REVIEWS_REQUIRED" in errors(audit_rows([row]))
    row = approved()
    row["source_text"] += "现在"
    assert "SOURCE_HASH_MISMATCH" in errors(audit_rows([row]))
    row["source_sha256"] = source_hash(row["source_text"])
    assert "TWO_INDEPENDENT_LABEL_REVIEWS_REQUIRED" in errors(audit_rows([row]))


def test_duplicate_reviewer_identity_does_not_count_twice():
    row = approved()
    row["reviews"][1]["reviewer_id"] = " unit_only_reviewer_a "
    assert "TWO_INDEPENDENT_LABEL_REVIEWS_REQUIRED" in errors(audit_rows([row]))


def test_normalized_duplicates_and_paraphrase_group_cross_split_are_blocked():
    first = approved()
    second = copy.deepcopy(first)
    second.update(sample_id="UNIT_B", split="val", source_text="到 标记UNIT_A 处停车")
    second["source_sha256"] = source_hash(second["source_text"])
    report = audit_rows([first, second])
    assert "DUPLICATE_NORMALIZED_TEXT" in errors(report)
    assert "PARAPHRASE_GROUP_SPLIT_LEAKAGE" in report["global_errors"]


def test_protected_old_evaluation_and_external_hashes_are_excluded():
    row = approved()
    row["source_text"] = "将车速设为20公里每小时"
    row["source_sha256"] = source_hash(row["source_text"])
    assert "PROTECTED_EVALUATION_OR_PROMPT_TEXT" in errors(audit_rows([row]))
    row = approved()
    assert "PROTECTED_EVALUATION_OR_PROMPT_TEXT" in errors(audit_rows([row], external_protected={text_hash(row["source_text"])}))


@pytest.mark.parametrize("key", ["from_frozen_test", "used_for_prompting", "used_for_tuning"])
def test_origin_leakage_flags_block_training_data(key):
    row = approved()
    row["origin"][key] = True
    assert "ORIGIN_NOT_ELIGIBLE" in errors(audit_rows([row]))


@pytest.mark.parametrize("field,value", [("reviews", None), ("sample_id", []), ("split", "test"), ("origin", {})])
def test_malformed_records_are_reported_not_silently_dropped(field, value):
    row = approved()
    row[field] = value
    assert any(e.startswith("INVALID_RECORD_SCHEMA") for e in errors(audit_rows([row])))


def test_data_ready_never_means_training_or_gate_ready():
    rows = [approved(f"UNIT_{split}_{index}", split=split, family=family)
            for split in ("train", "val")
            for index, family in enumerate(PLAN["data_smoke_thresholds"]["required_families"])]
    report = audit_rows(rows, external_protected={"0" * 64}, minimum_train=0, minimum_val=0)
    assert report["data_ready_for_tokenization"]
    assert not report["ready_for_training"]
    assert "NO_BUSINESS_DATA_TRAINER_IMPLEMENTED" in report["training_blockers"]


def test_external_registry_is_required_and_cannot_be_an_empty_self_assertion(tmp_path):
    assert "EXTERNAL_FROZEN_TEST_EXCLUSION_REGISTRY_MISSING" in audit_rows([approved()])["global_errors"]
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"normalization": "nfkc_casefold_remove_whitespace_v1", "publisher": "UNIT", "text_sha256": []}))
    with pytest.raises(ValueError):
        external_registry(path)


def test_output_paths_cannot_point_at_old_model_or_production_workspace(tmp_path):
    for path in (ROOT, ROOT.parent / "carla_driving_main_verify_20260907/artifacts/semantic_sft/run", tmp_path / "models/run"):
        with pytest.raises(ValueError):
            output_directory(path)
    allowed = tmp_path / "artifacts/semantic_sft/new_run"
    assert output_directory(allowed, root=tmp_path) == allowed.resolve()
    allowed.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        output_directory(allowed, root=tmp_path)


def test_sft_messages_never_include_review_or_group_answers_in_prompt():
    row = approved()
    record = chat_record(row)
    assert [m["role"] for m in record["messages"]] == ["system", "user", "assistant"]
    assert record["loss_roles"] == ["assistant"]
    assert record["image_inputs"] == []
    assert "UNIT_ONLY_REVIEWER" not in json.dumps(record["messages"])
    assert json.loads(record["messages"][-1]["content"]) == row["label"]


class ToyTokenizer:
    eos_token_id = ord("~")

    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt, enable_thinking):
        assert not tokenize and not enable_thinking
        return "S|U|A:" if add_generation_prompt else "S|U|A:" + messages[-1]["content"] + "~"

    def __call__(self, text, *, add_special_tokens):
        assert not add_special_tokens
        return {"input_ids": [ord(c) for c in text]}


def test_assistant_mask_excludes_prompt_and_trains_end_of_turn():
    messages = [{"role": "user", "content": "UNIT"}, {"role": "assistant", "content": "{}"}]
    record = assistant_token_mask(ToyTokenizer(), messages)
    assert all(v == -100 for v in record["labels"][:record["prompt_tokens"]])
    assert record["labels"][-1] == ToyTokenizer.eos_token_id
    with pytest.raises(ValueError, match="no silent truncation"):
        assistant_token_mask(ToyTokenizer(), messages, max_length=1)


def test_prefix_mismatch_is_not_a_guessed_training_mask():
    class Bad(ToyTokenizer):
        def apply_chat_template(self, messages, **kwargs):
            return "PREFIX" if kwargs["add_generation_prompt"] else "OTHER{}~"

    with pytest.raises(ValueError, match="prefix mismatch"):
        assistant_token_mask(Bad(), [{"role": "user", "content": "U"}, {"role": "assistant", "content": "{}"}])


def test_lora_index_selection_excludes_mtp_vision_and_linear_attention(tmp_path):
    (tmp_path / "config.json").write_text('{"architectures":["Qwen3_5ForConditionalGeneration"]}')
    keys = {name: "unused.safetensors" for name in (
        "model.language_model.layers.3.self_attn.q_proj.weight",
        "model.language_model.layers.3.self_attn.v_proj.weight",
        "mtp.layers.0.self_attn.q_proj.weight",
        "model.visual.blocks.0.q_proj.weight",
        "model.language_model.layers.0.linear_attn.in_proj_qkv.weight")}
    (tmp_path / "model.safetensors.index.json").write_text(json.dumps({"weight_map": keys}))
    report = inventory(tmp_path)
    assert report["candidate_index_module_count"] == 2
    assert not report["ready_for_training"] and not report["model_weights_loaded"]


@pytest.mark.parametrize("field,value", [("base_model", "Qwen/Qwen3.5-7B"),
    ("base_revision", "main"), ("training_entrypoint", "train.py"),
    ("push_to_hub", True), ("model_outputs", "MERGE_INTO_BASE"),
    ("production_gpu_policy", "SHARE_PRODUCTION_GPU")])
def test_unsafe_plan_changes_are_explicitly_blocked(field, value):
    changed = copy.deepcopy(PLAN)
    changed[field] = value
    with pytest.raises(ValueError, match=field):
        validate_plan_safety(changed)


def test_rejected_export_writes_no_training_files(tmp_path, monkeypatch):
    from experiments.semantic_sft import prepare
    seed = load_jsonl(HERE / "seeds.jsonl")[0]
    source = tmp_path / "review.jsonl"
    source.write_text(json.dumps(review_packet(seed)), encoding="utf-8")
    target = tmp_path / "unit_output"
    monkeypatch.setattr(prepare, "output_directory", lambda path: path)
    monkeypatch.setattr("sys.argv", ["prepare", "export", "--input", str(source), "--output-dir", str(target)])
    assert prepare.main() == 1
    assert not (target / "train.jsonl").exists()
    assert not (target / "val.jsonl").exists()
    report = json.loads((target / "report.json").read_text(encoding="utf-8"))
    assert not report["ready_for_training"]


def test_source_approval_hash_is_exact_but_dedup_is_normalized():
    assert text_hash("STOP A") == text_hash("stopa")
    assert source_hash("STOP A") != source_hash("stopa")
    row = approved()
    row["source_text"] = row["source_text"].replace("UNIT_A", "unit_a")
    row["source_sha256"] = source_hash(row["source_text"])
    assert "TWO_INDEPENDENT_LABEL_REVIEWS_REQUIRED" in errors(audit_rows([row]))
