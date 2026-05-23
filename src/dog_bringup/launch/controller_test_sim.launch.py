import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.parameter_descriptions import ParameterValue


def cmd_vel_once(delay, linear_x=0.0, linear_y=0.0, angular_z=0.0):
    return TimerAction(
        period=delay,
        actions=[
            ExecuteProcess(
                cmd=[
                    "ros2",
                    "topic",
                    "pub",
                    "--once",
                    "/cmd_vel",
                    "geometry_msgs/msg/Twist",
                    "{linear: {x: "
                    + str(linear_x)
                    + ", y: "
                    + str(linear_y)
                    + ", z: 0.0}, angular: {x: 0.0, y: 0.0, z: "
                    + str(angular_z)
                    + "}}",
                ],
                output="screen",
                condition=IfCondition(LaunchConfiguration("command_test")),
            )
        ],
    )


def generate_launch_description():
    gazebo_pkg = get_package_share_directory("gazebo_ros")
    pkg = get_package_share_directory("dog_bringup")

    use_rviz = LaunchConfiguration("use_rviz")
    gui = LaunchConfiguration("gui")
    world = LaunchConfiguration("world")

    xacro_file = os.path.join(pkg, "xacro", "cdut_dog", "dog.xacro")
    rviz_config_file = os.path.join(pkg, "config", "dog.rviz")
    xacro_command = ["xacro ", xacro_file, " is_sim:=true"]

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_pkg, "launch", "gazebo.launch.py")
        ),
        launch_arguments=[("world", world), ("verbose", "true"), ("gui", gui)],
    )

    dog_state_container = ComposableNodeContainer(
        name="dog_controller_test_container",
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
            "dog_robot_controller_test",
            "-x",
            "0.0",
            "-y",
            "0.0",
            "-z",
            "0.35",
            "-timeout",
            "300",
        ],
        output="screen",
    )

    joint_state_broadcaster_spawner = TimerAction(
        period=3.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "joint_state_broadcaster",
                    "--controller-manager",
                    "/controller_manager",
                ],
                output="screen",
            )
        ],
    )

    imu_broadcaster_spawner = TimerAction(
        period=4.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "imu_sensor_broadcaster",
                    "--controller-manager",
                    "/controller_manager",
                ],
                output="screen",
            )
        ],
    )

    controller_spawner = TimerAction(
        period=5.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "DogNmpcWbcControllerSim",
                    "--controller-manager",
                    "/controller_manager",
                ],
                output="screen",
            )
        ],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", rviz_config_file],
        output="screen",
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "world",
                default_value=os.path.join(pkg, "config", "controller_test.world"),
                description="Gazebo world file for controller testing.",
            ),
            DeclareLaunchArgument("gui", default_value="true"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument("command_test", default_value="true"),
            gazebo,
            dog_state_container,
            spawn_entity,
            joint_state_broadcaster_spawner,
            imu_broadcaster_spawner,
            controller_spawner,
            rviz_node,
            cmd_vel_once(9.0, linear_x=0.15),
            cmd_vel_once(12.0, linear_x=0.15),
            cmd_vel_once(15.0, angular_z=0.25),
            cmd_vel_once(18.0, linear_x=0.10, linear_y=0.05),
            cmd_vel_once(21.0),
        ]
    )
