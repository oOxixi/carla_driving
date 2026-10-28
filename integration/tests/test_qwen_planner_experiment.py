from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from qwen_service.planner_audit import PlannerAuditLog, summarize_choice_audit
from qwen_service.service import QwenDecisionService, VllmQwenPlannerBackend
from qwen_service.shadow_planner import (
    StructuredShadowPlanner, shadow_model_input, generation_schema, semantic_output_schema,
    request_output_schema, flag_set_schema, decode_flag_sets,
    action_completion_schema, validate_action_completions,
)
from tools.qwen_planner_experiment import extract_requests, run_shadow, run_choice

ROOT = Path(__file__).resolve().parents[2]


def request():
    payload = json.loads((ROOT / "interfaces/examples/model_request.json").read_text(encoding="utf-8"))
    payload["command_hint"] = {"intent": "SLOW_DOWN", "direction": None, "target_speed_mps": 3.0}
    payload["scene_capabilities"] = {"grounded_target_ids": ["scenario_actor"],
                                     "completion_target_groups": {"scenario_actor": ["scenario_actor"]}}
    return payload


def semantic_plan():
    full = json.loads((ROOT / "interfaces/examples/maneuver_plan.json").read_text(encoding="utf-8"))
    full["steps"] = full["steps"][:1]
    return {k: full[k] for k in ("steps", "replan_conditions", "confidence", "requires_confirmation", "reason_code")}


def transport(raw="C", *, finish="stop"):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw), finish_reason=finish)])

    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    backend._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    backend.model_id = "Qwen/Qwen3.5-2B"
    backend.image_root = None
    backend.image_max_side = 224
    backend.jpeg_quality = 75
    backend.max_new_tokens = 1
    return backend, calls


def test_audit_preserves_plan_and_exposes_single_choice(tmp_path):
    backend, calls = transport()
    payload = request()
    payload["rgb_ref"] = None
    original = backend.infer(payload)
    backend.audit_log = PlannerAuditLog(tmp_path / "audit.jsonl")
    assert backend.infer(payload) == original
    record = json.loads(backend.audit_log.path.read_text(encoding="utf-8"))
    assert record["candidate_codes"] == ["C"]
    assert record["raw_model_response"] == "C"
    assert record["adapter_plan"] == original
    assert record["model_choice_was_offered"] is True
    assert record["semantic_step_source"] == "DETERMINISTIC_ADAPTER_EXPANSION"
    assert record["stage"] == "ADAPTER_ONLY"
    assert len(calls) == 2
    assert "adapter_plan" not in original
    assert summarize_choice_audit([record])["single_candidate_fraction"] == 1.0


def test_audit_records_confirmation_override_without_claiming_execution(tmp_path):
    backend, _ = transport("A")
    backend.audit_log = PlannerAuditLog(tmp_path / "audit.jsonl")
    payload = request()
    payload["rgb_ref"] = None
    payload["routing"] = {"disposition": "CONFIRM_SAFE", "score": 1,
                          "reasons": ["UNCERTAIN"], "safe_wait_behavior": "STOP"}
    assert backend.infer(payload)["steps"][0]["behavior"] == "HOLD"
    record = json.loads(backend.audit_log.path.read_text(encoding="utf-8"))
    assert record["model_behavior"] == "KEEP_LANE"
    assert record["model_choice_was_offered"] is False
    assert record["overrides"] == ["CONFIRM_SAFE_TO_HOLD"]
    assert summarize_choice_audit([record])["post_model_override_requests"] == 1


def test_audit_keeps_model_error(tmp_path):
    backend, _ = transport("garbage")
    backend.audit_log = PlannerAuditLog(tmp_path / "audit.jsonl")
    payload = request()
    payload["rgb_ref"] = None
    with pytest.raises(ValueError):
        backend.infer(payload)
    record = json.loads(backend.audit_log.path.read_text(encoding="utf-8"))
    assert record["status"] == "ERROR"
    assert record["raw_model_response"] == "garbage"
    assert "adapter_plan" not in record


def test_audit_disk_failure_does_not_change_decision_and_is_observable(tmp_path):
    backend, _ = transport()
    backend.audit_log = PlannerAuditLog(tmp_path / "audit.jsonl")
    backend.audit_log.path = tmp_path  # directory cannot be opened for appending
    payload = request()
    payload["rgb_ref"] = None
    assert backend.infer(payload)["steps"][0]["behavior"] == "SLOW_DOWN"
    assert backend.audit_log.status()["write_errors"] == 1
    assert "AUDIT_WRITE_ERRORS=1" in backend.health()[1]


def test_audit_hashes_actual_encoded_rgb(tmp_path):
    backend, _ = transport()
    backend.audit_log = PlannerAuditLog(tmp_path / "audit.jsonl")
    image = tmp_path / "front.png"
    Image.new("RGB", (50, 50)).save(image)
    payload = request()
    payload["rgb_ref"] = str(image)
    backend.infer(payload)
    record = json.loads(backend.audit_log.path.read_text(encoding="utf-8"))
    assert record["image_sent"] is True
    assert len(record["encoded_image_sha256"]) == 64
    assert "base64" not in backend.audit_log.path.read_text(encoding="utf-8")


def test_shadow_removes_nlu_answers_but_never_widens_constraints():
    payload = request()
    original = copy.deepcopy(payload)
    sanitized = shadow_model_input(payload)
    assert "command_hint" not in sanitized
    assert "grounded_target_ids" not in sanitized["scene_capabilities"]
    assert "completion_target_groups" not in sanitized["scene_capabilities"]
    assert sanitized["constraints"] == payload["constraints"]
    assert payload == original


def test_shadow_model_owns_semantic_steps_and_is_not_a_production_backend():
    backend, calls = transport(json.dumps(semantic_plan()))
    planner = StructuredShadowPlanner(backend)
    with pytest.raises(TypeError, match="backend must provide"):
        QwenDecisionService(planner)
    payload = request()
    original = copy.deepcopy(payload)
    report = planner.generate(payload, vision="no_rgb")
    assert report["validation"] == "CONTRACT_PASS_ONLY"
    assert report["model_plan"]["steps"] == semantic_plan()["steps"]
    assert report["semantic_step_source"] == "MODEL_JSON"
    assert report["scope"] == "OFFLINE_SHADOW_NOT_EXECUTABLE_NOT_GATE"
    assert payload == original
    assert calls[0]["max_tokens"] == 2048
    assert "json" in calls[0]["extra_body"]["structured_outputs"]
    prompt = calls[0]["messages"][0]["content"][-1]["text"]
    assert "command_hint" not in prompt
    assert "scenario_actor" not in prompt
    assert "rgb_ref" not in prompt


@pytest.mark.parametrize("raw", ["not json", '{"steps":[],"steps":[]}',
                                  json.dumps({**semantic_plan(), "steer": 0.3})])
def test_shadow_rejects_bad_model_output_without_rule_repair(raw):
    backend, _ = transport(raw)
    report = StructuredShadowPlanner(backend).generate(request(), vision="no_rgb")
    assert report["validation"] == "REJECTED"
    assert report["raw_model_response"] == raw
    assert "compiled_preview" not in report


@pytest.mark.parametrize("finish", ["length", "content_filter", None])
def test_shadow_rejects_truncated_or_unverified_completion(finish):
    backend, _ = transport(json.dumps(semantic_plan()), finish=finish)
    report = StructuredShadowPlanner(backend).generate(request(), vision="no_rgb")
    assert report["validation"] == "REJECTED"


@pytest.mark.parametrize("fault", ["speed", "target", "red_light", "disallowed", "too_many_steps"])
def test_shadow_preserves_hard_boundaries(fault):
    semantic = semantic_plan()
    payload = request()
    if fault == "speed":
        semantic["steps"][0]["target"]["target_speed_mps"] = 40.0
    elif fault == "target":
        semantic["steps"][0]["target"]["target_id"] = "invented-id"
    elif fault == "red_light":
        payload["constraints"]["must_stop"] = True
        payload["scene_summary"]["traffic_light"] = "RED"
    elif fault == "disallowed":
        payload["constraints"]["allowed_behaviors"] = ["STOP"]
    else:
        semantic["steps"] *= 5
    backend, _ = transport(json.dumps(semantic))
    report = StructuredShadowPlanner(backend).generate(payload, vision="no_rgb")
    assert report["validation"] == "REJECTED"
    assert "compiled_preview" not in report


def test_shadow_rgb_ablation_uses_same_text_and_only_changes_image(tmp_path):
    image = tmp_path / "front.png"
    Image.new("RGB", (50, 50)).save(image)
    backend, calls = transport(json.dumps(semantic_plan()))
    payload = request()
    payload["rgb_ref"] = str(image)
    planner = StructuredShadowPlanner(backend)
    reports = list(run_shadow([payload], planner, visions=["original", "no_rgb"]))
    assert [r["image_sent"] for r in reports] == [True, False]
    assert reports[0]["model_input_sha256"] == reports[1]["model_input_sha256"]
    assert len(calls[0]["messages"][0]["content"]) == 2
    assert len(calls[1]["messages"][0]["content"]) == 1


def test_shadow_missing_rgb_is_error_not_text_only_success():
    backend, calls = transport(json.dumps(semantic_plan()))
    payload = request()
    payload["rgb_ref"] = None
    reports = list(run_shadow([payload], StructuredShadowPlanner(backend), visions=["original", "no_rgb"]))
    assert reports[0]["validation"] == "ERROR"
    assert reports[1]["validation"] == "CONTRACT_PASS_ONLY"
    assert len(calls) == 1


def test_audit_empty_summary_does_not_claim_success():
    assert summarize_choice_audit([])["single_candidate_fraction"] is None


def test_capture_extracts_exact_request_once_and_ignores_execution_frames(tmp_path):
    payload = request()
    source = tmp_path / "runner.jsonl"
    record = {"payload": {"orchestration": {"model_request": payload}}}
    source.write_text("\n".join(json.dumps(r) for r in
                      ({"record_type": "frame"}, record, record)), encoding="utf-8")
    extracted = extract_requests(source, limit=10)
    assert extracted == [{"request": payload, "source_line": 2}]


def test_capture_will_not_reconstruct_missing_request(tmp_path):
    source = tmp_path / "runner.jsonl"
    source.write_text(json.dumps({"payload": {"intent": "STOP"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="no complete ModelRequest"):
        extract_requests(source, limit=1)


def test_transport_schema_compatibility_does_not_weaken_local_unique_check():
    schema = semantic_output_schema()
    wire = generation_schema(schema)
    assert schema["properties"]["replan_conditions"]["uniqueItems"] is True
    assert "uniqueItems" not in json.dumps(wire)
    semantic = semantic_plan()
    semantic["replan_conditions"] = ["TARGET_LOST", "TARGET_LOST"]
    backend, _ = transport(json.dumps(semantic))
    report = StructuredShadowPlanner(backend).generate(request(), vision="no_rgb")
    assert report["validation"] == "REJECTED"
    assert "compiled_preview" not in report


def test_choice_replay_keeps_source_request_and_current_adapter_logic(tmp_path):
    image = tmp_path / "front.png"
    Image.new("RGB", (50, 50)).save(image)
    backend, calls = transport("C")
    backend.audit_log = PlannerAuditLog(tmp_path / "audit.jsonl")
    payload = request()
    payload["rgb_ref"] = str(image)
    original = copy.deepcopy(payload)
    reports = list(run_choice([payload], backend, visions=["original", "no_rgb"]))
    assert all(r["validation"] == "ADAPTER_RETURNED_NOT_VALIDATED" for r in reports)
    assert reports[0]["adapter_plan"] == reports[1]["adapter_plan"]
    assert all(c["max_tokens"] == 1 for c in calls)
    assert payload == original
    records = [json.loads(line) for line in backend.audit_log.path.read_text(encoding="utf-8").splitlines()]
    assert summarize_choice_audit(records)["single_candidate_requests"] == 2
    assert summarize_choice_audit(records)["image_sent_requests"] == 1


def wire_plan():
    semantic = semantic_plan()
    semantic["replan_conditions"] = {name: True for name in semantic["replan_conditions"]}
    for step in semantic["steps"]:
        step["preconditions"] = {name: True for name in step["preconditions"]}
    return semantic


def test_flag_format_is_lossless_not_a_step_repair():
    raw = wire_plan()
    original = copy.deepcopy(raw)
    assert decode_flag_sets(raw) == semantic_plan()
    assert raw == original
    backend, calls = transport(json.dumps(raw))
    report = StructuredShadowPlanner(backend, wire_format="flag_sets_v1").generate(request(), vision="no_rgb")
    assert report["validation"] == "CONTRACT_PASS_ONLY"
    assert report["model_plan"]["steps"] == semantic_plan()["steps"]
    assert report["task_accuracy"] == "NOT_MEASURED"
    assert report["visual_grounding"].startswith("UNVERIFIED")
    assert "uniqueItems" not in json.dumps(calls[0]["extra_body"])
    assert "OBJECT SETS" in calls[0]["messages"][0]["content"][-1]["text"]


def test_request_schema_binds_slots_without_selecting_an_answer():
    payload = request()
    payload["constraints"]["max_target_speed_mps"] = 2.0
    payload["scene_capabilities"]["available_lanes"] = ["CURRENT", "LEFT_ADJACENT"]
    before = copy.deepcopy(payload)
    schema = request_output_schema(payload)
    target = schema["$defs"]["step"]["properties"]["target"]["properties"]
    assert target["target_id"]["enum"] == [None, "vehicle-right-01"]
    assert "scenario_actor" not in target["target_id"]["enum"]
    assert target["target_speed_mps"]["maximum"] == 2.0
    assert "RIGHT_ADJACENT" not in target["target_lane"]["enum"]
    assert schema["$defs"]["step"]["properties"]["behavior"]["enum"] == [
        "KEEP_LANE", "SLOW_DOWN", "STOP", "FOLLOW", "HOLD",
    ]
    assert payload == before


@pytest.mark.parametrize("fault", ["false_flag", "unknown_flag", "unknown_target", "lane_as_target", "speed_cap", "duplicate_key", "array_instead_of_set"])
def test_flag_output_remains_strict_and_never_fixes_model_errors(fault):
    wire = wire_plan()
    payload = request()
    if fault == "false_flag":
        wire["replan_conditions"]["TARGET_LOST"] = False
    elif fault == "unknown_flag":
        wire["steps"][0]["preconditions"]["SCENARIO_EXPECTED_ANSWER"] = True
    elif fault == "unknown_target":
        wire["steps"][0]["target"]["target_id"] = "scenario_actor"
    elif fault == "lane_as_target":
        wire["steps"][0]["target"]["target_id"] = "CURRENT"
    elif fault == "speed_cap":
        payload["constraints"]["max_target_speed_mps"] = 1.0
    elif fault == "array_instead_of_set":
        wire["steps"][0]["preconditions"] = ["PERCEPTION_FRESH"]
    raw = json.dumps(wire)
    if fault == "duplicate_key":
        raw = raw.replace('"LANE_BLOCKED": true', '"LANE_BLOCKED": true, "LANE_BLOCKED": true')
    backend, _ = transport(raw)
    report = StructuredShadowPlanner(backend, wire_format="flag_sets_v1").generate(payload, vision="no_rgb")
    assert report["validation"] == "REJECTED"
    assert report["raw_model_response"] == raw
    assert "compiled_preview" not in report


def test_flag_grammar_does_not_mutate_full_acceptance_schema():
    schema = semantic_output_schema()
    original = copy.deepcopy(schema)
    flags = flag_set_schema(schema)
    assert schema == original
    assert schema["properties"]["replan_conditions"]["uniqueItems"] is True
    assert flags["properties"]["replan_conditions"]["type"] == "object"


def test_shadow_collects_multiple_contract_errors():
    raw = wire_plan()
    raw["steps"][0]["target"]["target_id"] = "invented"
    raw["steps"][0]["target"]["target_speed_mps"] = 45.0
    backend, _ = transport(json.dumps(raw))
    report = StructuredShadowPlanner(backend, wire_format="flag_sets_v1").generate(request(), vision="no_rgb")
    assert report["validation"] == "REJECTED"
    assert report["contract_error_count"] >= 2


def test_shadow_does_not_call_slow_down_stopped_a_safe_plan():
    raw = wire_plan()
    raw["steps"][0]["completion"] = {"type": "STOPPED", "value": 0.0, "hold_frames": 1}
    backend, _ = transport(json.dumps(raw))
    report = StructuredShadowPlanner(backend, wire_format="flag_sets_v1").generate(request(), vision="no_rgb")
    assert report["validation"] == "REJECTED"
    assert report["validation_layers"]["compiler"] is False
    with pytest.raises(ValueError, match="SLOW_DOWN cannot complete"):
        validate_action_completions(decode_flag_sets(raw))


def test_action_completion_grammar_leaves_step_order_to_model():
    schema = request_output_schema(request())
    original = copy.deepcopy(schema)
    constrained = action_completion_schema(flag_set_schema(schema))
    assert schema == original
    branches = constrained["$defs"]["step"]["anyOf"]
    slow = next(b for b in branches if b["properties"]["behavior"] == {"const": "SLOW_DOWN"})
    assert "STOPPED" not in slow["properties"]["completion"]["properties"]["type"]["enum"]
    assert constrained["properties"]["steps"]["maxItems"] == 4
    assert constrained["properties"]["steps"]["minItems"] == 1
