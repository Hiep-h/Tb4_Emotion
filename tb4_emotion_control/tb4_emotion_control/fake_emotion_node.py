"""Publishes scripted emotions so the robot side can be tested without a webcam."""

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from tb4_emotion_control.emotion_types import (
    DETECTED_EMOTION_TOPIC,
    KEY_CONFIDENCE,
    KEY_EMOTION,
    KEY_FACE,
    KEY_STAMP,
)

# Neutral between actions lets each trajectory finish (the spin takes ~8 s).
DEFAULT_SCRIPT = ['happy', 'neutral', 'sad', 'neutral', 'angry', 'neutral',
                  'surprise', 'neutral', 'fear', 'neutral']


class FakeEmotionNode(Node):

    def __init__(self):
        super().__init__('fake_emotion_node')
        self.declare_parameter('script', DEFAULT_SCRIPT)
        self.declare_parameter('interval_s', 10.0)
        self._script = list(self.get_parameter('script').value)
        self._interval = float(self.get_parameter('interval_s').value)
        self._start = self.get_clock().now().nanoseconds * 1e-9
        self._pub = self.create_publisher(String, DETECTED_EMOTION_TOPIC, 10)
        self._last = None
        self.create_timer(0.1, self._tick)
        self.get_logger().info(
            f'fake_emotion_node: {len(self._script)} bước, mỗi bước {self._interval:.0f} s')

    def _tick(self):
        now = self.get_clock().now().nanoseconds * 1e-9
        index = int((now - self._start) // self._interval) % len(self._script)
        emotion = self._script[index]
        if emotion != self._last:
            self.get_logger().info(f'Giả lập biểu cảm: {emotion}')
            self._last = emotion
        msg = String()
        msg.data = json.dumps({KEY_EMOTION: emotion, KEY_CONFIDENCE: 0.9,
                               KEY_FACE: True, KEY_STAMP: now})
        self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = FakeEmotionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
