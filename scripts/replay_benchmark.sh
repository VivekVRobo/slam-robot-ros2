#!/usr/bin/env bash
set -euo pipefail

BAG=${1:?usage: replay_benchmark.sh BAG_DIR [RATE]}
RATE=${2:-1.0}

# The captured bag includes /clock. Use rosbag2's synthetic --clock source and
# exclude the recorded /clock topic so replay has exactly one clock publisher.
# The topic set is intentionally limited to the channels used by the benchmark.
exec ros2 bag play "$BAG" --topics /scan /cmd_vel /odom /ground_truth/odom /tf /tf_static /map /diagnostics --clock --rate "$RATE"
