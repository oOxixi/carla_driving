# Qwen multi-step intent understanding: development status

## Boundary

Work follows `9ae752788` on `main_optimization`. No production service restart,
controller change, scenario contract change, official gate or new closed-loop
success is claimed. `main` and `challenge` are not changed.

Model remains pinned `Qwen/Qwen3.5-2B`, revision
`15852e8c16360a2fea060d615a32b45270f8a8fc`, artifact SHA256
`4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`.
This is prompt/interface work, not model training or a replacement checkpoint.

## Implemented responsibilities

`qwen_service/task_understanding.py` separates requested intent from executable
planning. Input to the model is the original instruction only: no front-end NLU
answer, previous allowed-action narrowing, scenario-owned actor IDs, evaluation
labels or RGB images. Output contains:

- Ordered requested actions (1-8 semantic tasks, not the executable 1-4-step plan).
- Quoted target descriptions, direction, speed in km/h and distance in metres.
- Quoted conditions, instruction evidence and prohibited actions.
- Explicit need for confirmation.

No code appends missing tasks. Quotes must exist in the instruction; a condition
equal to its own action evidence is rejected as a self-prerequisite. Short-source
copy grammar offers all bounded source substrings, not rule-picked target names.
This only prevents invented strings; a wrong source span can still be selected.
Literal support does not prove correct action, number, target or condition.

The default `joint` strategy generates all task fields together, then performs
one bounded Qwen review. Both raw attempts and prompt hashes are retained. The
review receives no evaluation labels. A bad final answer never falls back to a
previous answer, and a transport error retains earlier evidence.

An optional `sequence_first` ablation asks the model for actions first, then fixes
slots to THAT model's sequence. Code does not fix slots from expected answers.
This ablation did not improve full development scores and is not the default.

Neither class has the service `infer()/health()` interface or any actuator path.
All reports say intent-only, not grounded, not executable and not a formal gate.

## Development labels and reproducibility

- `config/qwen_task_understanding_dev.jsonl`: 12 authored text development cases,
  including ordered actions, direction/speed/gap slots, conditional resumption and
  explicit negative instructions. Used during prompt development, not Frozen Test.
- `config/qwen_task_understanding_probe.jsonl`: four additional text probes written
  after the main development iterations. No prompt changes were made after their
  final run. Too small to establish generalization or formal Unseen acceptance.
- Labels are consumed only after inference. Tests check they never enter either
  inference/review prompts. No synthetic RGB or Teacher training data is claimed.
- The evaluation checks full sequence, step count, prohibitions, numeric/direction
  slots and labeled target/condition terms. Mere JSON validity is insufficient.

## Actual results: still NOT ready for vehicle control

Server artifact root:
`/home/tiaozhansai/carla-driving-main-optimization/artifacts/validation/`.

| Artifact | Result | Interpretation |
| --- | --- | --- |
| `qwen_understanding_20261028_dev_v1` | 6/12 fully passed | Initial joint extraction; not a held-out result |
| `qwen_understanding_20261028_dev_joint_v7` | 9/12 fully passed, 11/12 literal/schema-valid | Final joint development result; repeated tuning prevents generalization claims |
| `qwen_understanding_20261028_probe_joint_v7` | 1/4 fully passed, 2/4 literal/schema-valid | New phrasing still exposes condition errors; no promotion |
| `qwen_understanding_20261028_dev_sequence_v1` | 4/12 fully passed | Sequence-first ablation was worse on full slot checks |
| `qwen_understanding_20261028_real_joint_verified_v8` | Rejected | Real captured pedestrian/overtake instruction still contains self-referential conditions |

Intermediate experiments are retained, not overwritten. Counts across revisions
are development observations, not a controlled accuracy improvement estimate:
prompts, representation, review and validation evolved during these iterations.

Remaining final development failures:

- DEV_TEXT_04: ordinary left lane change is misclassified as obstacle avoidance.
- DEV_TEXT_08: bicycle-following resumption becomes avoidance, with lost speed/
  condition information.
- DEV_TEXT_11: final stop condition repeats its own action evidence.

The long real instruction now produces multiple tasks rather than only one, but
still confuses pedestrian/vehicle targets, introduces duplicate actions or binds
conditions to themselves. More tasks does not mean correct understanding.

Its intent extraction also exposes `SET_SPEED` as absent from the old upstream
allowed-action policy. This diagnoses the known policy/intent mixing; it does
not authorize bypassing legal, speed, perception or safety constraints.

One artifact folder is named `real_joint_v7` but its manifest says
`sequence_first`: it started before a pending source sync finished. Exclude it
from joint comparisons. The explicit-strategy `real_joint_verified_v8` rerun is
the authoritative joint result. Always use recorded strategy/source hashes,
never infer configuration from a directory name.

## Deployment compatibility

The running vLLM reports a 4096-token context limit. A review carrying the entire
few-shot history plus raw output hit HTTP 400 in the retained `real_v5` run.
Review now keeps only system rules, source, candidate and review instruction;
the CLI caps intent output at 1536 tokens. Production vLLM configuration is not
changed. Long/oversized prompts or incomplete generation remain explicit errors.

## Running the tools

Software regression: local `1368 passed, 4 skipped`; server `1369 passed,
3 skipped`. These are engineering checks, not model task accuracy.

Use the model-service Python environment on the server and a NEW output folder:

```bash
python tools/qwen_planner_experiment.py understand \
  --understanding-strategy joint \
  --input config/qwen_task_understanding_dev.jsonl \
  --output-dir artifacts/validation/<new-development-run> \
  --limit 12 --timeout-s 120

python tools/qwen_planner_experiment.py understand \
  --understanding-strategy joint \
  --input artifacts/validation/qwen_attribution_20261028_capture/requests.jsonl \
  --output-dir artifacts/validation/<new-real-request-review> \
  --limit 1 --timeout-s 120
```

Development failures produce a nonzero CLI exit status even when JSON is valid.
Raw instructions/outputs remain private artifacts, not GitHub training data.

## Next work

1. Improve action/condition binding using separate development material. Preserve
   this probe result; do not repeatedly tune on it and then call it an unseen pass.
2. Before considering adaptation/training, audit sufficient independent labeled
   multi-step examples and preserve negative/conditional coverage; this work does
   not assume the existing B1 training release is suitable for this new interface.
3. Ground target descriptions to verified RGB/track associations, not scenario
   names, only after intent quality improves.
4. Separate upstream hard capability/legal constraints from task-intent hints.
   Reconcile requested tasks with hard constraints in a distinct validated stage.
5. No full-route or production promotion until independently checked task
   coverage/order/slots and short-event closed-loop gates are met.
