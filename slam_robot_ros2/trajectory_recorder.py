"""Record synchronized ground-truth and SLAM-estimated planar trajectories to CSV."""
from __future__ import annotations

import csv
import math
from pathlib import Path

import rclpy
from nav_msgs.msg import Odometry
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener


CSV_HEADER = ["stamp_s", "gt_x", "gt_y", "gt_yaw", "est_x", "est_y", "est_yaw"]


def yaw(q):
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z),
    )


class TrajectoryRecorder(Node):
    def __init__(self):
        super().__init__("trajectory_recorder")
        self.declare_parameter("output_path", "artifacts/trajectory.csv")
        self.declare_parameter("ground_truth_topic", "/ground_truth/odom")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("base_frame", "base_footprint")
        self.declare_parameter("sample_rate_hz", 10.0)

        self.latest_gt = None
        self.sample_count = 0

        # Evidence must survive a forced launch shutdown.  Previous versions
        # kept every sample only in memory and created trajectory.csv from the
        # node's finally block; if Gazebo made the launch graph require a
        # SIGTERM/SIGKILL escalation, an otherwise successful benchmark lost
        # the entire trajectory.  Create the artifact immediately and flush
        # each aligned sample as it is captured instead.
        self.output_path = Path(self.get_parameter("output_path").value)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.output_path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(CSV_HEADER)
        self._file.flush()

        self.tf = Buffer(cache_time=Duration(seconds=30.0))
        self.listener = TransformListener(self.tf, self)
        self.create_subscription(
            Odometry,
            self.get_parameter("ground_truth_topic").value,
            self._gt,
            20,
        )
        hz = max(float(self.get_parameter("sample_rate_hz").value), 0.1)
        self.create_timer(1.0 / hz, self._sample)

    def _gt(self, msg):
        self.latest_gt = msg

    def _sample(self):
        if self.latest_gt is None:
            return
        try:
            transform = self.tf.lookup_transform(
                self.get_parameter("map_frame").value,
                self.get_parameter("base_frame").value,
                Time(),
            )
        except TransformException:
            return

        gp = self.latest_gt.pose.pose.position
        gq = self.latest_gt.pose.pose.orientation
        ep = transform.transform.translation
        eq = transform.transform.rotation
        stamp = self.get_clock().now().nanoseconds / 1e9
        self._writer.writerow((stamp, gp.x, gp.y, yaw(gq), ep.x, ep.y, yaw(eq)))
        # Flush at capture time so the evidence is durable even if the launch
        # supervisor later has to terminate a stuck Gazebo process.
        self._file.flush()
        self.sample_count += 1

    def close(self):
        if getattr(self, "_file", None) is not None and not self._file.closed:
            self._file.flush()
            self._file.close()
        self.get_logger().info(
            f"persisted {self.sample_count} aligned trajectory samples to {self.output_path}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = TrajectoryRecorder()
    try:
        rclpy.spin(node)
    finally:
        node.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
