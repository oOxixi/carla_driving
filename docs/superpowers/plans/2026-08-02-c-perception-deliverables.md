# C Perception Deliverables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the five C-role deliverable files named in the team handoff while reusing the already-validated CARLA perception path.

**Architecture:** Keep the new C files as thin, auditable adapters around existing `integration/carla_perception.py`, `integration/rgb_detector.py`, and `car_control_C/safety_state.py` behavior. The files expose stable data structures and CLI evidence commands without replacing the closed-loop runner that already passed D02/D03/D07.

**Tech Stack:** Python 3.12 standard library dataclasses/JSON, existing pytest suite, existing CARLA runner evidence logs.

## Global Constraints

- Do not rewrite the already-passing CARLA closed-loop runner for these deliverables.
- Keep the new modules importable without CARLA, onnxruntime, or a running simulator.
- The named deliverables must live under `car_control_C/`: `sensor_adapter.py`, `rgb_pipeline.py`, `fusion_tracker.py`, `perception_state.json`, and `fault_injection.sh`.
- Tests must verify the new deliverables are structurally usable and map to the C-role evidence requirements.

---

### Task 1: Add C Deliverable Tests

**Files:**
- Create: `car_control_C/tests/test_c_deliverables.py`

**Interfaces:**
- Consumes: planned `build_sensor_audit`, `summarize_rgb_pipeline`, `StableTargetTracker`, and `PerceptionTarget`.
- Produces: failing tests that prove the named deliverables exist and provide inspectable records.

- [ ] **Step 1: Write tests for adapter, RGB summary, tracker, schema, and shell deliverable.**
- [ ] **Step 2: Run `python -m pytest car_control_C/tests/test_c_deliverables.py -q` and confirm it fails because modules/files do not exist.**

### Task 2: Add Thin Deliverable Modules

**Files:**
- Create: `car_control_C/sensor_adapter.py`
- Create: `car_control_C/rgb_pipeline.py`
- Create: `car_control_C/fusion_tracker.py`
- Create: `car_control_C/perception_state.json`
- Create: `car_control_C/fault_injection.sh`

**Interfaces:**
- Produces: importable helper dataclasses and JSON-ready summaries for C validation and handoff review.

- [ ] **Step 1: Implement `sensor_adapter.py` with frame/time/extrinsics audit helpers.**
- [ ] **Step 2: Implement `rgb_pipeline.py` with Top-K and latency summary helpers.**
- [ ] **Step 3: Implement `fusion_tracker.py` with stable target IDs and risk metrics.**
- [ ] **Step 4: Add `perception_state.json` schema/example for B/D.**
- [ ] **Step 5: Add `fault_injection.sh` commands for deterministic C validation and sensor stability checks.**

### Task 3: Verify and Prepare Git

**Files:**
- Test: `car_control_C/tests/test_c_deliverables.py`
- Test: existing C and runner tests that touched C evidence.

- [ ] **Step 1: Run `python -m pytest car_control_C/tests/test_c_deliverables.py car_control_C/tests/test_safety_state.py integration/tests/test_carla_runner_helpers.py -q`.**
- [ ] **Step 2: Run `git status --short` and report exact files to add.**
