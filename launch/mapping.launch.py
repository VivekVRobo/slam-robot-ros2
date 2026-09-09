from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, RegisterEventHandler
from launch.events import matches_action
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode
from launch_ros.descriptions import ParameterFile
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition

def generate_launch_description():
    pkg = Path(get_package_share_directory("slam_robot_ros2"))
    params = LaunchConfiguration("slam_params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")
    scan_topic = LaunchConfiguration("scan_topic")
    node = LifecycleNode(
        package="slam_toolbox",
        executable="async_slam_toolbox_node",
        namespace="",
        name="slam_toolbox",
        output="screen",
        parameters=[
            ParameterFile(params, allow_substs=True),
            {"use_sim_time": use_sim_time, "scan_topic": scan_topic},
        ],
    )
    configure = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_action(node),
            transition_id=Transition.TRANSITION_CONFIGURE,
        )
    )
    activate = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=node,
            start_state="configuring",
            goal_state="inactive",
            entities=[EmitEvent(event=ChangeState(
                lifecycle_node_matcher=matches_action(node),
                transition_id=Transition.TRANSITION_ACTIVATE,
            ))],
        )
    )
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument("scan_topic", default_value="/scan"),
        DeclareLaunchArgument(
            "slam_params_file", default_value=str(pkg / "config" / "slam_toolbox.yaml")
        ),
        node, configure, activate,
    ])
