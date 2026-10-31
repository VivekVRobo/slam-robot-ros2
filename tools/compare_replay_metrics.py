#!/usr/bin/env python3
"""Compare a rosbag-replayed SLAM trace with its original simulation trace.

This is a simulation replay consistency gate, not a physical-robot or
performance claim. Thresholds are deliberately explicit and configurable.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON object from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _finite_number(data: dict[str, Any], key: str, label: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label}.{key} must be a finite number")
    return float(value)


def _positive_int(data: dict[str, Any], key: str, label: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label}.{key} must be a positive integer")
    return value


def _non_negative_int(data: dict[str, Any], key: str, label: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label}.{key} must be a non-negative integer")
    return value


def compare(
    original_trajectory: dict[str, Any],
    replay_trajectory: dict[str, Any],
    original_loop: dict[str, Any],
    replay_loop: dict[str, Any],
    *,
    min_sample_ratio: float = 0.70,
    max_duration_delta_s: float = 5.0,
    max_ate_delta_m: float = 0.03,
    max_rpe_translation_delta_m: float = 0.04,
    max_rpe_yaw_delta_rad: float = 0.05,
    max_loop_translation_delta_m: float = 0.05,
    max_loop_yaw_delta_rad: float = 0.05,
    max_loop_event_delta: int = 2,
) -> dict[str, Any]:
    if not 0.0 < min_sample_ratio <= 1.0:
        raise ValueError("min_sample_ratio must be in (0, 1]")
    tolerances = {
        "min_sample_ratio": min_sample_ratio,
        "max_duration_delta_s": max_duration_delta_s,
        "max_ate_delta_m": max_ate_delta_m,
        "max_rpe_translation_delta_m": max_rpe_translation_delta_m,
        "max_rpe_yaw_delta_rad": max_rpe_yaw_delta_rad,
        "max_loop_translation_delta_m": max_loop_translation_delta_m,
        "max_loop_yaw_delta_rad": max_loop_yaw_delta_rad,
        "max_loop_event_delta": max_loop_event_delta,
    }
    original_samples = _positive_int(original_trajectory, "samples", "original_trajectory")
    replay_samples = _positive_int(replay_trajectory, "samples", "replay_trajectory")
    original_duration = _finite_number(original_trajectory, "duration_s", "original_trajectory")
    replay_duration = _finite_number(replay_trajectory, "duration_s", "replay_trajectory")

    metric_fields = {
        "ate_rmse_m": "max_ate_delta_m",
        "rpe_translation_rmse_m": "max_rpe_translation_delta_m",
        "rpe_yaw_rmse_rad": "max_rpe_yaw_delta_rad",
    }
    deltas: dict[str, float | int | None] = {
        "sample_ratio": replay_samples / original_samples,
        "duration_delta_s": abs(replay_duration - original_duration),
    }
    checks: dict[str, bool] = {
        "replay_has_sufficient_samples": replay_samples / original_samples >= min_sample_ratio,
        "duration_is_consistent": abs(replay_duration - original_duration) <= max_duration_delta_s,
    }
    for field, tolerance_key in metric_fields.items():
        original_value = _finite_number(original_trajectory, field, "original_trajectory")
        replay_value = _finite_number(replay_trajectory, field, "replay_trajectory")
        delta = abs(replay_value - original_value)
        deltas[f"{field}_delta"] = delta
        checks[f"{field}_is_consistent"] = delta <= tolerances[tolerance_key]

    original_events = _non_negative_int(original_loop, "loop_events", "original_loop")
    replay_events = _non_negative_int(replay_loop, "loop_events", "replay_loop")
    event_delta = abs(replay_events - original_events)
    deltas["loop_event_count_delta"] = event_delta
    checks["both_runs_detect_loop_events"] = original_events > 0 and replay_events > 0
    checks["loop_event_count_is_consistent"] = event_delta <= max_loop_event_delta

    loop_fields = {
        "max_relative_translation_error_m": "max_loop_translation_delta_m",
        "max_relative_yaw_error_rad": "max_loop_yaw_delta_rad",
    }
    if original_events > 0 and replay_events > 0:
        for field, tolerance_key in loop_fields.items():
            original_value = _finite_number(original_loop, field, "original_loop")
            replay_value = _finite_number(replay_loop, field, "replay_loop")
            delta = abs(replay_value - original_value)
            deltas[f"{field}_delta"] = delta
            checks[f"{field}_is_consistent"] = delta <= tolerances[tolerance_key]
    else:
        for field in loop_fields:
            deltas[f"{field}_delta"] = None
            checks[f"{field}_is_consistent"] = False

    return {
        "schema_version": 1,
        "scope": "simulation-only rosbag replay consistency; not physical-hardware validation or a performance claim",
        "passed": all(checks.values()),
        "tolerances": tolerances,
        "deltas": deltas,
        "checks": checks,
        "original": {
            "samples": original_samples,
            "duration_s": original_duration,
            "loop_events": original_events,
        },
        "replay": {
            "samples": replay_samples,
            "duration_s": replay_duration,
            "loop_events": replay_events,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-trajectory", required=True, type=Path)
    parser.add_argument("--replay-trajectory", required=True, type=Path)
    parser.add_argument("--original-loop", required=True, type=Path)
    parser.add_argument("--replay-loop", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = compare(
            _load_object(args.original_trajectory),
            _load_object(args.replay_trajectory),
            _load_object(args.original_loop),
            _load_object(args.replay_loop),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
