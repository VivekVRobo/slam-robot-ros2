"""Record synchronized ground-truth and SLAM-estimated planar trajectories to CSV."""
from __future__ import annotations
import csv, math
from pathlib import Path
import rclpy
from nav_msgs.msg import Odometry
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener

def yaw(q):
    return math.atan2(2.0*(q.w*q.z+q.x*q.y),1.0-2.0*(q.y*q.y+q.z*q.z))

class TrajectoryRecorder(Node):
    def __init__(self):
        super().__init__('trajectory_recorder')
        self.declare_parameter('output_path','artifacts/trajectory.csv')
        self.declare_parameter('ground_truth_topic','/ground_truth/odom')
        self.declare_parameter('map_frame','map')
        self.declare_parameter('base_frame','base_footprint')
        self.declare_parameter('sample_rate_hz',10.0)
        self.latest_gt=None; self.rows=[]
        path=Path(self.get_parameter('output_path').value); path.parent.mkdir(parents=True,exist_ok=True)
        self._file=path.open('w',newline='',encoding='utf-8'); self._writer=csv.writer(self._file)
        self._writer.writerow(['stamp_s','gt_x','gt_y','gt_yaw','est_x','est_y','est_yaw']); self._file.flush()
        self.tf=Buffer(cache_time=Duration(seconds=30.0)); self.listener=TransformListener(self.tf,self)
        self.create_subscription(Odometry,self.get_parameter('ground_truth_topic').value,self._gt,20)
        hz=max(float(self.get_parameter('sample_rate_hz').value),0.1); self.create_timer(1.0/hz,self._sample)
    def _gt(self,msg): self.latest_gt=msg
    def _sample(self):
        if self.latest_gt is None:return
        try:t=self.tf.lookup_transform(self.get_parameter('map_frame').value,self.get_parameter('base_frame').value,Time())
        except TransformException:return
        gp=self.latest_gt.pose.pose.position; gq=self.latest_gt.pose.pose.orientation; ep=t.transform.translation; eq=t.transform.rotation
        stamp=self.get_clock().now().nanoseconds/1e9
        row=(stamp,gp.x,gp.y,yaw(gq),ep.x,ep.y,yaw(eq)); self.rows.append(row)
        self._writer.writerow(row); self._file.flush()
    def close(self):
        if self._file.closed:return
        self._file.flush(); self._file.close()
        self.get_logger().info(f'wrote {len(self.rows)} aligned trajectory samples to {self.get_parameter("output_path").value}')
def main(args=None):
    rclpy.init(args=args); n=TrajectoryRecorder()
    try:rclpy.spin(n)
    finally:n.close();n.destroy_node();rclpy.shutdown()
if __name__=='__main__':main()
