# Release Readiness — v0.1.0

This checklist defines when `slam-robot-ros2` may be tagged as a **software engineering reference release**. It deliberately separates release readiness from unverified Gazebo runtime or physical-robot claims.

## Allowed release statement

> **v0.1.0 — CI-verified ROS 2 SLAM engineering reference with reproducible Gazebo benchmark tooling. Runtime benchmark evidence and physical-robot validation remain explicitly gated.**

A tag created under this checklist must not imply that Gazebo, SLAM accuracy, rosbag replay, or physical hardware has been validated unless matching evidence is present in the tagged commit.

## Required gates

### Source and CI

- [ ] Tag points to a clean `main` commit.
- [ ] Engineering CI is green on the exact tag commit.
- [ ] ROS 2 Lyrical package build passes on the exact commit.
- [ ] Static simulation/world/launch/TF contracts pass.
- [ ] No generated build artifacts, local bags, or machine-specific scratch files are committed accidentally.

### Reproducibility

- [ ] `README.md` quick-start commands match the tagged code.
- [ ] `docs/BENCHMARK_EVIDENCE_RUNBOOK.md` matches the current launch and tooling interfaces.
- [ ] `scripts/run_simulation_evidence_campaign.sh` remains the canonical evidence-producing path.
- [ ] Evidence manifests preserve exact commit SHA and SHA-256 artifact provenance.
- [ ] Benchmark thresholds remain labeled as regression targets rather than hardware specifications.

### Claim boundaries

- [ ] README evidence-maturity table matches actual evidence in the tag.
- [ ] No Gazebo runtime gate is marked complete without an archived real run bundle.
- [ ] No ATE/RPE, loop-closure, resource, or rosbag result is claimed without the corresponding captured artifact.
- [ ] No physical LiDAR/encoder, TF, mapping, localization, accuracy, repeatability, or reliability claim appears without physical evidence.
- [ ] Simulation and physical-robot language remain clearly separated.

### Release package

- [ ] Release notes state the supported reference environment: ROS 2 Lyrical + Gazebo Jetty.
- [ ] Release notes list known limitations and evidence gates still open.
- [ ] MIT license is present.
- [ ] Installation/build/run commands have been reviewed against the tagged tree.
- [ ] Open issues that represent missing evidence are linked rather than described as completed work.

## Runtime-evidence upgrade gate

The release may later be amended or followed by an evidence release only after a genuine campaign produces, at minimum:

- environment and exact commit record;
- live required-topic verification;
- map artifact;
- `trajectory.csv`;
- ATE/RPE output;
- loop-closure metrics;
- resource profile;
- rosbag + replay notes;
- SHA-256 manifest;
- limitations/failures observed during the run.

Only then may the release notes state that the documented Gazebo benchmark was executed successfully.

## Physical-hardware upgrade gate

Physical maturity remains blocked until the repository contains real LiDAR + encoder evidence, measured robot geometry/extrinsics, real TF/topic captures, real rosbags, repeatability runs, and documented failure cases. A software release does not waive this requirement.

## Recommended first release title

`v0.1.0 — Reproducible ROS 2 SLAM Engineering Reference`

## Recruiter review path

For a fast technical review, inspect in this order:

1. `README.md` — architecture and maturity boundary;
2. `docs/BENCHMARK_EVIDENCE_RUNBOOK.md` — reproducibility protocol;
3. `scripts/run_simulation_evidence_campaign.sh` — one-command evidence workflow;
4. trajectory/loop/resource tooling under `tools/`;
5. `.github/workflows/checks.yml` — automated verification;
6. this release checklist — exact boundary between demonstrated and pending evidence.
