# Qwen2.5-VL-7B-AWQ A800 latency evidence

Hardware: NVIDIA A800-SXM4-80GB. Runtime: CARLA 0.9.16, CUDA 13.2,
vLLM with AWQ Marlin, one constrained high-level action token and a fixed
224x224 / 64-token visual budget.

- `baseline_first50_summary.json`: pre-optimization first 50 complete
  sensor-ready-to-validated-trajectory samples.
- `optimized_partial_summary.json`: optimized run stopped on user request
  after 29 terminal scenarios. Scenario 30 was interrupted and is excluded
  from scenario accuracy. All 34 already-completed latency samples remain
  valid complete sensor-to-trajectory measurements.

The optimized run is partial evidence, not an 83-scenario completion claim.
It recorded 29/29 scenario success, 29/29 multimodal semantic alignment, and
sensor-to-trajectory P95 131.598 ms with no sample above 150 ms.
