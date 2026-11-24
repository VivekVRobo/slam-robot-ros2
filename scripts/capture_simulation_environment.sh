#!/usr/bin/env bash
set -euo pipefail

OUTPUT="${1:-artifacts/environment.json}"
SCENARIO="${BENCHMARK_SCENARIO:-unspecified}"
HEADLESS=()

if [[ "${BENCHMARK_HEADLESS:-false}" == "true" ]]; then
  HEADLESS+=(--headless)
fi

python3 tools/capture_simulation_environment.py "$OUTPUT" --scenario "$SCENARIO" "${HEADLESS[@]}"
