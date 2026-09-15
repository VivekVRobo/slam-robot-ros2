#!/usr/bin/env bash
set -euo pipefail
TRAJ=${1:-artifacts/trajectory.csv}
MAP=${2:-artifacts/map.pgm}
RESOURCE=${3:-artifacts/resource-profile.json}
OUTPUT_DIR=${ARTIFACTS_DIR:-$(dirname "$TRAJ")}
mkdir -p "$OUTPUT_DIR"
python3 tools/trajectory_metrics.py "$TRAJ" --output "$OUTPUT_DIR/trajectory-metrics.json"
python3 tools/loop_closure_metrics.py "$TRAJ" --output "$OUTPUT_DIR/loop-metrics.json"
if [[ -f "$MAP" ]]; then python3 tools/map_metrics.py "$MAP" --output "$OUTPUT_DIR/map-metrics.json"; fi
ARGS=(--trajectory "$OUTPUT_DIR/trajectory-metrics.json" --loop "$OUTPUT_DIR/loop-metrics.json" --output "$OUTPUT_DIR/benchmark-gate.json")
[[ -f "$OUTPUT_DIR/map-metrics.json" ]] && ARGS+=(--map "$OUTPUT_DIR/map-metrics.json")
[[ -f "$RESOURCE" ]] && ARGS+=(--resource "$RESOURCE")
python3 tools/benchmark_gate.py "${ARGS[@]}"
