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
- PGM header dimension validation without decoding image pixels;
- explicit ROS OccupancyGrid cell-center conversion;
- explicit PGM-to-world conversion with the vertical flip;
- deterministic unit tests for the two coordinate conventions and PGM dimensions.

The current benchmark's trajectory ATE/RPE tools operate on /ground_truth/odom and
the SLAM trajectory and do not consume map pixels. Therefore this change does not
claim a change in existing ATE/RPE numbers.

## Verified benchmark artifact

The first live artifact produced from PR #20's head
`519863ee248a9800538a137723f700165706845a` confirms the producer-side values:

- PGM dimensions: 158 x 159 pixels;
- resolution: 0.05 m/pixel;
- origin: [-0.563, -1.187, 0];
- map known ratio: 1.0.

The CI log also records that nav2_map_server received a 158 x 159 map at 0.05 m/pixel
and successfully wrote both map.pgm and map.yaml. The generated artifact was inspected
directly rather than inferred from the source code.

This confirms the expected map metadata shape for this benchmark run. It does not
by itself prove that every future producer/consumer path uses the same convention.

## Evidence boundary

The benchmark run was simulation evidence only. On this PR head, the map was saved
successfully and the ATE/RPE checks passed, but the overall benchmark gate failed
because the loop-event requirement was not met (0 loop events). No benchmark
threshold was changed and no physical-hardware result is claimed.

The audit therefore establishes the coordinate contract and verifies one real
generated map artifact without claiming improved SLAM accuracy.
