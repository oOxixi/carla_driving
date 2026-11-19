#!/usr/bin/env bash
set -u
root="$PWD/artifacts/runtime/multisensor_follow_20261112"
for case_name in 40 60 occlusion; do
  case "$case_name" in
    40) scenario=artifacts/runtime/temporal_integration_20261112/scenario_40m.json ;;
    60) scenario=artifacts/runtime/temporal_integration_20261112/scenario_60m.json ;;
    occlusion) scenario=artifacts/runtime/crop_follow_20261112/scenario_occlusion.json ;;
  esac
  out="$root/${case_name}_model_input";mkdir -p "$out"
  env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 SHADOW_MODEL_INPUT=1 SHADOW_EVAL_DIR="$out/evaluation" PYTHONPATH="$PWD" /home/tiaozhansai/carla-driving-challenge/.venv/bin/python -u -m tools.target_demo.evaluate_shadow_sensor_fusion --host 127.0.0.1 --port 22130 --scenario-file "$scenario" --use-current-map --perception-mode sensors --scenario-facts-mode perception --sensor-profile default --rgb-detector-model /home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx --experimental-temporal-lidar-frames 4 --experimental-crop-detector --qwen-service-url http://127.0.0.1:18131 --qwen-mode planner_v2 --qwen-timeout-ms 15000 --qwen-image-root "$PWD" --qwen-image-prefix artifacts/runtime/multisensor_follow_20261112/images --sensor-timeout-s 4 --sensor-warmup-frames 30 --warmup-frames 10 --timeout-s 30 --realtime --max-frames 120 --print-every 30 --log-dir "$out" >"$out/console.log" 2>&1
  code=$?;printf '%s %s\n' "$case_name" "$code" >> "$root/model_input_batch_status.txt"
  if [ "$code" -ne 0 ]; then exit "$code"; fi
done
