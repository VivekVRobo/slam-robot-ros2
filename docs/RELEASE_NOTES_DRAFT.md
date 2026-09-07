# Draft Release Notes — v0.1.0

## v0.1.0 — Reproducible ROS 2 SLAM Engineering Reference

This is the first software-reference release of `slam-robot-ros2`, a reproducibility-first ROS 2 SLAM benchmark stack for a differential-drive robot.

### What this release demonstrates

- ROS 2 Lyrical package build verified in GitHub Actions.
- Gazebo model/world, launch, configuration, URDF/TF and evidence contracts checked in CI.
- 2D LiDAR SLAM architecture with `slam_toolbox` mapping/localization paths.
- Separate Gazebo world-pose ground-truth channel for quantitative trajectory comparison.
- Deterministic benchmark path and trajectory capture tooling.
- ATE/RPE, loop-closure, map and CPU/RSS evaluation utilities.
- Rosbag record/replay workflow.
- One-command simulation evidence campaign with exact-commit and SHA-256 provenance.

### Evidence boundary

This release is a **CI-verified software engineering reference**. It does not claim that the full Gazebo SLAM benchmark has already been executed successfully on the release commit unless a matching archived runtime evidence bundle is attached.

It also does not claim physical-robot validation. Real LiDAR, wheel encoders, measured geometry/extrinsics, physical TF, mapping/localization repeatability and hardware reliability remain separate evidence gates.

### Reference environment

- ROS 2 Lyrical Luth (LTS)
- Gazebo Jetty

### Reproduce the software checks

Follow the README for build/launch commands and `docs/BENCHMARK_EVIDENCE_RUNBOOK.md` for the evidence-producing workflow. The canonical campaign entry point is:

```bash
bash scripts/run_simulation_evidence_campaign.sh
```

### Known pending evidence

- successful end-to-end Gazebo runtime bundle;
- live ground-truth bridge proof;
- published ATE/RPE and loop-closure results;
- resource profile from the same run;
- rosbag replay regression evidence;
- physical LiDAR + encoder validation.

### Release gate

Before publishing the GitHub Release, verify every applicable item in `docs/RELEASE_READINESS.md` against the exact commit selected for the tag.

License: MIT.
