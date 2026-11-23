# OccupancyGrid origin convention

The Gazebo benchmark saves the live /map with nav2_map_server map_saver_cli and
archives the resulting map.pgm and map.yaml. The benchmark currently does not
transform map coordinates during ATE/RPE evaluation, so this document makes the
map-coordinate contract explicit rather than implying that the image and ROS grid
share the same row origin.

## Coordinate contract

For a ROS nav_msgs/msg/OccupancyGrid, info.origin is the pose of the lower-left
corner of cell (0, 0). With resolution r and origin (ox, oy), the center of grid
cell (row, col) is:

x = ox + (col + 0.5) * r
y = oy + (row + 0.5) * r

The archived PGM is an image, so its row zero is the top row. When converting a
PGM pixel (row, col) to the ROS grid convention, use:

grid_row = height - 1 - row

before applying the cell-center formula.

This distinction matters when a future map-quality metric converts PGM pixels back
to world coordinates. Treating PGM row zero as ROS grid row zero introduces a vertical
translation of approximately (height - 1) * resolution.

## Repository implementation

tools/map_origin.py provides:

- YAML metadata parsing with validation;
- explicit ROS OccupancyGrid cell-center conversion;
- explicit PGM-to-world conversion with the vertical flip;
- deterministic unit tests for the two coordinate conventions.

The current benchmark's trajectory ATE/RPE tools operate on /ground_truth/odom and
the SLAM trajectory and do not consume map pixels. Therefore this change does not
claim a change in existing ATE/RPE numbers.

## Evidence boundary

The repository still requires a real benchmark run to verify the exact map.yaml
values produced by the current runtime. This audit establishes the coordinate
contract and testable conversion semantics; it does not fabricate a captured map
or claim a new benchmark result.
