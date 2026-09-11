# A3 Handoff Contract

## From A1: Student

Set `model.factory` to `module:callable`. The callable receives the configured
options plus `max_steps=4` and `max_targets`, and must return a
`torch.nn.Module`. Its forward input is the dictionary produced by A1's future
input packer. Its output must contain these floating tensors for batch size B:

| Head | Shape |
| --- | --- |
| `plan_length_logits` | `[B, 4]` |
| `behavior_logits` | `[B, 4, 14]` |
| `target_pointer_logits` | `[B, 4, max_targets + 1]` |
| `target_lane_logits` | `[B, 4, 6]` |
| `target_speed_mps` | `[B, 4]` |
| `completion_type_logits` | `[B, 4, 8]` |
| `on_failure_logits` | `[B, 4, 4]` |
| `confidence` | `[B, 1]` |
| `requires_confirmation_logits` | `[B, 1]` |
| `replan_condition_logits` | `[B, 7]` |

Pointers 0 through 7 are zero-based positions in the current
`ModelRequest.targets`; pointer 8 means `NONE`. The Student must not learn
Actor ID text. Target-lane indices are A1's fixed
`CURRENT, LEFT_ADJACENT, RIGHT_ADJACENT, ROUTE_BRANCH, SHOULDER, NONE` order.

## From B1: Train and Validation

Provide separate UTF-8 JSONL manifests. Every row must have a unique
`sample_id`, `metadata.dataset_version`, `metadata.split`, a contract-valid
`input` (`ModelRequest V1`), and `teacher.maneuver_plan` (`ManeuverPlan V2`).
Supported `metadata.sample_class` values are `normal`, `complex`, and
`safety_critical`.

A3 will reject split overlap, protected Test provenance, invalid target
references, plans longer than four steps, unsupported categories, non-finite
JSON values, and more targets than the configured fixed Student shape.

## From B2: Evaluation

B2 owns frozen Test and final PASS/FAIL. A3 consumes only aggregate results and
error classifications supplied by B2; A3 training, weighting, checkpoint
selection, and hard-case mining never read frozen Test samples.
