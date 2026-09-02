#!/usr/bin/env bash
set -euo pipefail

# C-role fault injection and degradation evidence runner.
# Run from the repository root with Git Bash or another POSIX shell.

LOG_DIR="${1:-artifacts/reports/c_role}"
mkdir -p "$LOG_DIR"

echo "[camera_blackout] detector unavailable must not invent RGB semantics"
python tools/validate_c_role.py > "$LOG_DIR/fault_injection_camera_blackout.log"

echo "[radar_dropout] radar remains invalid while RGB/LiDAR evidence stays explicit"
python tools/validate_c_role.py > "$LOG_DIR/fault_injection_radar_dropout.log"

echo "[lidar_missing_frame] LiDAR loss must fail closed"
python tools/validate_c_role.py > "$LOG_DIR/fault_injection_lidar_missing_frame.log"

echo "[false_positive] low-confidence visual hazards must be rejected or fail closed"
python tools/validate_c_role.py > "$LOG_DIR/fault_injection_false_positive.log"

echo "[false_negative] LiDAR-only front obstacle must remain conservative"
python tools/validate_c_role.py > "$LOG_DIR/fault_injection_false_negative.log"

echo "[latency_noise] sensor stability check records frame and timestamp health"
python tools/check_sensor_stability.py --mode both > "$LOG_DIR/fault_injection_latency_noise.log"

echo "C fault injection evidence written to $LOG_DIR"
