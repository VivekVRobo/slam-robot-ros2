import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.compare_replay_metrics import compare


def trajectory(samples=485, duration=48.7, ate=0.02235, rpe_t=0.02458, rpe_y=0.03796):
    return {
        "samples": samples,
        "duration_s": duration,
        "ate_rmse_m": ate,
        "rpe_translation_rmse_m": rpe_t,
        "rpe_yaw_rmse_rad": rpe_y,
    }


def loop_metrics(events=5, trans=0.02526, yaw=0.00298):
    return {
        "loop_events": events,
        "max_relative_translation_error_m": trans,
        "max_relative_yaw_error_rad": yaw,
    }


def test_identical_original_and_replay_pass():
    result = compare(trajectory(), trajectory(), loop_metrics(), loop_metrics())
    assert result["passed"] is True
    assert all(result["checks"].values())


def test_metric_drift_fails_closed():
    result = compare(trajectory(), trajectory(ate=0.2), loop_metrics(), loop_metrics())
    assert result["passed"] is False
    assert result["checks"]["ate_rmse_m_is_consistent"] is False


def test_insufficient_replay_samples_fail():
    result = compare(trajectory(), trajectory(samples=200), loop_metrics(), loop_metrics())
    assert result["passed"] is False
    assert result["checks"]["replay_has_sufficient_samples"] is False


def test_missing_loop_revisits_fail():
    result = compare(trajectory(), trajectory(), loop_metrics(events=0), loop_metrics(events=0))
    assert result["passed"] is False
    assert result["checks"]["both_runs_detect_loop_events"] is False
    assert result["checks"]["max_relative_translation_error_m_is_consistent"] is False


def test_non_finite_metric_is_rejected():
    original = trajectory(ate=math.nan)
    with pytest.raises(ValueError, match="finite number"):
        compare(original, trajectory(), loop_metrics(), loop_metrics())


def test_boolean_sample_count_is_rejected():
    original = trajectory()
    original["samples"] = True
    with pytest.raises(ValueError, match="positive integer"):
        compare(original, trajectory(), loop_metrics(), loop_metrics())
