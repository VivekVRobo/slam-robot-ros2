from glob import glob
import os

from setuptools import setup

package_name = "slam_robot_ros2"


def existing(paths):
    return [path for path in paths if os.path.exists(path)]


data_files = [
    ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
    (f"share/{package_name}", ["package.xml"]),
]

for root_dir in ("launch", "config", "urdf", "worlds", "rviz", "docs", "media", "simulation"):
    if not os.path.exists(root_dir):
        continue
    for dirpath, _, filenames in os.walk(root_dir):
        files = [os.path.join(dirpath, f) for f in filenames if os.path.isfile(os.path.join(dirpath, f))]
        if files:
            dest_dir = os.path.join("share", package_name, dirpath)
            data_files.append((dest_dir, files))

setup(
    name=package_name,
    version="0.3.0",
    # Keep installation intentionally narrow.  The repository also contains
    # test/ and tools/ trees, but they are development assets rather than
    # importable runtime packages and must not be installed into site-packages.
    packages=[package_name],
    data_files=data_files,
    install_requires=["setuptools", "numpy>=1.24"],
    zip_safe=True,
    maintainer="Vivek Vala",
    maintainer_email="vivekvala562@gmail.com",
    description="ROS 2 SLAM platform with quantitative trajectory and loop-closure evaluation.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "benchmark_driver = slam_robot_ros2.benchmark_driver:main",
            "diagnostics = slam_robot_ros2.diagnostics:main",
            "mock_scan_publisher = slam_robot_ros2.mock_scan_publisher:main",
            "noisy_odom_publisher = slam_robot_ros2.noisy_odom_publisher:main",
            "tf_monitor = slam_robot_ros2.tf_monitor:main",
            "trajectory_recorder = slam_robot_ros2.trajectory_recorder:main",
        ],
    },
)
