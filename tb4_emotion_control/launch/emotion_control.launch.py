"""Webcam emotion recognition + robot behaviour.

  ros2 launch tb4_emotion_control emotion_control.launch.py
  ros2 launch tb4_emotion_control emotion_control.launch.py backend:=fer camera_index:=1
  ros2 launch tb4_emotion_control emotion_control.launch.py fake:=true   # no webcam
  ros2 launch tb4_emotion_control emotion_control.launch.py use_sim_time:=true   # with Gazebo
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    args = [
        DeclareLaunchArgument('backend', default_value='onnx',
                              description='onnx (nhẹ, mặc định) | deepface | fer'),
        DeclareLaunchArgument('camera_index', default_value='0'),
        DeclareLaunchArgument('show_preview', default_value='true'),
        DeclareLaunchArgument('start_enabled', default_value='false',
                              description='true = robot bật ngay (mặc định tắt, bấm SPACE trong cửa sổ để bật)'),
        DeclareLaunchArgument('fake', default_value='false',
                              description='true = phát biểu cảm giả, không cần webcam'),
        DeclareLaunchArgument('use_stamped', default_value='false',
                              description='true = /cmd_vel là TwistStamped (ROS 2 Jazzy trở lên)'),
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='true khi chạy với Gazebo: đếm thời gian quỹ đạo theo '
                                          'đồng hồ mô phỏng (đúng cả khi Gazebo chạy dưới 100%)'),
    ]
    recognition = Node(
        package='tb4_emotion_control', executable='emotion_recognition_node',
        name='emotion_recognition_node', output='screen',
        condition=UnlessCondition(LaunchConfiguration('fake')),
        parameters=[{
            'backend': LaunchConfiguration('backend'),
            'camera_index': LaunchConfiguration('camera_index'),
            'show_preview': LaunchConfiguration('show_preview'),
            'start_enabled': LaunchConfiguration('start_enabled'),
        }])
    fake = Node(
        package='tb4_emotion_control', executable='fake_emotion_node',
        name='fake_emotion_node', output='screen',
        condition=IfCondition(LaunchConfiguration('fake')),
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}])
    behavior = Node(
        package='tb4_emotion_control', executable='emotion_behavior_node',
        name='emotion_behavior_node', output='screen',
        parameters=[{'use_stamped': LaunchConfiguration('use_stamped'),
                     'use_sim_time': LaunchConfiguration('use_sim_time')}])
    return LaunchDescription(args + [recognition, fake, behavior])
