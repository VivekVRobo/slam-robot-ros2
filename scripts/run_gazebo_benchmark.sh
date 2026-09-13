#!/usr/bin/env bash
set -euo pipefail
DURATION=${BENCHMARK_DURATION_S:-52}
ARTIFACTS=${ARTIFACTS_DIR:-artifacts}
mkdir -p "$ARTIFACTS" "$ARTIFACTS/bags"
LAUNCH_PID=''; DRIVER_PID=''; BAG_PID=''; PROFILE_PID=''; SCAN_HZ_PID=''
RECORDER_OUTPUT="artifacts/trajectory.csv"
rm -f "$RECORDER_OUTPUT"

stop_process() {
  local pid=${1:-}
  local label=${2:-process}
  local int_grace=${3:-12}
  local term_grace=${4:-5}

  [[ -z "$pid" ]] && return 0
  if ! kill -0 "$pid" 2>/dev/null; then
    wait "$pid" 2>/dev/null || true
    return 0
  fi

  kill -INT "$pid" 2>/dev/null || true
  for _ in $(seq 1 "$int_grace"); do
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" 2>/dev/null || true
      return 0
    fi
    sleep 1
  done

  echo "$label did not stop after SIGINT; escalating to SIGTERM"
  kill -TERM "$pid" 2>/dev/null || true
  for _ in $(seq 1 "$term_grace"); do
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" 2>/dev/null || true
      return 0
    fi
    sleep 1
  done

  echo "$label did not stop after SIGTERM; escalating to SIGKILL"
  kill -KILL "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

capture_runtime_diagnostics() {
  ros2 node list > "$ARTIFACTS/runtime-nodes.txt" 2>&1 || true
  gz topic -l > "$ARTIFACTS/gazebo-topics.txt" 2>&1 || true
}

cleanup() {
  set +e
  stop_process "$SCAN_HZ_PID" 'scan-rate sampler' 2 2
  stop_process "$BAG_PID" 'ros2 bag recorder' 8 4
  stop_process "$DRIVER_PID" 'benchmark driver' 4 2
  stop_process "$LAUNCH_PID" 'ROS launch graph' 12 5
  if [[ -n "$PROFILE_PID" ]]; then
    if kill -0 "$PROFILE_PID" 2>/dev/null; then
      kill -TERM "$PROFILE_PID" 2>/dev/null || true
    fi
    wait "$PROFILE_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

LAUNCH_LOG="$ARTIFACTS/launch.log"
ros2 launch slam_robot_ros2 simulation_mapping.launch.py headless:=true record_trajectory:=true run_benchmark_driver:=false >"$LAUNCH_LOG" 2>&1 &
LAUNCH_PID=$!

REQUIRED_TOPICS=(/scan /odom /ground_truth/odom /tf /tf_static /map /clock)
ready=false
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

  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    if wait "$LAUNCH_PID"; then LAUNCH_RC=0; else LAUNCH_RC=$?; fi
    LAUNCH_PID=''
    printf '%s\n' "$TOPICS" > "$ARTIFACTS/runtime-topics.txt"
    capture_runtime_diagnostics
    echo "Gazebo/SLAM launch exited before the required runtime graph was ready (exit=$LAUNCH_RC)."
    cat "$LAUNCH_LOG"
    exit 2
  fi
  sleep 1
done

TOPICS=$(ros2 topic list 2>/dev/null || true)
printf '%s\n' "$TOPICS" > "$ARTIFACTS/runtime-topics.txt"
for topic in "${REQUIRED_TOPICS[@]}"; do
  if ! grep -qx "$topic" <<<"$TOPICS"; then
    capture_runtime_diagnostics
    echo "missing required runtime topic $topic"
    cat "$LAUNCH_LOG"
    exit 2
  fi
done

ros2 topic hz /scan --window 5 > "$ARTIFACTS/scan-hz.txt" 2>&1 &
SCAN_HZ_PID=$!
sleep 6
stop_process "$SCAN_HZ_PID" 'scan-rate sampler' 2 2
SCAN_HZ_PID=''

# Start the deterministic drive only after Gazebo, bridges, SLAM and scan rate
# have been proven ready. Starting it inside the launch graph can consume path
# segments while transport endpoints are still coming online.
ros2 run slam_robot_ros2 benchmark_driver --ros-args -p use_sim_time:=true >>"$LAUNCH_LOG" 2>&1 &
DRIVER_PID=$!

ros2 bag record -o "$ARTIFACTS/bags/gazebo_loop_square" --topics /scan /odom /ground_truth/odom /tf /tf_static /map /diagnostics /clock &
BAG_PID=$!
python3 tools/process_profile.py --duration "$DURATION" --match slam_toolbox --match gz --match ros_gz_bridge --output "$ARTIFACTS/resource-profile.json" &
PROFILE_PID=$!

sleep "$DURATION"
if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
  if wait "$LAUNCH_PID"; then LAUNCH_RC=0; else LAUNCH_RC=$?; fi
  LAUNCH_PID=''
  capture_runtime_diagnostics
  echo "Gazebo/SLAM launch exited during benchmark capture (exit=$LAUNCH_RC)."
  cat "$LAUNCH_LOG"
  exit 2
fi
if ! kill -0 "$DRIVER_PID" 2>/dev/null; then
  if wait "$DRIVER_PID"; then DRIVER_RC=0; else DRIVER_RC=$?; fi
  DRIVER_PID=''
  capture_runtime_diagnostics
  echo "benchmark driver exited during benchmark capture (exit=$DRIVER_RC)."
  cat "$LAUNCH_LOG"
  exit 2
fi

ros2 run nav2_map_server map_saver_cli -f "$ARTIFACTS/map" --ros-args -p use_sim_time:=true -p save_map_timeout:=10.0

# Flush evidence without allowing stuck ROS processes to consume the CI timeout.
stop_process "$BAG_PID" 'ros2 bag recorder' 12 5; BAG_PID=''
stop_process "$DRIVER_PID" 'benchmark driver' 4 2; DRIVER_PID=''
stop_process "$LAUNCH_PID" 'ROS launch graph' 15 5; LAUNCH_PID=''
wait "$PROFILE_PID" || true; PROFILE_PID=''
trap - EXIT INT TERM

# The trajectory recorder currently writes to its package default path. Move only
# this run's freshly-created output into the active evidence directory.
if [[ "$RECORDER_OUTPUT" != "$ARTIFACTS/trajectory.csv" && -s "$RECORDER_OUTPUT" ]]; then
  mv "$RECORDER_OUTPUT" "$ARTIFACTS/trajectory.csv"
fi

[[ -s "$ARTIFACTS/runtime-topics.txt" ]] || { echo 'runtime topic snapshot was not generated'; exit 3; }
[[ -s "$ARTIFACTS/trajectory.csv" ]] || { echo 'trajectory.csv was not generated'; exit 4; }
[[ -s "$ARTIFACTS/map.pgm" ]] || { echo 'map.pgm was not generated'; exit 5; }
[[ -s "$ARTIFACTS/map.yaml" ]] || { echo 'map.yaml was not generated'; exit 6; }
[[ -s "$ARTIFACTS/resource-profile.json" ]] || { echo 'resource profile was not generated'; exit 7; }
[[ -s "$ARTIFACTS/bags/gazebo_loop_square/metadata.yaml" ]] || { echo 'rosbag metadata was not generated'; exit 8; }

bash scripts/evaluate_benchmark.sh "$ARTIFACTS/trajectory.csv" "$ARTIFACTS/map.pgm" "$ARTIFACTS/resource-profile.json"
