from tools.trajectory_metrics import Pose2
from tools.loop_closure_metrics import evaluate


def test_detects_return_loop():
    pts = []
    xy = [
        (0, 0),
        (1, 0),
        (2, 0),
        (2, 1),
        (2, 2),
        (1, 2),
        (0, 2),
        (0, 1),
        (0, 0),
    ]
    k = 0
    for a, b in zip(xy, xy[1:]):
        for j in range(10):
            t = j / 10
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            p = Pose2(x, y, 0)
            pts.append((k * 0.1, p, p))
            k += 1
    pts.append((k * 0.1, Pose2(0, 0, 0), Pose2(0, 0, 0)))

    metrics = evaluate(pts, radius=.15, min_path=4, min_gap_samples=30)

    assert metrics["loop_events"] >= 1


def test_reports_closest_revisit_when_no_loop_is_detected():
    pts = []
    for i in range(80):
        p = Pose2(i * 0.1, 0, 0)
        pts.append((i * 0.1, p, p))

    metrics = evaluate(pts, radius=.30, min_path=3, min_gap_samples=20)

    assert metrics["loop_events"] == 0
    assert metrics["path_length_m"] == 7.9
    candidate = metrics["revisit_search"]["closest_candidate"]
    assert candidate is not None
    assert candidate["within_radius"] is False
    assert candidate["gt_revisit_distance_m"] > 0.30
