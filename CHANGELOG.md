# Changelog
## 0.4.0 - 2026-08-30
- Added physical LiDAR/encoder hardware profile with explicit unmeasured placeholders.
- Added physical ROS graph/TF/rate/timestamp audit and one-command rosbag evidence capture.
- Added wheel-radius and wheel-separation calibration tooling based on externally measured truth.
- Added LiDAR extrinsic-verification workflow and hardware evidence manifests with optional SHA-256 checks.
- Added hardware-data-ready and hardware-calibrated maturity stages before mapping/localization claims.
- Added CI checks proving the template cannot pass measured-hardware gates without evidence.

## 0.3.0 - 2026-08-18
- Added Gazebo Jetty physics benchmark world and differential-drive LiDAR model.
- Added separate simulator ground-truth odometry bridge.
- Added deterministic benchmark driver and trajectory recorder.
- Added SE(2)-aligned ATE/RPE, loop-closure metrics, benchmark gates, rosbag scripts and process profiling.
- Added simulation/trajectory/loop/resource/hardware evidence documentation.
- Expanded evidence-based maturity gates so simulation cannot be mistaken for physical validation.
