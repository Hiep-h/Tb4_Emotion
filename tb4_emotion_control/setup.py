import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'tb4_emotion_control'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Hiep-h',
    maintainer_email='hiepga05102005@gmail.com',
    description='Facial expression recognition that drives TurtleBot trajectories via /cmd_vel.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'emotion_recognition_node = tb4_emotion_control.emotion_recognition_node:main',
            'emotion_behavior_node = tb4_emotion_control.emotion_behavior_node:main',
            'fake_emotion_node = tb4_emotion_control.fake_emotion_node:main',
        ],
    },
)
