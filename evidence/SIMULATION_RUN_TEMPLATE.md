# Gazebo SLAM Simulation Evidence Run

> Copy this file into `evidence/runs/<run-id>/README.md` for a real run. Do not fill measured values from dry runs, CI smoke tests, or estimates.

## Run identity

- Run ID:
- Date/time + timezone:
- Operator:
- Git commit SHA:
- Working tree clean: yes / no
- Scenario:
- Headless: true / false

## Environment

- OS / version:
- Kernel:
- CPU:
- RAM:
- ROS 2 distribution/version:
- Gazebo version:
- Python version:
- `slam_toolbox` version/source:
- `ros_gz` version/source:

## Build

```text
<exact commands>
```

Build result: PASS / FAIL

Warnings or deviations:

## Launch

```text
<exact launch command>
```

Runtime graph checks:

| Contract | Result | Evidence / note |
|---|---|---|
| `/scan` publishing | | |
| `/odom` publishing | | |
| `/ground_truth/odom` publishing | | |
| `/clock` publishing | | |
| `/map` publishing | | |
| `map -> base_footprint` available | | |
| TF ownership matches design | | |

## Artifacts

| Artifact | Path / external location | SHA256 / identifier | Present |
|---|---|---|---|
| trajectory CSV | | | |
| trajectory metrics | | | |
| loop metrics | | | |
| map PGM | | | |
| map YAML | | | |
| resource profile | | | |
| rosbag | | | |
| replay notes | | | |
| logs | | | |

Large rosbags may live outside Git; record a stable location and hash instead of committing them blindly.

## Metrics

Record only values generated from the archived artifacts.

| Metric | Value | Units / definition |
|---|---:|---|
| ATE RMSE | | |
| RPE translation RMSE | | |
| RPE rotation RMSE | | |
| Loop revisit error | | |
| Peak RSS | | |
| Process CPU / summary | | |

## Replay

Replay command:

```text
<exact command>
```

Replay result: PASS / FAIL / PARTIAL

Differences from live run:

## Failures and limitations

List every material warning, dropped topic, parameter change, restart, excluded sample, timing issue, or environment-specific limitation.

## Claim decision

- [ ] Gazebo runtime demonstrated by this run
- [ ] Ground-truth bridge demonstrated by this run
- [ ] SLAM benchmark demonstrated by this run
- [ ] ATE/RPE metrics supported by archived trajectory
- [ ] Loop-closure metric supported by archived trajectory
- [ ] Resource profile supported by recorded host/run metadata
- [ ] Rosbag replay path demonstrated

Physical robot claims remain **out of scope** for this simulation run.

## Recruiter review path

`commit -> environment -> build -> launch -> graph/TF -> raw artifacts -> metrics -> replay -> failures -> constrained claims`
