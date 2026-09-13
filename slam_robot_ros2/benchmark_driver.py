"""Replay a deterministic open-loop benchmark path; simulation-only by default."""
from __future__ import annotations

from pathlib import Path

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Twist
from rclpy.node import Node


class BenchmarkDriver(Node):
    def __init__(self):
        super().__init__('benchmark_driver')
        default = str(
            Path(get_package_share_directory('slam_robot_ros2'))
            / 'config'
            / 'benchmark_path.yaml'
        )
        self.declare_parameter('profile_file', default)
        self.declare_parameter('allow_hardware', False)
        if not self.has_parameter('use_sim_time'):
            self.declare_parameter('use_sim_time', True)
        if (
            not self.get_parameter('allow_hardware').value
            and not self.get_parameter('use_sim_time').value
        ):
            raise RuntimeError(
                'benchmark_driver is simulation-only by default; '
                'set allow_hardware:=true only after safety review'
            )

        data = yaml.safe_load(
            Path(self.get_parameter('profile_file').value).read_text()
        )
        self.segments = data['segments']
        self.i = 0
        self.elapsed = 0.0
        self.dt = 0.05
        self.finished = False

        # Command velocity is latest-state control data, not a work queue. Keep only
        # the newest sample so a slow bridge cannot replay stale segment commands.
        self.pub = self.create_publisher(Twist, '/cmd_vel', 1)
        self.timer = self.create_timer(self.dt, self.tick)
        self.get_logger().info(
            f"benchmark profile={data.get('profile')} segments={len(self.segments)}"
        )

    def tick(self):
        if self.i >= len(self.segments):
            if not self.finished:
                self.pub.publish(Twist())
                self.finished = True
            return

        seg = self.segments[self.i]
        msg = Twist()
        msg.linear.x = float(seg['linear_x'])
        msg.angular.z = float(seg['angular_z'])
        self.pub.publish(msg)

        self.elapsed += self.dt
        if self.elapsed >= float(seg['duration_s']):
            self.get_logger().info(f"segment complete: {seg['name']}")
            self.i += 1
            self.elapsed = 0.0


def main(args=None):
    rclpy.init(args=args)
    node = BenchmarkDriver()
    try:
        rclpy.spin(node)
    finally:
        if rclpy.ok():
            node.pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
