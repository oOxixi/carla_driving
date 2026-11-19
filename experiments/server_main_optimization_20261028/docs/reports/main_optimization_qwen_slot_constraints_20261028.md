# Request-grounded shadow output constraints (2026-10-28)

## Changes, still offline only

This follows the [attribution report](main_optimization_qwen_attribution_20261028.md).
The production adapter, control, safety modules and official scenario contracts
are not switched to the structured planner. Neither `main` nor `challenge` is changed.

- Bind generated `target_id` slots to the actual ModelRequest target IDs or null.
  Scenario-owned completion targets are not treated as visual detections. A lane
  token such as `CURRENT` is never a legal target ID.
- Bound speed by both the current speed limit and `max_target_speed_mps`, within
  the existing validator ceiling. Preserve upstream allowed behaviors; do not
  silently remove hard constraints to improve apparent model success.
- Bound lane slots to the supplied lane context, plus route-branch/null slots.
- New `flag_sets_v1` wire representation uses optional true-valued keys for
  preconditions/replanning sets. This avoids unsupported `uniqueItems` in the
  deployed grammar without post-generation deduplication. Local full-schema
  validation still applies after lossless set conversion.
- Add a generic action/completion grammar and validation: for example SLOW_DOWN
  cannot use STOPPED as its completion. Model still chooses action, target,
  speed, condition and step order; no semantic steps are automatically added.
- Report validation layers separately, preserve raw output and all useful slot
  errors, and explicitly report visual grounding and task accuracy as unverified.
- CLI default shadow format is `flag_sets_v1`; use `--shadow-format full_json`
  for the prior representation. This does not change the production one-token API.

## Real 2B development replay, not a frozen test or formal gate

Same captured pedestrian/overtake request as the first report:
`qwen-1dc25c814ffe49c1840358d2a181ed4a`. This request was already inspected during
development. Do not count repeated runs as independent unseen samples.

Server evidence is under
`/home/tiaozhansai/carla-driving-main-optimization/artifacts/validation/`.

| Directory | Observed result | Boundary |
| --- | --- | --- |
| `qwen_attribution_20261028_shadow_slots_v3` | Original/no-RGB both passed the previous contract validator | Inspection found SLOW_DOWN paired with STOPPED; this motivated the additional compatibility guard, not a driving success |
| `qwen_attribution_20261028_shadow_slots_v4` | Both passed wire, semantic schema, action/completion, PlanValidator and compiler checks | Both still produced only one SLOW_DOWN step; the requested compound task is not fulfilled |

The v4 model outputs targeted `C-0027`, at approximately 11.11 m/s, with
SPEED_REACHED completion and a 1-1.5 second timeout. They did NOT produce the
requested yield/overtake/return/resume sequence. They are not ready for vehicle
execution despite passing contract checks. Do not call this 100% task accuracy.

Input candidates were generic `obstacle` targets. ModelRequest V1 does not carry
a verified RGB-region-to-track association. Restricting IDs prevents invented
names; it does not prove that the model selected the correct physical pedestrian
or slow vehicle. The model's self-reported 0.95/1.0 confidence is not calibrated.

The upstream allowed behaviors for this captured request also omit KEEP_LANE
and SET_SPEED, so straightforward cruise-resumption steps are restricted before
the model runs. This is a policy-contract limitation, not evidence that increasing
model size alone will resolve the issue. This update deliberately does not guess
which upstream restrictions are hard safety limits and which are task hints.

## Remaining priority

Software verification for this update: local `1347 passed, 4 skipped`; server
`1348 passed, 3 skipped`. All 155 scenario contracts and official scene static
validation pass. These counts do not measure model task accuracy or driving.

1. Separate hard capability/legal constraints from NLU task hints upstream, with
   explicit provenance and regression tests, before widening the shadow planner.
2. Evaluate independently labeled task coverage/order/targets/conditions, in
   addition to structural and feasibility checks. Freeze new evaluation cases;
   do not tune repeatedly on a formal test set.
3. Improve the compact semantic generation interface on development cases; retain
   all failed raw results. Do not restore hidden keyword-based task completion.
4. Add verified RGB detector/track associations before claiming visual grounding.
5. Only then consider a reviewed short-event closed-loop pilot. Do not promote
   this offline output or restart production merely because contract checks pass.
