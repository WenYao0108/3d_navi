import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    gazebo_pkg = get_package_share_directory("gazebo_ros")
    pkg = get_package_share_directory("dog_bringup")

    xacro_file = os.path.join(pkg, "xacro", "cdut_dog", "dog.xacro")
    world_file = os.path.join(pkg, "config", "inspection_stairs.world")
    rviz_config_file = os.path.join(pkg, "dog.rviz")
    urdf_output_dir = os.path.join(pkg, "config", "cdut_dog", "description")
    urdf_output_file = os.path.join(urdf_output_dir, "dog.urdf")
    xacro_command = ["xacro ", xacro_file, " is_sim:=true"]

    generate_urdf = ExecuteProcess(
        cmd=[
            f"mkdir -p {urdf_output_dir} && xacro {xacro_file} is_sim:=true -o {urdf_output_file}"
        ],
        shell=True,
        output="screen",
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_pkg, "launch", "gazebo.launch.py")
        ),
        launch_arguments=[("world", world_file), ("verbose", "true")],
    )

    robot_state_publisher = ComposableNodeContainer(
        name="dog_state_container",
        namespace="",
        package="rclcpp_components",
        executable="component_container",
        composable_node_descriptions=[
            ComposableNode(
                package="robot_state_publisher",
                plugin="robot_state_publisher::RobotStatePublisher",
                name="robot_state_publisher",
                parameters=[
                    {
                        "robot_description": ParameterValue(
                            Command(xacro_command), value_type=str
                        )
                    }
                ],
            ),
            ComposableNode(
                package="dog_controllers",
                plugin="dog_controllers::TargetTrajectoriesPublisher",
                name="target_trajectories_publisher",
            ),
        ],
        output="screen",
    )

    spawn_entity = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=[
            "-topic",
            "robot_description",
            "-entity",
            "dog_robot",
            "-x",
            "-9.0",
            "-y",
            "0",
            "-z",
            "0.35",
            "-timeout",
            "300",
        ],
        output="screen",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
    )

    controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["DogNmpcWbcControllerSim"],
    )

    local_path_follower = Node(
        package="local_path_follower",
        executable="local_path_follower",
        name="local_path_follower",
        output="screen",
        parameters=[
            {
                "path_topic": "/visual_local_trajectory",
                "odom_topic": "/odom",
                "cmd_topic": "/cmd_vel",
                "lookahead_dist": 0.8,
                "max_linear_vel": 0.25,
                "max_angular_vel": 0.6,
                "goal_tolerance": 0.25,
                "simulate_odom": False,
            }
        ],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", rviz_config_file],
        output="screen",
    )

    return LaunchDescription(
        [
            generate_urdf,
            gazebo,
            robot_state_publisher,
            spawn_entity,
            joint_state_broadcaster_spawner,
            controller_spawner,
            local_path_follower,
            rviz_node,
        ]
    )
