import math
from pathlib import Path

import pytest

from tools.occupancy_grid_origin import (
    MapOrigin,
    cell_center_world,
    load_map_origin,
    world_to_cell_center,
)


def test_cell_zero_is_half_resolution_from_map_origin():
    origin = MapOrigin(-2.0, 3.0)
    assert cell_center_world(origin, 0.2, 0, 0) == pytest.approx((-1.9, 3.1))


def test_cell_center_round_trip():
    origin = MapOrigin(-1.5, 2.25)
    resolution = 0.5
    for column, row in [(0, 0), (3, 7), (20, 4)]:
        x, y = cell_center_world(origin, resolution, column, row)
        assert world_to_cell_center(origin, resolution, x, y) == (column, row)


def test_rotated_origin_applies_to_cell_center():
    origin = MapOrigin(1.0, 2.0, math.pi / 2)
    assert cell_center_world(origin, 1.0, 0, 0) == pytest.approx((0.5, 2.5))


def test_rotated_origin_round_trip():
    origin = MapOrigin(-1.5, 2.25, math.pi / 2)
    resolution = 0.5
    for column, row in [(0, 0), (3, 7), (20, 4)]:
        x, y = cell_center_world(origin, resolution, column, row)
        assert world_to_cell_center(origin, resolution, x, y) == (column, row)


def test_map_yaml_origin_is_lower_left_corner(tmp_path: Path):
    path = tmp_path / "map.yaml"
    path.write_text(
        "image: map.pgm\nresolution: 0.1\norigin: [-4.0, 2.0, 0.0]\n",
        encoding="utf-8",
    )
    origin, resolution = load_map_origin(path)
    assert origin == MapOrigin(-4.0, 2.0, 0.0)
    assert resolution == pytest.approx(0.1)
    assert cell_center_world(origin, resolution, 0, 0) == pytest.approx((-3.95, 2.05))


def test_invalid_resolution_is_rejected():
    with pytest.raises(ValueError, match="resolution must be positive"):
        cell_center_world(MapOrigin(0.0, 0.0), 0.0, 0, 0)
