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

for directory in ("launch", "config", "urdf", "worlds", "rviz"):
    files = existing(glob(f"{directory}/*"))
    if files:
        data_files.append((os.path.join("share", package_name, directory), files))

for directory in ("docs", "media"):
    files = existing(glob(f"{directory}/*"))
    if files:
        data_files.append((os.path.join("share", package_name, directory), files))

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
    maintainer="VivekVRobotics",
    maintainer_email="vivekvala562@gmail.com",
    description="ROS 2 SLAM platform with quantitative trajectory and loop-closure evaluation.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "mock_scan_publisher = slam_robot_ros2.mock_scan_publisher:main",
            "noisy_odom_publisher = slam_robot_ros2.noisy_odom_publisher:main",
        ],
    },
)
