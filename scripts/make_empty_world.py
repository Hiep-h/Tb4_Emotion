#!/usr/bin/env python3
"""Make an empty TurtleBot 4 Gazebo world (flat floor, nothing else, no downloaded models).

It is derived from the installed warehouse.sdf, so it keeps the plugins the
TurtleBot 4 simulation expects, minus the Fuel models that need Internet.

  python3 scripts/make_empty_world.py                  # writes ~/empty.sdf
  sudo cp ~/empty.sdf /opt/ros/humble/share/turtlebot4_ignition_bringup/worlds/empty.sdf
  ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py world:=empty
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_SOURCE = '/opt/ros/humble/share/turtlebot4_ignition_bringup/worlds/warehouse.sdf'

# warehouse.sdf already has an (invisible) collision ground_plane; the visible floor lived in a
# Fuel model, so add a visual-only floor. Lighting is the world's own white ambient light.
FLOOR_VISUAL = """
    <model name='floor_visual'>
      <static>true</static>
      <link name='link'>
        <visual name='visual'>
          <geometry><plane><normal>0 0 1</normal><size>100 100</size></plane></geometry>
          <material>
            <ambient>0.75 0.75 0.75 1</ambient>
            <diffuse>0.75 0.75 0.75 1</diffuse>
          </material>
        </visual>
      </link>
    </model>
"""


def make_empty_world(source_text):
    text = re.sub(r'<include>.*?</include>', '', source_text, flags=re.DOTALL)
    text, count = re.subn(r"<world name=['\"]warehouse['\"]>", "<world name='empty'>", text)
    if count != 1:
        raise ValueError("Không tìm thấy <world name='warehouse'> trong file nguồn")
    text = text.replace('</world>', FLOOR_VISUAL + '  </world>', 1)

    root = ET.fromstring(text)           # raises if the result is not valid XML
    world = root.find('world')
    if world is None or world.get('name') != 'empty':
        raise ValueError('World sinh ra không hợp lệ')
    if any(True for _ in root.iter('include')):
        raise ValueError('Vẫn còn <include> trong world')
    names = [m.get('name') for m in world.findall('model')]
    if sorted(names) != ['floor_visual', 'ground_plane']:
        raise ValueError(f'Danh sách model bất thường: {names}')
    return text


def main():
    source = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE)
    target = Path(sys.argv[2] if len(sys.argv) > 2 else Path.home() / 'empty.sdf')
    if not source.is_file():
        sys.exit(f'Không thấy {source}. Truyền đường dẫn warehouse.sdf làm tham số đầu tiên.')
    target.write_text(make_empty_world(source.read_text()))
    print(f'Đã tạo {target}')
    print('Bước tiếp theo:')
    print(f'  sudo cp {target} {source.parent}/empty.sdf')
    print('  ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py world:=empty')


if __name__ == '__main__':
    main()
