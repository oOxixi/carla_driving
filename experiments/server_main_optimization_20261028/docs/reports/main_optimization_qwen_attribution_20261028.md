# Qwen decision attribution and structured shadow planning (2026-10-28)

## Scope and deployment boundary

This is work on `main_optimization`, based on `2df88503e54f4f5a0e3031c95228fa0c80270645`.
Experiments captured the source as a working-tree patch; versioning this work
does not create a new frozen driving baseline.
Neither `main` nor `challenge` is changed. Server `outputs/` is preserved.
No new 8 km run or official gate is claimed.

The running production adapter on port 18005 was NOT restarted or switched.
The existing C/D safety logic, route generation, controller and scenario contracts
are unchanged. New structured output is offline only: the shadow planner has no
`infer()` service interface and no actuator/runner integration.

Teacher checked for the live offline calls:

- Model: `Qwen/Qwen3.5-2B` (not 7B).
- Revision: `15852e8c16360a2fea060d615a32b45270f8a8fc`.
- Artifact SHA256: `4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`.
- Manifest retains adapter health, vLLM URL, source/dirty-tree provenance, and input SHA256.
- Adapter health attests the deployment configuration, not a cryptographic proof
  that arbitrary endpoints contain those weights. The CLI also requires a common
  host and checks vLLM's exposed model ID.

## Implemented

1. `qwen_service/planner_audit.py`: opt-in append-only adapter audit. Captures
   original request, offered candidates, raw response, model/effective behavior,
   rule override reason, deterministic expansion ownership, adapter plan, actual
   encoded-image hash and elapsed time. No API credentials or image bytes.
   `ADAPTER_RETURNED` does not mean validated, executed, or successful driving.
   Runtime write failures are counted and exposed without changing vehicle action.
2. Production adapter option `--planner-audit-jsonl <private-artifact-path>`.
   Disabled by default; does not add fields to the strict ManeuverPlan response.
3. `qwen_service/shadow_planner.py`: the model generates 1-4 semantic steps,
   targets, completion, failure and replanning fields. Only transport metadata
   is assembled by code; no keyword-based semantic step repair.
4. `tools/qwen_planner_experiment.py`: capture actual ModelRequest records,
   replay the current choice adapter, run structured original/no-RGB pairs,
   or summarize choice audits. No CARLA execution.
5. Tests cover unchanged legacy plans, single-choice attribution, overrides,
   audit failures, encoded-image hashing, immutable captured input, missing RGB,
   schema/target/speed/stop/behavior boundaries and incomplete model generation.

## Safety and attribution boundaries

- Remove NLU `command_hint` and routing answers only from the shadow prompt.
  Strip scenario-owned completion groups/IDs, which are not visual detections.
  Do not silently widen upstream `allowed_behaviors`: it currently mixes semantic
  narrowing with capability policy. This remains a limitation to address explicitly.
- Keep request constraints, real observed targets, map capabilities and raw source
  instruction. Original and no-RGB shadow pairs use identical text inputs.
- No RGB file means an error in the original-vision arm, not a hidden text-only run.
- Validate full schema and existing PlanValidator after generation. Duplicate keys,
  duplicate unique-array items, unknown targets, forbidden low-level fields,
  overspeed and incompatible completion are not silently fixed.
- Captured monotonic timestamps are checked at capture time only. This offline
  validation never authorizes use of an old plan in the current simulation.
- Contract validity is not semantic accuracy. HOLD or an incomplete task can pass
  the contract; neither is automatically counted as task success.
- The image transport remains 224x224. This work does not activate the optional
  RGB ONNX detector or prove visual grounding/detection accuracy.

## Real offline smoke and observations

Final source checks: local `1334 passed, 4 skipped`; server `1335 passed, 3 skipped`.
The platform-dependent skip difference is retained, not turned into extra model
evidence. The 155 scenario contracts and official S1/S2/S3 static validators also
pass. These are software/static checks, not new driving or formal model gates.

Source request: the 2026-10-26 case 001 pedestrian/overtake event, request
`qwen-1dc25c814ffe49c1840358d2a181ed4a`. It was extracted unchanged from the runner's
canonical submission record, not rebuilt from a script or expected answer.

Server artifact root: `/home/tiaozhansai/carla-driving-main-optimization/artifacts/validation/`.

| Artifact directory | Observed result | Interpretation |
| --- | --- | --- |
| `qwen_attribution_20261028_capture` | One real request frozen, source SHA/line retained | Input provenance, not a new model result |
| `qwen_attribution_20261028_choice` | Original and no-RGB each offered only `["K"]`; both raw outputs `K`; expanded plans identical | This request's action is predetermined by constraints; no evidence of visual decision benefit |
| `qwen_attribution_20261028_shadow` | Two HTTP 400 errors: grammar backend lacks `uniqueItems` | Deployment compatibility failure; preserved, not counted as model accuracy |
| `qwen_attribution_20261028_shadow_grammar_v2` | Both calls generated JSON but were rejected | Structured mode is NOT ready to replace production |

Compatibility fix: omit `uniqueItems` only from the generation grammar projection.
The full local acceptance schema still enforces it. A dedicated regression test
proves duplicate replanning conditions are rejected, not deduplicated.

Structured original-image result: one `SLOW_DOWN` step with repeated
`TARGET_VISIBLE` preconditions; full schema rejected it. It also does not establish
completion of the requested four-part task.

Structured no-RGB result: four steps, but repeated replanning conditions; full
schema rejected it. Raw output additionally contained invalid target IDs such as
`CURRENT`. No vehicle received either plan. Do not deduplicate the output and
retroactively report a pass; subsequent independent errors need separate analysis.

Only one request was examined. These results do not estimate overall Qwen accuracy,
prove Qwen never uses RGB, or establish a statistically significant A/B advantage.

## Usage (server, private artifacts)

Use a new output directory for every run; existing evidence is never overwritten.
The caller must have access to the original RGB files. Use the model-service venv
for live calls (requires OpenAI client, Pillow and jsonschema).

```bash
python tools/qwen_planner_experiment.py capture \
  --input <runner.jsonl> --output-dir artifacts/validation/<new_capture> --limit 10

python tools/qwen_planner_experiment.py choice \
  --input artifacts/validation/<new_capture>/requests.jsonl \
  --output-dir artifacts/validation/<new_choice> \
  --image-root /home/tiaozhansai/carla-driving-main-optimization --limit 10

python tools/qwen_planner_experiment.py shadow \
  --input artifacts/validation/<new_capture>/requests.jsonl \
  --output-dir artifacts/validation/<new_shadow> \
  --image-root /home/tiaozhansai/carla-driving-main-optimization --limit 10

python tools/qwen_planner_experiment.py audit \
  --input artifacts/validation/<new_choice>/choice_audit.jsonl \
  --output-dir artifacts/validation/<new_audit_summary>
```

The default model endpoint is port 8000 `/v1`; pinned production health is port
18005 `/health`. Original/no-RGB are the default two arms. `--vision` can select
one arm explicitly. Do not execute arbitrary old requests through the live
orchestrator just to run this offline experiment.

Audit files contain instruction text and target identities. Keep them in private
artifacts; do not commit raw JSONL/images to GitHub.

## Remaining work, in order

1. Improve compact structured generation reliability on development requests,
   retaining raw failures and full post-validation. No silent semantic repair.
2. Separate task-intent hints from hard allowed capabilities before widening model
   choices. Preserve explicit user prohibitions, legal constraints and safety.
3. Build independently labeled, frozen multi-choice and counterfactual pairs.
   Compare a fair rule baseline; report action/target/order/condition accuracy and
   uncertainty separately from downstream safety intervention.
4. Activate and verify RGB detector plus image-to-track grounding in a controlled
   regression, with sensor provenance, not scenario names as visual evidence.
5. Only after offline/shadow acceptance, consider short-event closed loop. The
   existing bicycle `STEP_TIMEOUT` issue and remaining event regressions are not
   declared resolved by this work. Do not start the full route yet.

For subsequent request-slot constraints and the remaining one-step semantic
failure, see [the follow-up report](main_optimization_qwen_slot_constraints_20261028.md).
