#!/usr/bin/env bash
set -euo pipefail

BAG_DIR=${1:?usage: validate_benchmark_replay.sh BAG_DIR RUNTIME_DIR [RATE]}
RUNTIME_DIR=${2:?usage: validate_benchmark_replay.sh BAG_DIR RUNTIME_DIR [RATE]}
RATE=${3:-1.0}
REPLAY_DIR="$RUNTIME_DIR/replay"
REPLAY_CSV="$REPLAY_DIR/trajectory.csv"
REPLAY_MD="$RUNTIME_DIR/replay.md"
RECORDER_PID=''

mkdir -p "$REPLAY_DIR"

fail() {
  local reason=${1:-"replay validation failed"}
  local code=${2:-2}
  cat > "$REPLAY_MD" <<EOF
# Replay validation

- Status: **FAIL**
- Bag: `$BAG_DIR`
- Replay rate: `$RATE`
- Failure: $reason

See `runtime/replay/rosbag-play.log`, `runtime/replay/trajectory-recorder.log`, and `runtime/replay/comparison.log` where available.
EOF
  echo "ERROR: $reason" >&2
  exit "$code"
}

stop_recorder() {
  [[ -z "$RECORDER_PID" ]] && return 0
  if kill -0 "$RECORDER_PID" 2>/dev/null; then
    kill -INT "$RECORDER_PID" 2>/dev/null || true
    for _ in $(seq 1 10); do
      if ! kill -0 "$RECORDER_PID" 2>/dev/null; then
        wait "$RECORDER_PID" 2>/dev/null || true
        RECORDER_PID=''
        return 0
      fi
      sleep 1
    done
    echo "trajectory recorder did not stop after SIGINT; escalating to SIGTERM" >&2
    kill -TERM "$RECORDER_PID" 2>/dev/null || true
  fi
  wait "$RECORDER_PID" 2>/dev/null || true
  RECORDER_PID=''
}

trap stop_recorder EXIT INT TERM

on_error() {
  local code=$?
  cat > "$REPLAY_MD" <<EOF
# Replay validation

- Status: **FAIL**
- Failure: unexpected replay command failure (exit $code)

See `runtime/replay/rosbag-play.log`, `runtime/replay/trajectory-recorder.log`, and `runtime/replay/comparison.log` where available.
EOF
  echo "ERROR: unexpected replay command failure (exit $code)" >&2
  exit "$code"
}
trap on_error ERR

[[ -s "$BAG_DIR/metadata.yaml" ]] || fail "bag metadata is missing: $BAG_DIR/metadata.yaml" 3
shopt -s nullglob
BAG_FILES=("$BAG_DIR"/*.mcap "$BAG_DIR"/*.db3)
BAG_COUNT=$(printf '%s\n' "${BAG_FILES[@]}" | grep -c . || true)
[[ "$BAG_COUNT" -gt 0 ]] || fail "no MCAP or SQLite rosbag file found under $BAG_DIR" 3

cat > "$REPLAY_MD" <<EOF
# Replay validation

- Status: **IN_PROGRESS**
- Bag: `$BAG_DIR`
- Replay rate: `$RATE`
- Command: `bash scripts/replay_benchmark.sh "$BAG_DIR" "$RATE"`
- Clock policy: rosbag2 publishes replay `/clock`; the helper excludes the recorded `/clock` topic to avoid duplicate clock publishers.
EOF

rm -f "$REPLAY_CSV"
ros2 run slam_robot_ros2 trajectory_recorder --ros-args -p use_sim_time:=true -p output_path:="$REPLAY_CSV" -p sample_rate_hz:=10.0 > "$REPLAY_DIR/trajectory-recorder.log" 2>&1 &
RECORDER_PID=$!

ready=false
for _ in $(seq 1 30); do
  if ! kill -0 "$RECORDER_PID" 2>/dev/null; then
    wait "$RECORDER_PID" 2>/dev/null || true
    RECORDER_PID=''
    fail "trajectory recorder exited before becoming ready" 4
  fi
  if ros2 node list 2>/dev/null | grep -q 'trajectory_recorder'; then
    ready=true
    break
  fi
  sleep 1
done
[[ "$ready" == true ]] || fail "trajectory recorder did not become ready within 30 seconds" 4

set +e
bash scripts/replay_benchmark.sh "$BAG_DIR" "$RATE" > "$REPLAY_DIR/rosbag-play.log" 2>&1
PLAY_RC=$?
set -e
[[ "$PLAY_RC" -eq 0 ]] || fail "rosbag playback exited with status $PLAY_RC" 5

# Let the last replayed transform/odometry messages reach the recorder before
# stopping it. Simulated time is controlled by the replayed bag clock.
sleep 2
stop_recorder
trap - EXIT INT TERM

[[ -s "$REPLAY_CSV" ]] || fail "replay did not produce a trajectory CSV" 6
SAMPLE_COUNT=$(awk 'END { print NR - 1 }' "$REPLAY_CSV")
[[ "$SAMPLE_COUNT" =~ ^[0-9]+$ ]] || fail "could not count replay trajectory samples" 6
[[ "$SAMPLE_COUNT" -ge 100 ]] || fail "replay produced only $SAMPLE_COUNT samples; at least 100 are required" 6

python3 tools/trajectory_metrics.py "$REPLAY_CSV" --output "$REPLAY_DIR/trajectory-metrics.json"
python3 tools/loop_closure_metrics.py "$REPLAY_CSV" --output "$REPLAY_DIR/loop-metrics.json"

set +e
python3 tools/compare_replay_metrics.py --original-trajectory "$RUNTIME_DIR/trajectory-metrics.json" --replay-trajectory "$REPLAY_DIR/trajectory-metrics.json" --original-loop "$RUNTIME_DIR/loop-metrics.json" --replay-loop "$REPLAY_DIR/loop-metrics.json" --output "$REPLAY_DIR/comparison.json" > "$REPLAY_DIR/comparison.log" 2>&1
COMPARE_RC=$?
set -e
[[ "$COMPARE_RC" -eq 0 ]] || fail "replayed trajectory/loop metrics did not meet the consistency gate (exit $COMPARE_RC)" 7

cat > "$REPLAY_MD" <<EOF
# Replay validation

- Status: **PASS**
- Bag: `$BAG_DIR`
- Replay rate: `$RATE`
- Command: `bash scripts/replay_benchmark.sh "$BAG_DIR" "$RATE"`
- Playback exit code: `$PLAY_RC`
- Replayed trajectory samples: `$SAMPLE_COUNT`
- Comparison: `runtime/replay/comparison.json` — all configured consistency checks passed.
- Replay artifacts: `runtime/replay/trajectory.csv`, `runtime/replay/trajectory-metrics.json`, and `runtime/replay/loop-metrics.json`.
- Clock policy: rosbag2 publishes replay `/clock`; the helper excludes the recorded `/clock` topic to avoid duplicate clock publishers.

This validates reproducibility of the recorded **simulation** trace within the comparator tolerances. It is not physical-robot validation and does not establish a general performance claim.
EOF

echo "PASS: rosbag replay produced $SAMPLE_COUNT trajectory samples and passed metric consistency checks."
