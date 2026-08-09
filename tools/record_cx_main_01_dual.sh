#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
output_dir=${1:-"$repo_dir/artifacts/8.9_recording"}
display_name=${DISPLAY:-:0}
mkdir -p "$output_dir/logs" "$output_dir/qwen_images"

find_window_id() {
    local title=$1
    xwininfo -root -tree -display "$display_name" 2>/dev/null |
        awk -v title="$title" 'index($0, title) { print $1; exit }'
}

runner_pid=""
ffmpeg_pid=""
cleanup() {
    if [[ -n "$runner_pid" ]] && kill -0 "$runner_pid" 2>/dev/null; then
        kill -INT "$runner_pid" 2>/dev/null || true
        wait "$runner_pid" 2>/dev/null || true
    fi
    if [[ -n "$ffmpeg_pid" ]] && kill -0 "$ffmpeg_pid" 2>/dev/null; then
        kill -INT "$ffmpeg_pid" 2>/dev/null || true
        wait "$ffmpeg_pid" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

cd "$repo_dir"
PYTHONUNBUFFERED=1 conda run --no-capture-output -n carla312 \
    python -m integration.carla_runner \
    --scenario-file scenarios/acceptance_suite/complex/CX_MAIN_01_safe_urban_mission.json \
    --qwen-service-url http://127.0.0.1:18000 \
    --qwen-mode planner_v2 \
    --qwen-image-transport inline \
    --qwen-image-prefix artifacts/8.9_recording/qwen_images \
    --perception-mode sensors \
    --scenario-facts-mode perception \
    --sensor-profile demo \
    --realtime \
    --ui-mode demo \
    --ui-fps 10 \
    --log-dir artifacts/8.9_recording/logs \
    --follow-spectator \
    --timeout-s 30 \
    --sensor-timeout-s 1 \
    --sensor-warmup-frames 20 \
    --qwen-timeout-ms 30000 \
    --qwen-queue-size 1 \
    --watchdog-startup-grace-s 5 \
    --print-every 20 \
    >"$output_dir/run_stdout.log" 2>&1 &
runner_pid=$!

carla_window=""
first_person_window=""
last_carla_window=""
last_first_person_window=""
stable_window_checks=0
for _ in $(seq 1 300); do
    carla_window=$(find_window_id "CarlaUE4" || true)
    first_person_window=$(find_window_id "CARLA 语音控制演示" || true)
    if [[ -n "$carla_window" && -n "$first_person_window" ]]; then
        if [[ "$carla_window" == "$last_carla_window" && \
              "$first_person_window" == "$last_first_person_window" ]]; then
            stable_window_checks=$((stable_window_checks + 1))
        else
            stable_window_checks=0
        fi
        last_carla_window=$carla_window
        last_first_person_window=$first_person_window
        if [[ $stable_window_checks -ge 10 ]]; then
            break
        fi
    fi
    if ! kill -0 "$runner_pid" 2>/dev/null; then
        wait "$runner_pid"
        exit $?
    fi
    sleep 0.1
done

if [[ -z "$carla_window" || -z "$first_person_window" ]]; then
    echo "failed to locate CARLA and first-person windows" >&2
    exit 2
fi

ffmpeg -hide_banner -loglevel warning -y \
    -thread_queue_size 512 -f x11grab -framerate 10 -draw_mouse 0 \
    -window_id "$carla_window" -use_wallclock_as_timestamps 1 -i "$display_name" \
    -thread_queue_size 512 -f x11grab -framerate 10 -draw_mouse 0 \
    -window_id "$first_person_window" -use_wallclock_as_timestamps 1 -i "$display_name" \
    -map 0:v:0 -an -c:v libx264 -preset veryfast -crf 28 -pix_fmt yuv420p \
    -movflags +faststart "$output_dir/CX_MAIN_01_CARLA_follow_view.mp4" \
    -map 1:v:0 -an -c:v libx264 -preset veryfast -crf 28 -pix_fmt yuv420p \
    -movflags +faststart "$output_dir/CX_MAIN_01_first_person_view.mp4" \
    >"$output_dir/ffmpeg.log" 2>&1 &
ffmpeg_pid=$!

# Pygame creates and reparents its X11 window during startup. Fail the run
# immediately if either captured window disappeared before ffmpeg attached.
sleep 2
if ! kill -0 "$ffmpeg_pid" 2>/dev/null; then
    set +e
    wait "$ffmpeg_pid"
    ffmpeg_status=$?
    set -e
    ffmpeg_pid=""
    echo "ffmpeg failed to attach to stable CARLA/UI windows" >&2
    exit "$ffmpeg_status"
fi

set +e
wait "$runner_pid"
runner_status=$?
set -e
runner_pid=""

if kill -0 "$ffmpeg_pid" 2>/dev/null; then
    kill -INT "$ffmpeg_pid" 2>/dev/null || true
fi
set +e
wait "$ffmpeg_pid"
ffmpeg_status=$?
set -e
ffmpeg_pid=""

video_frame_count() {
    ffprobe -v error -select_streams v:0 -count_frames \
        -show_entries stream=nb_read_frames \
        -of default=noprint_wrappers=1:nokey=1 "$1"
}

synchronize_video_frames() {
    local video_path=$1
    local current_frames=$2
    local target_frames=$3
    local synced_path="${video_path%.mp4}.sync.tmp.mp4"
    if (( current_frames <= target_frames )); then
        return
    fi
    ffmpeg -hide_banner -loglevel error -y -i "$video_path" \
        -map 0:v:0 -an -c copy -frames:v "$target_frames" "$synced_path"
    mv "$synced_path" "$video_path"
}

carla_video="$output_dir/CX_MAIN_01_CARLA_follow_view.mp4"
first_person_video="$output_dir/CX_MAIN_01_first_person_view.mp4"
carla_frames=$(video_frame_count "$carla_video")
first_person_frames=$(video_frame_count "$first_person_video")
if (( carla_frames < first_person_frames )); then
    synchronized_frames=$carla_frames
else
    synchronized_frames=$first_person_frames
fi
synchronize_video_frames "$carla_video" "$carla_frames" "$synchronized_frames"
synchronize_video_frames "$first_person_video" "$first_person_frames" "$synchronized_frames"

{
    echo "recording_status=SUCCEEDED"
    echo "runner_status=$runner_status"
    echo "ffmpeg_status=$ffmpeg_status"
    echo "carla_window=$carla_window"
    echo "first_person_window=$first_person_window"
    echo "synchronized_frames=$synchronized_frames"
    ffprobe -v error -show_entries format=filename,duration,size \
        -of default=noprint_wrappers=1 "$carla_video"
    ffprobe -v error -show_entries format=filename,duration,size \
        -of default=noprint_wrappers=1 "$first_person_video"
} >"$output_dir/recording_manifest.txt"

if [[ $runner_status -ne 0 ]]; then
    exit "$runner_status"
fi
if [[ $ffmpeg_status -ne 0 && $ffmpeg_status -ne 255 ]]; then
    exit "$ffmpeg_status"
fi
