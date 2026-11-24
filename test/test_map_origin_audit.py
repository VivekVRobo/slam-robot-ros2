from pathlib import Path

import pytest

from tools.map_origin_audit import cell_center_to_world, load_metadata, world_to_cell


def write_map(path: Path, origin: list[float]) -> None:
    path.write_text(
        "image: map.pgm\n"
        "resolution: 0.5\n"
        f"origin: [{origin[0]}, {origin[1]}, {origin[2]}]\n"
        "negate: 0\n"
        "occupied_thresh: 0.65\n"
        "free_thresh: 0.196\n",
        encoding="utf-8",
    )


def test_origin_is_corner_and_cell_center_is_half_resolution_offset(tmp_path):
    path = tmp_path / "map.yaml"
    write_map(path, [10.0, -2.0, 0.0])

    metadata = load_metadata(path)

    assert metadata["convention"] == "origin_is_lower_left_corner_of_cell_0_0"
    assert cell_center_to_world(metadata, 0, 0) == pytest.approx((10.25, -1.75))
    assert cell_center_to_world(metadata, 2, 3) == pytest.approx((11.25, -0.25))


def test_rotated_origin_is_applied_before_cell_index_conversion(tmp_path):
    path = tmp_path / "map.yaml"
    write_map(path, [1.0, 2.0, 1.5707963267948966])

    metadata = load_metadata(path)

    center = cell_center_to_world(metadata, 0, 0)
    assert center == pytest.approx((0.75, 2.25), abs=1e-9)
    assert world_to_cell(metadata, *center) == (0, 0)


@pytest.mark.parametrize(
    "bad_origin",
    [[0.0], [0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
)
def test_origin_must_have_three_values(tmp_path, bad_origin):
    path = tmp_path / "map.yaml"
    write_map(path, bad_origin)

    with pytest.raises(ValueError, match="exactly \[x, y, yaw\]"):
        load_metadata(path)


def test_missing_resolution_is_rejected(tmp_path):
    path = tmp_path / "map.yaml"
    path.write_text("origin: [0, 0, 0]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="resolution"):
        load_metadata(path)
