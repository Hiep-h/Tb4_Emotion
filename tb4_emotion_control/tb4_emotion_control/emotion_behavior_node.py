"""/detected_emotion -> /cmd_vel trajectories for the six emotions.

Neutral stops at once. Any other stable emotion starts its timed trajectory
(a new emotion replaces the one running). If /detected_emotion goes silent the
robot stops, so a crashed webcam node never leaves it moving.
"""

import json
from dataclasses import fields

import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from rclpy.node import Node
from std_msgs.msg import String

from tb4_emotion_control.behaviors import (
    BehaviorParams,
    build_behaviors,
    total_duration,
    velocity_at,
)
from tb4_emotion_control.emotion_types import (
    CMD_VEL_TOPIC,
    DETECTED_EMOTION_TOPIC,
    KEY_CONFIDENCE,
    KEY_EMOTION,
    NONE,
)
from tb4_emotion_control.stabilizer import EdgeTracker


class EmotionBehaviorNode(Node):

    def __init__(self):
        super().__init__('emotion_behavior_node')
        self.declare_parameter('cmd_vel_topic', CMD_VEL_TOPIC)
        self.declare_parameter('use_stamped', False)
        self.declare_parameter('signal_timeout', 2.0)
        self.declare_parameter('required_consecutive', 3)
        self.declare_parameter('min_trigger_interval', 0.5)
        self.declare_parameter('retrigger_s', 0.0)
        self.declare_parameter('control_rate_hz', 20.0)
        defaults = BehaviorParams()
        for f in fields(BehaviorParams):
            self.declare_parameter(f.name, getattr(defaults, f.name))

        get = lambda name: self.get_parameter(name).value  # noqa: E731
        params = BehaviorParams(**{f.name: float(get(f.name)) for f in fields(BehaviorParams)})
        self._behaviors = build_behaviors(params)   # raises ValueError on unsafe values
        self._signal_timeout = float(get('signal_timeout'))
        self._tracker = EdgeTracker(int(get('required_consecutive')),
                                    float(get('min_trigger_interval')),
                                    float(get('retrigger_s')))

        self._stamped = bool(get('use_stamped'))
        self._pub = self.create_publisher(
            TwistStamped if self._stamped else Twist, get('cmd_vel_topic'), 10)
        self.create_subscription(String, DETECTED_EMOTION_TOPIC, self._on_emotion, 10)

        self._sequence = []
        self._started = 0.0
        self._running = None
        self._last_msg = None
        self._lost = False
        self.create_timer(1.0 / float(get('control_rate_hz')), self._control_step)
        self.get_logger().info('emotion_behavior_node sẵn sàng, robot đang đứng yên')

    def _now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _command(self, linear, angular):
        twist = Twist()
        twist.linear.x = float(linear)
        twist.angular.z = float(angular)
        if not self._stamped:
            return twist
        stamped = TwistStamped()
        stamped.header.stamp = self.get_clock().now().to_msg()
        stamped.twist = twist
        return stamped

    def _on_emotion(self, msg):
        now = self._now()
        self._last_msg = now
        if self._lost:
            self.get_logger().info('Tín hiệu biểu cảm đã trở lại')
            self._lost = False
        try:
            payload = json.loads(msg.data)
            emotion = payload.get(KEY_EMOTION, NONE)
            confidence = float(payload.get(KEY_CONFIDENCE, 0.0))
        except (ValueError, TypeError, AttributeError):
            self.get_logger().warning(f'Bản tin /detected_emotion sai định dạng: {msg.data!r}')
            return

        fired = self._tracker.process(emotion, now)
        if fired is None:
            return
        self.get_logger().info(f'Kích hoạt: {fired} (độ tin cậy {confidence:.2f})')
        self._start(fired)

    def _start(self, emotion):
        sequence = self._behaviors.get(emotion)
        if sequence is None:
            return
        if not sequence:        # neutral
            self._stop()
            return
        self._sequence = sequence
        self._started = self._now()
        self._running = emotion
        self.get_logger().info(
            f'Bắt đầu hành động "{emotion}" ({total_duration(sequence):.1f} s)')

    def _stop(self):
        self._sequence = []
        self._running = None
        self._pub.publish(self._command(0.0, 0.0))

    def _control_step(self):
        now = self._now()
        if self._last_msg is not None and now - self._last_msg > self._signal_timeout:
            if not self._lost:
                self._lost = True
                self.get_logger().warning(
                    f'Mất tín hiệu biểu cảm hơn {self._signal_timeout:.1f}s, dừng robot')
                self._stop()
            return
        if not self._sequence:
            return
        velocity = velocity_at(self._sequence, now - self._started)
        if velocity is None:
            self.get_logger().info(f'Hoàn thành hành động "{self._running}"')
            self._stop()
            return
        self._pub.publish(self._command(*velocity))


def main(args=None):
    rclpy.init(args=args)
    node = EmotionBehaviorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
