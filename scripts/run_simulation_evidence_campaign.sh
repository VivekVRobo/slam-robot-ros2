#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

EXPECTED_ROS_DISTRO=${EXPECTED_ROS_DISTRO:-lyrical}
SCENARIO=${SCENARIO:-gazebo_loop_square}
DURATION=${BENCHMARK_DURATION_S:-52}
ALLOW_DIRTY=${ALLOW_DIRTY_EVIDENCE:-0}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 2
  }
}

for cmd in git python3 ros2 rosdep colcon gz sha256sum; do
  require_cmd "$cmd"
done

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: this evidence campaign must run in Linux (native or WSL2)." >&2
  exit 2
fi

if [[ "${ROS_DISTRO:-unknown}" != "$EXPECTED_ROS_DISTRO" ]]; then
  echo "ERROR: expected ROS_DISTRO=$EXPECTED_ROS_DISTRO, got ${ROS_DISTRO:-unset}." >&2
  echo "Source the correct ROS environment before running this campaign." >&2
  exit 2
fi

if [[ -n "$(git status --porcelain)" && "$ALLOW_DIRTY" != "1" ]]; then
  echo "ERROR: working tree is dirty. Commit/stash changes or set ALLOW_DIRTY_EVIDENCE=1 for a non-publishable exploratory run." >&2
  exit 2
fi

SHA=$(git rev-parse HEAD)
SHORT_SHA=$(git rev-parse --short=8 HEAD)
STAMP=$(date -u +%Y-%m-%dT%H-%M-%SZ)
RUN_ID=${RUN_ID:-${STAMP}_${SCENARIO}_${SHORT_SHA}}
RUN_DIR=${RUN_DIR:-artifacts/evidence/$RUN_ID}
RUNTIME_DIR="$RUN_DIR/runtime"
mkdir -p "$RUNTIME_DIR"

LOG="$RUN_DIR/campaign.log"
exec > >(tee -a "$LOG") 2>&1

printf 'run_id=%s\ncommit=%s\nscenario=%s\n' "$RUN_ID" "$SHA" "$SCENARIO"
printf 'duration_s=%s\nros_distro=%s\n' "$DURATION" "$ROS_DISTRO"

bash scripts/capture_simulation_environment.sh "$RUN_DIR/environment.md"

cat > "$RUN_DIR/commands.txt" <<EOF
rm -rf build install log
rosdep install --from-paths . --ignore-src --rosdistro $ROS_DISTRO -r -y
colcon build --packages-select slam_robot_ros2 --symlink-install
source install/setup.bash
ARTIFACTS_DIR=$RUNTIME_DIR BENCHMARK_DURATION_S=$DURATION bash scripts/run_gazebo_benchmark.sh
EOF

rm -rf build install log
rosdep install --from-paths . --ignore-src --rosdistro "$ROS_DISTRO" -r -y
colcon build --packages-select slam_robot_ros2 --symlink-install
# shellcheck disable=SC1091
source install/setup.bash

ARTIFACTS_DIR="$RUNTIME_DIR" BENCHMARK_DURATION_S="$DURATION" \
  bash scripts/run_gazebo_benchmark.sh

cat > "$RUN_DIR/replay.md" <<'EOF'
# Replay validation

Replay has not been claimed automatically by the capture campaign. Run the documented replay workflow after the benchmark bundle is complete, then replace this note with the exact replay command, observed result, and any differences.

Until that is done, the run is valid runtime capture evidence but not a completed rosbag-regression claim.
EOF

for required in \
  runtime-topics.txt trajectory.csv trajectory-metrics.json loop-metrics.json \
  resource-profile.json map.pgm map.yaml; do
  [[ -s "$RUNTIME_DIR/$required" ]] || {
    echo "ERROR: missing required runtime artifact: $RUNTIME_DIR/$required" >&2
    exit 3
  }
done

for topic in /scan /odom /ground_truth/odom /tf /tf_static /map /clock; do
  grep -qx "$topic" "$RUNTIME_DIR/runtime-topics.txt" || {
    echo "ERROR: live topic snapshot does not contain $topic" >&2
    exit 4
  }
done

OS_NAME=$(grep '^PRETTY_NAME=' /etc/os-release | cut -d= -f2- | tr -d '"')
KERNEL=$(uname -r)
CPU=$(awk -F: '/model name/{gsub(/^ +/,"",$2); print $2; exit}' /proc/cpuinfo)
RAM=$(awk '/MemTotal/{printf "%.1f GiB", $2/1024/1024}' /proc/meminfo)
GAZEBO_VERSION=$(gz sim --versions 2>/dev/null | head -n 1 || gz sim --version 2>/dev/null | head -n 1 || echo unavailable)
MODE=native-linux
if grep -qi microsoft /proc/version 2>/dev/null; then MODE=wsl2; fi
DATE_UTC=$(date -u +%Y-%m-%d)

cat > "$RUN_DIR/manifest.yaml" <<EOF
simulation_run:
  run_id: "$RUN_ID"
  date: "$DATE_UTC"
  commit_sha: "$SHA"
  scenario: "$SCENARIO"
  simulation: true
  physical_hardware: false
  environment:
    os: "$OS_NAME"
    kernel: "$KERNEL"
    cpu: "$CPU"
    ram: "$RAM"
    ros_distro: "$ROS_DISTRO"
    gazebo_version: "$GAZEBO_VERSION"
    mode: "$MODE"
  commands: commands.txt
  topics:
    - /scan
    - /odom
    - /ground_truth/odom
    - /tf
    - /tf_static
    - /map
    - /clock
  artifacts:
    trajectory: runtime/trajectory.csv
    trajectory_metrics: runtime/trajectory-metrics.json
    loop_metrics: runtime/loop-metrics.json
    resource_profile: runtime/resource-profile.json
    map_image: runtime/map.pgm
    map_metadata: runtime/map.yaml
    replay_notes: replay.md
  files:
    - path: runtime/runtime-topics.txt
      sha256: "$(sha256sum "$RUNTIME_DIR/runtime-topics.txt" | awk '{print $1}')"
    - path: runtime/trajectory.csv
      sha256: "$(sha256sum "$RUNTIME_DIR/trajectory.csv" | awk '{print $1}')"
    - path: runtime/trajectory-metrics.json
      sha256: "$(sha256sum "$RUNTIME_DIR/trajectory-metrics.json" | awk '{print $1}')"
    - path: runtime/loop-metrics.json
      sha256: "$(sha256sum "$RUNTIME_DIR/loop-metrics.json" | awk '{print $1}')"
    - path: runtime/resource-profile.json
      sha256: "$(sha256sum "$RUNTIME_DIR/resource-profile.json" | awk '{print $1}')"
    - path: runtime/map.pgm
      sha256: "$(sha256sum "$RUNTIME_DIR/map.pgm" | awk '{print $1}')"
    - path: runtime/map.yaml
      sha256: "$(sha256sum "$RUNTIME_DIR/map.yaml" | awk '{print $1}')"
EOF

python3 tools/simulation_evidence_manifest.py "$RUN_DIR/manifest.yaml" --check-files

cat > "$RUN_DIR/README.md" <<EOF
# Gazebo evidence run: $RUN_ID

- Commit: \`$SHA\`
- Scenario: \`$SCENARIO\`
- ROS: \`$ROS_DISTRO\`
- Environment mode: \`$MODE\`
- Runtime duration: \`${DURATION}s\`
- Physical hardware evidence: **no**

This directory was generated by \`scripts/run_simulation_evidence_campaign.sh\`.
The live ROS topic snapshot, manifest, and SHA-256 hashes establish provenance for the captured simulation artifacts.
Rosbag replay remains a separate evidence gate until \`replay.md\` records a completed replay.
EOF

printf '\nPASS: simulation evidence bundle created at %s\n' "$RUN_DIR"
printf 'Next gate: perform rosbag replay and replace replay.md with the observed result.\n'
