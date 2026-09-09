import math

import pytest

from tools.trajectory_metrics import Pose2, align_se2, evaluate


def test_alignment_removes_global_offset():
    gt = [Pose2(0, 0, 0), Pose2(1, 0, 0), Pose2(1, 1, math.pi / 2)]
    est = [
        Pose2(2, 3, 0.4),
        Pose2(2 + math.cos(0.4), 3 + math.sin(0.4), 0.4),
        Pose2(
            2 + math.cos(0.4) - math.sin(0.4),
            3 + math.sin(0.4) + math.cos(0.4),
            0.4 + math.pi / 2,
        ),
    ]
    aligned, _ = align_se2(gt, est)
    assert max(math.hypot(a.x - b.x, a.y - b.y) for a, b in zip(gt, aligned)) < 1e-9


def test_metrics_zero_for_identical_with_real_rpe_pairs():
    rows = [(i * 0.1, Pose2(i * 0.1, 0, 0), Pose2(i * 0.1, 0, 0)) for i in range(30)]
    metrics = evaluate(rows, 5)
    assert metrics["rpe_pairs"] == 25
    assert metrics["ate_rmse_m"] < 1e-12
    assert metrics["rpe_translation_rmse_m"] < 1e-12


def test_rpe_rejects_delta_with_no_valid_pairs():
    rows = [(i * 0.1, Pose2(i * 0.1, 0, 0), Pose2(i * 0.1, 0, 0)) for i in range(5)]
    with pytest.raises(ValueError, match="requires at least 6 trajectory samples"):
        evaluate(rows, 5)


def test_rpe_rejects_non_positive_delta():
    rows = [(i * 0.1, Pose2(i * 0.1, 0, 0), Pose2(i * 0.1, 0, 0)) for i in range(5)]
    with pytest.raises(ValueError, match="positive integer"):
        evaluate(rows, 0)
