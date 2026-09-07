#!/usr/bin/env bash
set -euo pipefail
DURATION=${BENCHMARK_DURATION_S:-52}
ARTIFACTS=${ARTIFACTS_DIR:-artifacts}
mkdir -p "$ARTIFACTS" "$ARTIFACTS/bags"
LAUNCH_PID=''; BAG_PID=''; PROFILE_PID=''
cleanup() {
  set +e
  [[ -n "$BAG_PID" ]] && kill -INT "$BAG_PID" 2>/dev/null
  [[ -n "$LAUNCH_PID" ]] && kill -INT "$LAUNCH_PID" 2>/dev/null
  [[ -n "$PROFILE_PID" ]] && wait "$PROFILE_PID" 2>/dev/null
  [[ -n "$BAG_PID" ]] && wait "$BAG_PID" 2>/dev/null
  [[ -n "$LAUNCH_PID" ]] && wait "$LAUNCH_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

ros2 launch slam_robot_ros2 simulation_mapping.launch.py headless:=true record_trajectory:=true run_benchmark_driver:=true &
LAUNCH_PID=$!

REQUIRED_TOPICS=(/scan /odom /ground_truth/odom /tf /tf_static /map /clock)
for _ in $(seq 1 60); do
  TOPICS=$(ros2 topic list 2>/dev/null || true)
  ready=true
  for topic in "${REQUIRED_TOPICS[@]}"; do
    if ! grep -qx "$topic" <<<"$TOPICS"; then
      ready=false
      break
    fi
  done
  [[ "$ready" == true ]] && break
  sleep 1
done

TOPICS=$(ros2 topic list)
printf '%s\n' "$TOPICS" > "$ARTIFACTS/runtime-topics.txt"
for topic in "${REQUIRED_TOPICS[@]}"; do
  grep -qx "$topic" <<<"$TOPICS" || { echo "missing required runtime topic $topic"; exit 2; }
done

ros2 topic hz /scan --window 5 > "$ARTIFACTS/scan-hz.txt" 2>&1 &
SCAN_HZ_PID=$!
sleep 6
kill "$SCAN_HZ_PID" 2>/dev/null || true
wait "$SCAN_HZ_PID" 2>/dev/null || true

ros2 bag record -o "$ARTIFACTS/bags/gazebo_loop_square" /scan /odom /ground_truth/odom /tf /tf_static /map /diagnostics /clock &
BAG_PID=$!
python tools/process_profile.py --duration "$DURATION" --match slam_toolbox --match gz --match ros_gz_bridge --output "$ARTIFACTS/resource-profile.json" &
PROFILE_PID=$!

sleep "$DURATION"
ros2 run nav2_map_server map_saver_cli -f "$ARTIFACTS/map" --ros-args -p use_sim_time:=true

kill -INT "$BAG_PID"; wait "$BAG_PID" || true; BAG_PID=''
kill -INT "$LAUNCH_PID"; wait "$LAUNCH_PID" || true; LAUNCH_PID=''
wait "$PROFILE_PID" || true; PROFILE_PID=''
trap - EXIT INT TERM

[[ -s "$ARTIFACTS/runtime-topics.txt" ]] || { echo 'runtime topic snapshot was not generated'; exit 3; }
[[ -s "$ARTIFACTS/trajectory.csv" ]] || { echo 'trajectory.csv was not generated'; exit 4; }
[[ -s "$ARTIFACTS/map.pgm" ]] || { echo 'map.pgm was not generated'; exit 5; }
[[ -s "$ARTIFACTS/map.yaml" ]] || { echo 'map.yaml was not generated'; exit 6; }
bash scripts/evaluate_benchmark.sh "$ARTIFACTS/trajectory.csv" "$ARTIFACTS/map.pgm" "$ARTIFACTS/resource-profile.json"
