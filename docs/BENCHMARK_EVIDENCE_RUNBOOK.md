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

Capture the machine/runtime metadata as JSON, then create the human-readable companion:

```bash
python tools/capture_environment.py --repo . --output artifacts/environment.json
bash scripts/capture_simulation_environment.sh artifacts/environment.md
```

The JSON helper records a UTC timestamp, OS/kernel details, Python version, `ROS_DISTRO`, the installed `ros2cli` package version, the detected Gazebo CLI/version, Git commit SHA, branch, and working-tree state (`clean`, `dirty`, or `unknown`). If ROS 2 or Gazebo cannot be detected, the relevant JSON value is `null`; the helper does not guess a version. It uses read-only probes and writes only the requested output file (creating its parent directory if needed). It does not launch Gazebo, install packages, change ROS configuration, or certify that a benchmark ran.

The Markdown companion also records CPU/RAM and WSL detection. Review both outputs, then copy them into `evidence/runs/<run-id>/`. Add details that cannot be inferred safely, including rendering mode, benchmark scenario, command line, and non-default parameters.

Required run metadata includes:

- commit SHA and clean/dirty working-tree state
- operating system and kernel
- CPU / RAM
- ROS 2 distribution and available CLI package version
- Gazebo version, if installed
- Python version
- headless vs GUI mode
- whether the run is native Linux, WSL2, or another VM
- benchmark scenario name and command line
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
ros2 launch slam_robot_ros2 simulation_mapping.launch.py \\
  headless:=true \\
  record_trajectory:=true \\
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
├── environment.json
├── environment.md
├── commands.txt
├── manifest.yaml
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

Use [`../evidence/SIMULATION_MANIFEST_TEMPLATE.yaml`](../evidence/SIMULATION_MANIFEST_TEMPLATE.yaml) as the machine-readable provenance template. It deliberately requires `simulation: true` and `physical_hardware: false`.

## 6. Evaluate trajectory quality

```bash
python tools/trajectory_metrics.py artifacts/trajectory.csv \\
  --output artifacts/trajectory-metrics.json

python tools/loop_closure_metrics.py artifacts/trajectory.csv \\
  --output artifacts/loop-metrics.json
```

ATE and RPE should only be compared between runs that use compatible scenarios and evaluation settings.

The full regression gate can be run with:

```bash
bash scripts/evaluate_benchmark.sh
```

## 7. Capture resource profile

```bash
python tools/process_profile.py \\
  --duration 90 \\
  --match slam_toolbox \\
  --match gz \\
  --match ros_gz_bridge \\
  --output artifacts/resource-profile.json
```

Record host hardware and rendering mode because CPU/RSS numbers are environment-dependent.

## 8. Replay validation

```bash
bash scripts/replay_benchmark.sh artifacts/bags/gazebo_loop_square
```

Document whether replay reproduces the expected evaluation path and derived artifacts. A replay failure is evidence and must remain visible.

## 9. Validate the evidence manifest

After filling `manifest.yaml`:

```bash
python tools/simulation_evidence_manifest.py evidence/runs/<run-id>/manifest.yaml
```

When all referenced files have been copied into the run directory, use the stricter check:

```bash
python tools/simulation_evidence_manifest.py \\
  evidence/runs/<run-id>/manifest.yaml \\
  --check-files
```

This validator checks the simulation/hardware claim boundary, Git SHA format, required environment fields, required runtime topics, artifact references, and optional file hashes. Passing the manifest proves **provenance completeness**, not benchmark quality by itself.

## 10. Publish without overstating claims

When a run is complete:

- copy only genuine artifacts into `evidence/runs/<run-id>/`;
- link the run from the README or an evidence index;
- update only the maturity gates directly supported by that run;
- state whether the host was native Linux, WSL2, or another virtualized environment;
- keep physical-robot gates blocked until real LiDAR/encoder data exists.

## Recruiter review path

A reviewer should be able to follow:

`commit -> environment -> launch command -> runtime topics -> rosbag/map/trajectory -> metrics -> replay -> manifest -> limitations`

without needing to trust an unsupported performance claim.
