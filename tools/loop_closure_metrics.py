#!/usr/bin/env python3
"""Detect ground-truth loop revisits and score long-horizon relative-pose error."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

try:
    from tools.trajectory_metrics import load, relative, wrap
except ModuleNotFoundError:
    from trajectory_metrics import load, relative, wrap


def cumulative(gt):
    out = [0.0]
    for a, b in zip(gt, gt[1:]):
        out.append(out[-1] + math.hypot(b.x - a.x, b.y - a.y))
    return out


def detect(rows, radius=.30, min_path=3.0, min_gap_samples=50):
    gt = [r[1] for r in rows]
    est = [r[2] for r in rows]
    dist = cumulative(gt)
    events = []
    last_j = -min_gap_samples

    for j in range(min_gap_samples, len(rows)):
        best = None
        for i in range(0, j - min_gap_samples):
            path_length = dist[j] - dist[i]
            if path_length < min_path:
                continue
            d = math.hypot(gt[j].x - gt[i].x, gt[j].y - gt[i].y)
            if d <= radius and (best is None or d < best[0]):
                best = (d, i)
        if best and j - last_j >= min_gap_samples:
            _, i = best
            err = relative(
                relative(gt[i], gt[j]),
                relative(est[i], est[j]),
            )
            events.append(
                {
                    "start_index": i,
                    "end_index": j,
                    "path_length_m": dist[j] - dist[i],
                    "gt_revisit_distance_m": best[0],
                    "relative_translation_error_m": math.hypot(err.x, err.y),
                    "relative_yaw_error_rad": abs(wrap(err.yaw)),
                }
            )
            last_j = j

    return events


def closest_revisit(rows, radius=.30, min_path=3.0, min_gap_samples=50):
    """Return the closest eligible revisit candidate, even when it is outside radius."""
    gt = [r[1] for r in rows]
    dist = cumulative(gt)
    best = None

    for j in range(min_gap_samples, len(rows)):
        for i in range(0, j - min_gap_samples):
            path_length = dist[j] - dist[i]
            if path_length < min_path:
                continue
            distance = math.hypot(gt[j].x - gt[i].x, gt[j].y - gt[i].y)
            if best is None or distance < best["gt_revisit_distance_m"]:
                best = {
                    "start_index": i,
                    "end_index": j,
                    "path_length_m": path_length,
                    "gt_revisit_distance_m": distance,
                    "within_radius": distance <= radius,
                }

    return best


def evaluate(rows, **kw):
    e = detect(rows, **kw)
    diagnostics = {
        "path_length_m": cumulative([r[1] for r in rows])[-1],
        "revisit_search": {
            "radius_m": kw.get("radius", .30),
            "min_path_m": kw.get("min_path", 3.0),
            "min_gap_samples": kw.get("min_gap_samples", 50),
            "closest_candidate": closest_revisit(rows, **kw),
        },
    }

    if not e:
        return {
            "loop_events": 0,
            "mean_relative_translation_error_m": None,
            "mean_relative_yaw_error_rad": None,
            "events": [],
            **diagnostics,
        }

    return {
        "loop_events": len(e),
        "mean_relative_translation_error_m": sum(
            x["relative_translation_error_m"] for x in e
        ) / len(e),
        "max_relative_translation_error_m": max(
            x["relative_translation_error_m"] for x in e
        ),
        "mean_relative_yaw_error_rad": sum(
            x["relative_yaw_error_rad"] for x in e
        ) / len(e),
        "max_relative_yaw_error_rad": max(
            x["relative_yaw_error_rad"] for x in e
        ),
        "events": e,
        **diagnostics,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--radius", type=float, default=.30)
    p.add_argument("--min-path", type=float, default=3.0)
    p.add_argument("--min-gap-samples", type=int, default=50)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    m = evaluate(
        load(a.csv),
        radius=a.radius,
        min_path=a.min_path,
        min_gap_samples=a.min_gap_samples,
    )
    text = json.dumps(m, indent=2)
    print(text)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
