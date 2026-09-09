#!/usr/bin/env bash
set -euo pipefail
DURATION=${BENCHMARK_DURATION_S:-52}
ARTIFACTS=${ARTIFACTS_DIR:-artifacts}
mkdir -p "$ARTIFACTS" "$ARTIFACTS/bags"
LAUNCH_PID=''; BAG_PID=''; PROFILE_PID=''

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

cleanup() {
  set +e
  stop_process "$BAG_PID" 'ros2 bag recorder' 8 4
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
ros2 launch slam_robot_ros2 simulation_mapping.launch.py headless:=true record_trajectory:=true run_benchmark_driver:=true >"$LAUNCH_LOG" 2>&1 &
LAUNCH_PID=$!

for _ in $(seq 1 60); do
  TOPICS=$(ros2 topic list 2>/dev/null || true)
  if grep -qx '/scan' <<<"$TOPICS" && grep -qx '/odom' <<<"$TOPICS" && grep -qx '/ground_truth/odom' <<<"$TOPICS" && grep -qx '/map' <<<"$TOPICS"; then
    break
  fi

  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    if wait "$LAUNCH_PID"; then
      LAUNCH_RC=0
    else
      LAUNCH_RC=$?
    fi
    LAUNCH_PID=''
    printf '%s\n' "$TOPICS" > "$ARTIFACTS/runtime_topics.txt"
    ros2 node list > "$ARTIFACTS/runtime_nodes.txt" 2>&1 || true
    gz topic -l > "$ARTIFACTS/gazebo_topics.txt" 2>&1 || true
    echo "Gazebo/SLAM launch exited before the required runtime graph was ready (exit=$LAUNCH_RC)."
    cat "$LAUNCH_LOG"
    exit 2
  fi

  sleep 1
done

TOPICS=$(ros2 topic list 2>/dev/null || true)
printf '%s\n' "$TOPICS" > "$ARTIFACTS/runtime_topics.txt"
for topic in /scan /odom /ground_truth/odom /map; do
  if ! grep -qx "$topic" <<<"$TOPICS"; then
    ros2 node list > "$ARTIFACTS/runtime_nodes.txt" 2>&1 || true
    gz topic -l > "$ARTIFACTS/gazebo_topics.txt" 2>&1 || true
    echo "missing required topic $topic"
    cat "$LAUNCH_LOG"
    exit 2
  fi
done

ros2 bag record -o "$ARTIFACTS/bags/gazebo_loop_square" /scan /odom /ground_truth/odom /tf /tf_static /map /diagnostics /clock &
BAG_PID=$!
python3 tools/process_profile.py --duration "$DURATION" --match slam_toolbox --match gz --match ros_gz_bridge --output "$ARTIFACTS/resource-profile.json" &
PROFILE_PID=$!

sleep "$DURATION"
ros2 run nav2_map_server map_saver_cli -f "$ARTIFACTS/map" --ros-args -p use_sim_time:=true

# Finalization must never be allowed to consume the entire CI timeout. Give
# rosbag and the ROS launch graph a graceful SIGINT window so bags and the
# trajectory recorder can flush, then escalate only if a process is stuck.
stop_process "$BAG_PID" 'ros2 bag recorder' 12 5; BAG_PID=''
stop_process "$LAUNCH_PID" 'ROS launch graph' 15 5; LAUNCH_PID=''
wait "$PROFILE_PID" || true; PROFILE_PID=''
trap - EXIT INT TERM

[[ -s "$ARTIFACTS/trajectory.csv" ]] || { echo 'trajectory.csv was not generated'; exit 3; }
[[ -s "$ARTIFACTS/map.pgm" ]] || { echo 'map.pgm was not generated'; exit 4; }
bash scripts/evaluate_benchmark.sh "$ARTIFACTS/trajectory.csv" "$ARTIFACTS/map.pgm" "$ARTIFACTS/resource-profile.json"
