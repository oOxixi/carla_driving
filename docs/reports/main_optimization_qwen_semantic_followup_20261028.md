# Multi-step understanding follow-up: constraints, negative experiments and hard cases

## Outcome and scope

Based on `7e852e234`, still `main_optimization` only. No model weight change,
production service restart, controller change, RGB recognition improvement or new
closed-loop result is claimed. Both proposed inference alternatives were worse
than the existing development baseline, so neither becomes the default.

The default remains joint English-code extraction, with the unchanged independent
development labels. Latest result remains **9/12**, not an accuracy improvement.
The previous four-probe result remains **1/4**; it was not tuned and rerun here.
Do not interpret successful software tests as successful semantic understanding.

## Implemented engineering improvements

1. Explicit numeric contradictions in a model-selected evidence quote are rejected:
   e.g. a quote requesting 30 km/h cannot supply a 50 km/h slot. A LEFT action with
   an explicit RIGHT direction slot is rejected. No value, direction or action is
   repaired or filled by code.
2. These are narrow consistency checks, not a semantic oracle. Multiple values,
   Chinese-number expressions or missing quoted units still need independent
   labels. Metres/second are not interpreted as a distance in metres.
3. `summary.json` now groups failed development checks by head. Counts include
   failures caused by missing extraction; they are not independent error causes.
4. `hard_cases.jsonl` preserves failed inputs, labels (when independently supplied),
   raw model outputs and checks. Scope is `AUDIT_NOT_APPROVED_TRAINING_DATA`:
   generated cases are not automatically eligible for training, B1 release or
   Frozen Test. Labels never enter inference prompts.

## Alternatives retained for reproducible comparison, not promoted

### Clause-focused extraction

`qwen_service/clause_understanding.py` splits punctuation only, permits zero
commands in a background clause, and asks Qwen to choose actions/parameters for
each clause. A final model call chooses a permutation of the extracted tasks.
No keywords select actions; code does not force source order, deduplicate an
invalid permutation, append missing tasks or accept a partial result on failure.

The model still sometimes extracts the whole sentence instead of the focused
clause, confuses continuation with lane return, or attaches a condition to its
own action. Dedicated tests reject cross-clause repetition and duplicate ordering.

### Native Chinese action names

`--understanding-action-language zh` offers the same 14 choices as Chinese names,
then uses a bijective codec to return existing action codes. This is protocol
translation only: no text keywords, action expansion or task selection in code.
Original native output is retained. Mixed/unoffered codes are rejected.
The option applies to the joint strategy only and is not the default.

## Actual evidence

All controlled CLI experiments used pinned `Qwen/Qwen3.5-2B`, revision
`15852e8c16360a2fea060d615a32b45270f8a8fc`, artifact SHA256
`4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`.
Manifests retain health, endpoint, configuration, input SHA and dirty-source
provenance. No raw instructions, images or result JSONL are pushed to GitHub.

Server artifact root:
`/home/tiaozhansai/carla-driving-main-optimization/artifacts/validation/`.

| Directory | Result | Decision |
| --- | --- | --- |
| `qwen_clause_20261028_dev_v1` | 7/12 fully passed, 9/12 schema/support-valid | Do not promote |
| `qwen_clause_20261028_real_v1` | Rejected; background extraction included unrelated tasks/self-condition | Do not execute |
| `qwen_native_20261028_dev_v1` | 7/12 fully passed, 10/12 schema/support-valid | Do not promote |
| `qwen_semantic_guard_20261028_dev_v1` | 9/12 fully passed, 11/12 schema/support-valid | Retain baseline; export 3 hard cases |

Free-text diagnostics on the long pedestrian/overtake instruction and DEV_TEXT_04/
08 also showed added tasks, wrong ordering or lost conditions. Removing the JSON
grammar alone did not establish correct understanding. These diagnostic stdout
observations are not part of the controlled development accuracy table.

A bounded request-only thinking diagnostic on DEV_TEXT_04/08 used 2048 output
tokens. Both ended with `finish_reason=length` before a final answer. This does
not prove thinking cannot help with a different deployment/budget, but supplies
no valid result for the current configuration. No reasoning trace is published
and the production reasoning configuration is not changed.

The pinned [official model card](https://huggingface.co/Qwen/Qwen3.5-2B/blob/15852e8c16360a2fea060d615a32b45270f8a8fc/README.md)
describes this scale as intended for prototyping and task-specific fine-tuning.
Our small task-specific failures do not establish a universal limit of the model.

## Use

Software regression: local `1385 passed, 4 skipped`; server `1386 passed,
3 skipped`. These are engineering tests, not semantic accuracy or driving gates.

Each output directory must be new. Default behavior is unchanged:

```bash
python tools/qwen_planner_experiment.py understand \
  --understanding-strategy joint --understanding-action-language en \
  --input config/qwen_task_understanding_dev.jsonl \
  --output-dir artifacts/validation/<new-run> --limit 12 --timeout-s 120
```

For ablation, use `--understanding-strategy clause_focused`, or joint with
`--understanding-action-language zh`. Neither runs CARLA or sends vehicle commands.

## Remaining work

- Ordinary lane change vs avoidance, bicycle-following resumption, and conditional
  scope remain unresolved. The real long instruction is not declared passed.
- More prompt variants are not demonstrated to solve the issue. Next work should
  prioritize independently reviewed multi-step supervision and a separate train/
  validation contract, then evaluate task-specific 2B adaptation in isolation.
- No fine-tuning was started. Existing B1/Student distillation data must not be
  assumed valid supervision for this Qwen intent interface without an audit.
- Before any execution, reconcile extracted intent with independently sourced
  capability/legal constraints, ground visual targets, and pass short-event gates.
