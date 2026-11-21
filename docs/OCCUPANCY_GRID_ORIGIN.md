# OccupancyGrid origin convention

The benchmark pipeline saves maps through nav2_map_server and evaluates
trajectory/map artifacts in world coordinates. The repository treats the
map.yaml origin as the world pose of the **lower-left corner of cell (0, 0)**,
matching the ROS nav_msgs/MapMetaData convention.

For a map with resolution r and origin (ox, oy), the centre of cell
(column, row) is:

(ox + (column + 0.5) * r, oy + (row + 0.5) * r)

This distinction matters when comparing map pixels, occupancy cells and
world-frame trajectory data. A consumer that treats origin as the cell
centre introduces a systematic half-cell translation.

The repository now has a deterministic, ROS-free contract test in
tools/occupancy_grid_origin.py and test/test_occupancy_grid_origin.py.
It validates the conversion convention and the YAML parsing boundary.

This is a coordinate-frame correctness contract, not a claim that the
archived SLAM benchmark has been regenerated. Existing evidence remains
immutable until a new runtime benchmark is actually executed.
