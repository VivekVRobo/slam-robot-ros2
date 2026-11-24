#!/usr/bin/env python3
"""Audit ROS OccupancyGrid map metadata and expose the cell/world convention."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import yaml


def load_metadata(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("map metadata must be a YAML mapping")

    missing = [key for key in ("resolution", "origin") if key not in data]
    if missing:
        raise ValueError(f"map metadata missing required field(s): {', '.join(missing)}")

    resolution = float(data["resolution"])
    origin = data["origin"]
    if resolution <= 0 or not math.isfinite(resolution):
        raise ValueError("resolution must be a positive finite number")
    if not isinstance(origin, list) or len(origin) != 3:
        raise ValueError("origin must contain exactly [x, y, yaw]")

    values = [float(value) for value in origin]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("origin values must be finite")

    return {
        "image": data.get("image"),
        "resolution_m_per_cell": resolution,
        "origin": {"x_m": values[0], "y_m": values[1], "yaw_rad": values[2]},
        "convention": "origin_is_lower_left_corner_of_cell_0_0",
        "source_standard": "nav_msgs/MapMetaData.origin",
        "occupancy_thresholds": {
            "negate": data.get("negate"),
            "occupied_thresh": data.get("occupied_thresh"),
            "free_thresh": data.get("free_thresh"),
        },
    }


def cell_center_to_world(metadata: dict, column: int, row: int) -> tuple[float, float]:
    if column < 0 or row < 0:
        raise ValueError("cell indices must be non-negative")

    resolution = metadata["resolution_m_per_cell"]
    origin = metadata["origin"]
    local_x = (column + 0.5) * resolution
    local_y = (row + 0.5) * resolution
    c = math.cos(origin["yaw_rad"])
    s = math.sin(origin["yaw_rad"])
    return (
        origin["x_m"] + c * local_x - s * local_y,
        origin["y_m"] + s * local_x + c * local_y,
    )


def world_to_cell(metadata: dict, x: float, y: float) -> tuple[int, int]:
    origin = metadata["origin"]
    dx = float(x) - origin["x_m"]
    dy = float(y) - origin["y_m"]
    c = math.cos(origin["yaw_rad"])
    s = math.sin(origin["yaw_rad"])
    local_x = c * dx + s * dy
    local_y = -s * dx + c * dy
    resolution = metadata["resolution_m_per_cell"]
    return math.floor(local_x / resolution), math.floor(local_y / resolution)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("map_yaml", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    metadata = load_metadata(args.map_yaml)
    metadata["cell_0_0_center_world"] = {
        "x_m": cell_center_to_world(metadata, 0, 0)[0],
        "y_m": cell_center_to_world(metadata, 0, 0)[1],
    }
    text = json.dumps(metadata, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
