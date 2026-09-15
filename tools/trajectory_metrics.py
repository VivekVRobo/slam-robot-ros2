#!/usr/bin/env python3
"""Compute SE(2)-aligned ATE and fixed-delta RPE from benchmark trajectory CSV."""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Pose2:
    x: float
    y: float
    yaw: float


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def compose(a, b):
    c, s = math.cos(a.yaw), math.sin(a.yaw)
    return Pose2(
        a.x + c * b.x - s * b.y,
        a.y + s * b.x + c * b.y,
        wrap(a.yaw + b.yaw),
    )


def inverse(a):
    c, s = math.cos(a.yaw), math.sin(a.yaw)
    return Pose2(-c * a.x - s * a.y, s * a.x - c * a.y, wrap(-a.yaw))


def relative(a, b):
    return compose(inverse(a), b)


def load(path):
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                (
                    float(r["stamp_s"]),
                    Pose2(float(r["gt_x"]), float(r["gt_y"]), float(r["gt_yaw"])),
                    Pose2(float(r["est_x"]), float(r["est_y"]), float(r["est_yaw"])),
                )
            )
    if len(rows) < 2:
        raise ValueError("at least two samples required")
    return rows


def align_se2(gt, est):
    gx = sum(p.x for p in gt) / len(gt)
    gy = sum(p.y for p in gt) / len(gt)
    ex = sum(p.x for p in est) / len(est)
    ey = sum(p.y for p in est) / len(est)
    cross = dot = 0.0
    for g, e in zip(gt, est):
        gxc, gyc = g.x - gx, g.y - gy
        exc, eyc = e.x - ex, e.y - ey
        dot += exc * gxc + eyc * gyc
        cross += exc * gyc - eyc * gxc
    th = math.atan2(cross, dot)
    c, s = math.cos(th), math.sin(th)
    tx = gx - (c * ex - s * ey)
    ty = gy - (s * ex + c * ey)
    return (
        [
            Pose2(c * p.x - s * p.y + tx, s * p.x + c * p.y + ty, wrap(p.yaw + th))
            for p in est
        ],
        {"yaw_rad": th, "tx_m": tx, "ty_m": ty},
    )


def rms(values):
    if not values:
        raise ValueError("RMS requires at least one value")
    return math.sqrt(sum(x * x for x in values) / len(values))


def evaluate(rows, delta=10):
    if not isinstance(delta, int) or delta <= 0:
        raise ValueError("RPE delta must be a positive integer")
    if len(rows) <= delta:
        raise ValueError(
            f"RPE delta {delta} requires at least {delta + 1} trajectory samples; "
            f"got {len(rows)}"
        )

    gt = [r[1] for r in rows]
    est = [r[2] for r in rows]
    aligned, transform = align_se2(gt, est)

    ate = [math.hypot(g.x - e.x, g.y - e.y) for g, e in zip(gt, aligned)]
    yaw_error = [abs(wrap(g.yaw - e.yaw)) for g, e in zip(gt, aligned)]
    rpe_translation = []
    rpe_yaw = []

    for i in range(len(rows) - delta):
        err = relative(
            relative(gt[i], gt[i + delta]),
            relative(aligned[i], aligned[i + delta]),
        )
        rpe_translation.append(math.hypot(err.x, err.y))
        rpe_yaw.append(abs(err.yaw))

    return {
        "samples": len(rows),
        "duration_s": rows[-1][0] - rows[0][0],
        "alignment_se2": transform,
        "ate_rmse_m": rms(ate),
        "ate_mean_m": sum(ate) / len(ate),
        "ate_max_m": max(ate),
        "yaw_rmse_rad": rms(yaw_error),
        "rpe_delta_samples": delta,
        "rpe_pairs": len(rpe_translation),
        "rpe_translation_rmse_m": rms(rpe_translation),
        "rpe_translation_max_m": max(rpe_translation),
        "rpe_yaw_rmse_rad": rms(rpe_yaw),
        "rpe_yaw_max_rad": max(rpe_yaw),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--delta", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    metrics = evaluate(load(args.csv), args.delta)
    text = json.dumps(metrics, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
