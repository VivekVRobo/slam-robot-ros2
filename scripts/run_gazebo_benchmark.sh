#!/usr/bin/env bash
set -euo pipefail
DURATION=${BENCHMARK_DURATION_S:-52}
ARTIFACTS=${ARTIFACTS_DIR:-artifacts}
mkdir -p "$ARTIFACTS" "$ARTIFACTS/bags"
LAUNCH_PID=''; DRIVER_PID=''; BAG_PID=''; PROFILE_PID=''; SCAN_HZ_PID=''; CMD_TRACE_PID=''
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

stop_process_group() {
  local pid=${1:-}
  local label=${2:-process-group}
  local int_grace=${3:-12}
  local term_grace=${4:-5}

  [[ -z "$pid" ]] && return 0
  if ! kill -0 "$pid" 2>/dev/null; then
    wait "$pid" 2>/dev/null || true
    return 0
  fi

  kill -INT -- "-$pid" 2>/dev/null || true
  for _ in $(seq 1 "$int_grace"); do
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" 2>/dev/null || true
      return 0
    fi
    sleep 1
  done

  echo "$label did not stop after SIGINT; escalating to SIGTERM"
  kill -TERM -- "-$pid" 2>/dev/null || true
  for _ in $(seq 1 "$term_grace"); do
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" 2>/dev/null || true
      return 0
    fi
    sleep 1
  done

  echo "$label did not stop after SIGTERM; escalating to SIGKILL"
  kill -KILL -- "-$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

capture_runtime_diagnostics() {
  ros2 node list > "$ARTIFACTS/runtime-nodes.txt" 2>&1 || true
  gz topic -l > "$ARTIFACTS/gazebo-topics.txt" 2>&1 || true
}

cleanup() {
  set +e
  stop_process "$SCAN_HZ_PID" 'scan-rate sampler' 2 2
  stop_process "$CMD_TRACE_PID" 'Gazebo cmd_vel trace' 2 2
  stop_process "$BAG_PID" 'ros2 bag recorder' 8 4
  stop_process "$DRIVER_PID" 'benchmark driver' 4 2
  stop_process_group "$LAUNCH_PID" 'ROS launch graph' 12 5
  if [[ -n "$PROFILE_PID" ]]; then
    if kill -0 "$PROFILE_PID" 2>/dev/null; then
      kill -TERM "$PROFILE_PID" 2>/dev/null || true
    fi
    wait "$PROFILE_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

LAUNCH_LOG="$ARTIFACTS/launch.log"
# Run the launch graph in its own process group. ros2 launch can leave child
# nodes alive after the parent exits; evidence must not be hashed while the
# trajectory recorder is still able to append samples.
setsid ros2 launch slam_robot_ros2 simulation_mapping.launch.py headless:=true record_trajectory:=true run_benchmark_driver:=false >"$LAUNCH_LOG" 2>&1 &
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

gz topic -e -t /model/slam_robot/cmd_vel > "$ARTIFACTS/cmd-vel-gz.txt" 2>&1 &
CMD_TRACE_PID=$!

ros2 run slam_robot_ros2 benchmark_driver --ros-args -p use_sim_time:=true >>"$LAUNCH_LOG" 2>&1 &
DRIVER_PID=$!

ros2 bag record -o "$ARTIFACTS/bags/gazebo_loop_square" --topics /scan /cmd_vel /odom /ground_truth/odom /tf /tf_static /map /diagnostics /clock &
BAG_PID=$!
python3 tools/process_profile.py --duration "$DURATION" --match slam_toolbox --match gz --match ros_gz_bridge --output "$ARTIFACTS/resource-profile.json" &
PROFILE_PID=$!

# The driver exits only after every configured segment has completed and a
# zero-velocity command has been published. DURATION is a wall-clock watchdog,
# not the trajectory-completion signal.
driver_complete=false
for _ in $(seq 1 "$DURATION"); do
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
    if [[ "$DRIVER_RC" -ne 0 ]]; then
      capture_runtime_diagnostics
      echo "benchmark driver failed during benchmark capture (exit=$DRIVER_RC)."
      cat "$LAUNCH_LOG"
      exit 2
    fi
    driver_complete=true
    break
  fi
  sleep 1
done

if [[ "$driver_complete" != true ]]; then
  capture_runtime_diagnostics
  echo "benchmark driver did not complete within ${DURATION}s watchdog"
  cat "$LAUNCH_LOG"
  exit 2
fi

# Give the final stop command and recorder one bounded second to propagate the
# completed state before saving the map and shutting down evidence capture.
sleep 1
ros2 run nav2_map_server map_saver_cli -f "$ARTIFACTS/map" --ros-args -p use_sim_time:=true -p save_map_timeout:=10.0

stop_process "$CMD_TRACE_PID" 'Gazebo cmd_vel trace' 2 2; CMD_TRACE_PID=''
stop_process "$BAG_PID" 'ros2 bag recorder' 12 5; BAG_PID=''
stop_process_group "$LAUNCH_PID" 'ROS launch graph' 15 5; LAUNCH_PID=''
wait "$PROFILE_PID" || true; PROFILE_PID=''
trap - EXIT INT TERM

if [[ "$RECORDER_OUTPUT" != "$ARTIFACTS/trajectory.csv" && -s "$RECORDER_OUTPUT" ]]; then
  mv "$RECORDER_OUTPUT" "$ARTIFACTS/trajectory.csv"
fi

[[ -s "$ARTIFACTS/runtime-topics.txt" ]] || { echo 'runtime topic snapshot was not generated'; exit 3; }
[[ -s "$ARTIFACTS/trajectory.csv" ]] || { echo 'trajectory.csv was not generated'; exit 4; }
[[ -s "$ARTIFACTS/map.pgm" ]] || { echo 'map.pgm was not generated'; exit 5; }
[[ -s "$ARTIFACTS/map.yaml" ]] || { echo 'map.yaml was not generated'; exit 6; }
[[ -s "$ARTIFACTS/resource-profile.json" ]] || { echo 'resource profile was not generated'; exit 7; }
[[ -s "$ARTIFACTS/bags/gazebo_loop_square/metadata.yaml" ]] || { echo 'rosbag metadata was not generated'; exit 8; }
[[ -s "$ARTIFACTS/cmd-vel-gz.txt" ]] || { echo 'Gazebo cmd_vel trace was not generated'; exit 9; }

trajectory_sha=''
trajectory_stable=0
for _ in $(seq 1 10); do
  current_sha=$(sha256sum "$ARTIFACTS/trajectory.csv" | awk '{print $1}')
  if [[ "$current_sha" == "$trajectory_sha" ]]; then
    trajectory_stable=$((trajectory_stable + 1))
    if (( trajectory_stable >= 2 )); then
      break
    fi
  else
    trajectory_sha="$current_sha"
    trajectory_stable=0
  fi
  sleep 1
done
if (( trajectory_stable < 2 )); then
  echo 'trajectory.csv did not settle after launch shutdown'
  exit 10
fi

bash scripts/evaluate_benchmark.sh "$ARTIFACTS/trajectory.csv" "$ARTIFACTS/map.pgm" "$ARTIFACTS/resource-profile.json"
