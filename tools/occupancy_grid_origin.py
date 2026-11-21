"""Explicit ROS OccupancyGrid map-origin and cell-centre conversions.

ROS nav_msgs/MapMetaData.origin is the world pose of the lower-left
corner of cell (0, 0). Cell centres therefore add half a resolution in
both axes. This module keeps that convention explicit and testable without
requiring a running ROS graph.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import yaml


@dataclass(frozen=True)
class MapOrigin:
    x: float
    y: float
    yaw: float = 0.0


def cell_center_world(origin: MapOrigin, resolution: float, column: int, row: int) -> tuple[float, float]:
    """Return the world position of an occupancy-grid cell centre."""
    if resolution <= 0:
        raise ValueError("resolution must be positive")
    if column < 0 or row < 0:
        raise ValueError("column and row must be non-negative")
    return (
        origin.x + (column + 0.5) * resolution,
        origin.y + (row + 0.5) * resolution,
    )


def world_to_cell_center(
    origin: MapOrigin,
    resolution: float,
    x: float,
    y: float,
) -> tuple[int, int]:
    """Return the cell whose centre contains a world point."""
    if resolution <= 0:
        raise ValueError("resolution must be positive")
    return (
        int((x - origin.x) // resolution),
        int((y - origin.y) // resolution),
    )


def load_map_origin(path: Path) -> tuple[MapOrigin, float]:
    """Load a map YAML and return its declared origin and resolution."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    origin: Sequence[float] = data["origin"]
    if len(origin) < 2:
        raise ValueError("map origin must contain at least x and y")
    resolution = float(data["resolution"])
    return MapOrigin(float(origin[0]), float(origin[1]), float(origin[2]) if len(origin) > 2 else 0.0), resolution
