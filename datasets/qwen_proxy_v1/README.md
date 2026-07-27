# Qwen high-level decision proxy set

`cases.jsonl` is a frozen local proxy set for the restricted high-level Qwen
decision boundary. It is not an organizer-provided or official test set.

Each line contains:

- `case_id` and `category`;
- a Chinese `voice_command`;
- optional scene, perception and safety-state overrides;
- expected action(s), confirmation behaviour and optional target speed.

The benchmark uses `tools/run_qwen_batch_benchmark.py`. The current 20-case
set covers normal speed/stop/start, emergency and slowdown commands, red-light
and front-TTC conflicts, ambiguous targets and invalid visual input.

The 2026-07-28 run reused one real Town03 RGB frame with frozen proxy context.
It measures strict response parsing and high-level semantic contracts. It does
not measure multi-image visual generalization or target-track association, and
its results must not be presented as hidden-test performance.
