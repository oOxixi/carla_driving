#!/usr/bin/env bash
set -u
root="$PWD/artifacts/runtime/direct_sensor_follow_20261112"
for case_name in 40 60; do
  out="$root/multi_${case_name}m";mkdir -p "$out"
  env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 SHADOW_EVAL_DIR="$out/evaluation" PYTHONPATH="$PWD" /home/tiaozhansai/carla-driving-challenge/.venv/bin/python -u -m tools.target_demo.evaluate_shadow_sensor_fusion --host 127.0.0.1 --port 22140 --scenario-file "$root/scenario_multi_${case_name}m.json" --use-current-map --perception-mode sensors --scenario-facts-mode perception --sensor-profile default --rgb-detector-model /home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx --experimental-temporal-lidar-frames 4 --experimental-crop-detector --sensor-timeout-s 4 --sensor-warmup-frames 30 --warmup-frames 10 --timeout-s 30 --realtime --max-frames 150 --print-every 30 --log-dir "$out" >"$out/console.log" 2>&1
  code=$?;printf '%s %s\n' "$case_name" "$code" >> "$root/multicar_batch_status.txt"
  if [ "$code" -ne 0 ]; then exit "$code"; fi
done
