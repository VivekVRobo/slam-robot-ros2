# Benchmark Evidence Runbook

This runbook defines the exact evidence-producing workflow for the first reproducible Gazebo SLAM benchmark. It is intentionally separate from CI: CI verifies static/build contracts, while this runbook is for runtime evidence.

## Evidence policy

A benchmark is valid only when the repository can trace every reported metric back to:

1. an exact commit SHA;
2. a documented ROS 2 / Gazebo environment;
3. a named benchmark scenario;
4. captured runtime artifacts;
5. the commands used to produce derived metrics.

Do not advance README runtime/hardware maturity gates without archived evidence.

## 1. Record environment

Create `evidence/runs/<run-id>/environment.md` and record:

- commit SHA (`git rev-parse HEAD`)
- operating system and kernel
- CPU / RAM
- ROS 2 distribution
- Gazebo version
- Python version
- headless vs GUI mode
- benchmark scenario name
- any non-default parameters

Suggested run id: `YYYY-MM-DD_gazebo_loop_square_<short-sha>`.

## 2. Build from a clean workspace

```bash
rm -rf build install log
source /opt/ros/lyrical/setup.bash
rosdep install --from-paths . --ignore-src --rosdistro lyrical -r -y
colcon build --packages-select slam_robot_ros2 --symlink-install
source install/setup.bash
```

Archive the build command and any warnings. A failed or partially built workspace is not benchmark evidence.

## 3. Launch the benchmark

```bash
ros2 launch slam_robot_ros2 simulation_mapping.launch.py \
  headless:=true \
  record_trajectory:=true \
  run_benchmark_driver:=true
```

Verify the required graph before trusting the run:

```bash
ros2 topic list
ros2 topic hz /scan
ros2 topic hz /odom
ros2 topic hz /ground_truth/odom
ros2 topic echo /clock --once
ros2 run tf2_ros tf2_echo map base_footprint
```

Required runtime channels:

- `/scan`
- `/odom`
- `/ground_truth/odom`
- `/tf`
- `/tf_static`
- `/map`
- `/clock`

## 4. Record the matching rosbag

```bash
bash scripts/record_benchmark.sh gazebo_loop_square
```

Do not reuse a bag from a different commit or parameter set without documenting that difference.

## 5. Export runtime artifacts

The run directory should contain, at minimum:

```text
evidence/runs/<run-id>/
├── environment.md
├── commands.txt
├── trajectory.csv
├── trajectory-metrics.json
├── loop-metrics.json
├── resource-profile.json
├── map.pgm
├── map.yaml
├── rosbag/
├── replay.md
└── notes.md
```

If an artifact cannot be produced, keep the failed run and explain why in `notes.md`; do not silently omit it.

## 6. Evaluate trajectory quality

```bash
python tools/trajectory_metrics.py artifacts/trajectory.csv \
  --output artifacts/trajectory-metrics.json

python tools/loop_closure_metrics.py artifacts/trajectory.csv \
  --output artifacts/loop-metrics.json
```

ATE and RPE should only be compared between runs that use compatible scenarios and evaluation settings.

## 7. Capture resource profile

```bash
python tools/process_profile.py \
  --duration 90 \
  --match slam_toolbox \
  --match gz \
  --match ros_gz_bridge \
  --output artifacts/resource-profile.json
```

Record host hardware and rendering mode because CPU/RSS numbers are environment-dependent.

## 8. Replay validation

```bash
bash scripts/replay_benchmark.sh artifacts/bags/gazebo_loop_square
```

Document whether replay reproduces the expected evaluation path and derived artifacts. A replay failure is evidence and must remain visible.

## 9. Publish without overstating claims

When a run is complete:

- copy only genuine artifacts into `evidence/runs/<run-id>/`;
- link the run from the README or an evidence index;
- update only the maturity gates directly supported by that run;
- keep physical-robot gates blocked until real LiDAR/encoder data exists.

## Recruiter review path

A reviewer should be able to follow:

`commit -> environment -> launch command -> rosbag/map/trajectory -> metrics -> replay -> limitations`

without needing to trust an unsupported performance claim.
