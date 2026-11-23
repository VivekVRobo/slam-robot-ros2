#!/usr/bin/env python3
"""Map YAML and grid-coordinate helpers for the SLAM evidence pipeline.

The helpers make the ROS OccupancyGrid convention explicit:
- origin is the world pose of the lower-left corner of cell (0, 0);
- an OccupancyGrid cell center is origin + (col + 0.5, row + 0.5) * resolution;
- a PGM image is stored top-to-bottom, so its pixel row must be vertically
  flipped before applying the OccupancyGrid convention.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


def load_map_metadata(path: Path) -> dict[str, Any]:
    """Load and validate the metadata fields emitted alongside a PGM map."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("map metadata must be a YAML mapping")

    try:
        resolution = float(data["resolution"])
        origin = data["origin"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("map metadata requires numeric resolution and origin") from exc

    if resolution <= 0:
        raise ValueError("map resolution must be positive")
    if not isinstance(origin, (list, tuple)) or len(origin) < 2:
        raise ValueError("map origin must contain at least x and y")

    origin_xy = (float(origin[0]), float(origin[1]))
    return {
        "image": str(data.get("image", "")),
        "resolution": resolution,
        "origin_xy": origin_xy,
        "origin_yaw": float(origin[2]) if len(origin) > 2 else 0.0,
        "negate": int(data.get("negate", 0)),
        "occupied_thresh": float(data.get("occupied_thresh", 0.65)),
        "free_thresh": float(data.get("free_thresh", 0.196)),
    }


def read_pgm_dimensions(path: Path) -> tuple[int, int]:
    """Read the width and height from a binary PGM header without decoding pixels."""
    with path.open("rb") as stream:
        magic = stream.readline().strip()
        if magic != b"P5":
            raise ValueError("expected a binary PGM (P5) image")

        tokens: list[bytes] = []
        while len(tokens) < 3:
            line = stream.readline()
            if not line:
                raise ValueError("incomplete PGM header")
            line = line.split(b"#", 1)[0]
            tokens.extend(line.split())

        try:
            width, height, max_value = (int(token) for token in tokens[:3])
        except ValueError as exc:
            raise ValueError("PGM header contains non-numeric dimensions") from exc

    if width <= 0 or height <= 0:
        raise ValueError("PGM dimensions must be positive")
    if not 0 < max_value <= 65535:
        raise ValueError("PGM max value must be in the range 1..65535")
    return width, height


def occupancy_grid_cell_center(
    row: int, col: int, resolution: float, origin_xy: tuple[float, float]
) -> tuple[float, float]:
    """Return the world center of an OccupancyGrid cell.

    Here row 0 is the ROS grid's bottom row (y increases with row).
    """
    if row < 0 or col < 0:
        raise ValueError("row and col must be non-negative")
    ox, oy = origin_xy
    return (
        ox + (col + 0.5) * resolution,
        oy + (row + 0.5) * resolution,
    )


def pgm_pixel_center_world(
    row: int,
    col: int,
    height: int,
    resolution: float,
    origin_xy: tuple[float, float],
) -> tuple[float, float]:
    """Return world coordinates for a PGM pixel center.

    PGM row 0 is the top row, while the ROS map origin is the lower-left
    corner. The vertical row index is therefore flipped before conversion.
    """
    if row < 0 or col < 0 or row >= height:
        raise ValueError("PGM row is outside image bounds")
    grid_row = height - 1 - row
    return occupancy_grid_cell_center(grid_row, col, resolution, origin_xy)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map_yaml", type=Path)
    parser.add_argument("--check-cell", nargs=2, type=int, metavar=("ROW", "COL"))
    parser.add_argument("--height", type=int)
    args = parser.parse_args()

    metadata = load_map_metadata(args.map_yaml)
    print(yaml.safe_dump(metadata, sort_keys=False).rstrip())

    if args.check_cell is not None:
        if args.height is None:
            parser.error("--height is required with --check-cell")
        row, col = args.check_cell
        print(
            "occupancy_grid_cell_center:",
            occupancy_grid_cell_center(
                row, col, metadata["resolution"], metadata["origin_xy"]
            ),
        )
        print(
            "pgm_pixel_center_world:",
            pgm_pixel_center_world(
                row, col, args.height, metadata["resolution"], metadata["origin_xy"]
            ),
        )


if __name__ == "__main__":
    main()
