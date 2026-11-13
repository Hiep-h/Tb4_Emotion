"""Webcam -> facial emotion -> /detected_emotion, with a live preview window.

The model runs in a worker thread, so the camera preview stays smooth and only the label
updates a few times per second. Keys in the window:
  SPACE  switch the robot on/off (starts OFF for safety; recognition keeps running)
  s      stop the movement that is running
  q/ESC  quit
"""

import json
import threading
import time

import cv2
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from tb4_emotion_control.backends import make_backend
from tb4_emotion_control.emotion_types import (
    DETECTED_EMOTION_TOPIC,
    KEY_CONFIDENCE,
    KEY_EMOTION,
    KEY_ENABLED,
    KEY_FACE,
    KEY_STAMP,
    KEY_STOP_ID,
    NONE,
    ROBOT_STATE_TOPIC,
    face_is_large_enough,
    pick_emotion,
)
from tb4_emotion_control.overlay import draw_overlay
from tb4_emotion_control.stabilizer import MajorityVoter

RESULT_TTL_S = 1.5   # analysis older than this is treated as "no face"


class EmotionRecognitionNode(Node):

    def __init__(self):
        super().__init__('emotion_recognition_node')
        self.declare_parameter('backend', 'onnx')
        self.declare_parameter('model_path', '')
        self.declare_parameter('detector_backend', 'opencv')   # DeepFace only
        self.declare_parameter('camera_index', 0)
        self.declare_parameter('min_confidence', 0.40)
        self.declare_parameter('min_face_ratio', 0.15)
        self.declare_parameter('vote_window', 5)
        self.declare_parameter('vote_min', 3)
        self.declare_parameter('analyze_interval_s', 0.15)
        self.declare_parameter('publish_rate_hz', 10.0)
        self.declare_parameter('show_preview', True)
        self.declare_parameter('mirror', True)
        self.declare_parameter('start_enabled', False)

        get = lambda name: self.get_parameter(name).value  # noqa: E731
        self._min_confidence = float(get('min_confidence'))
        self._min_face_ratio = float(get('min_face_ratio'))
        self._interval = float(get('analyze_interval_s'))
        self._show = bool(get('show_preview'))
        self._mirror = bool(get('mirror'))
        self._publish_period = 1.0 / float(get('publish_rate_hz'))
        self._enabled = bool(get('start_enabled'))
        self._stop_id = 0

        self.get_logger().info(f"Đang nạp model nhận diện biểu cảm ({get('backend')})...")
        self._backend = make_backend(get('backend'), get('detector_backend'), get('model_path'))
        self._voter = MajorityVoter(int(get('vote_window')), int(get('vote_min')))

        self._cap = cv2.VideoCapture(int(get('camera_index')))
        if not self._cap.isOpened():
            raise RuntimeError(f"Không mở được webcam số {get('camera_index')}")

        self._lock = threading.Lock()
        self._frame = None
        self._frame_id = 0
        self._face = None
        self._scores = None
        self._raw = (NONE, 0.0)
        self._stable = NONE
        self._last_conf = {}
        self._result_time = 0.0
        self._infer_ms = None
        self._error = None
        self._analyses = 0
        self._analysis_rate = 0.0
        self._rate_mark = time.monotonic()
        self._last_publish = 0.0
        self._last_logged = None
        self._robot_state = None
        self._robot_state_rx = 0.0
        self._running = True

        self._pub = self.create_publisher(String, DETECTED_EMOTION_TOPIC, 10)
        self.create_subscription(String, ROBOT_STATE_TOPIC, self._on_robot_state, 10)
        self._worker = threading.Thread(target=self._analysis_loop, daemon=True)
        self._worker.start()
        self.get_logger().info(
            'emotion_recognition_node sẵn sàng. SPACE: bật/tắt robot, s: dừng, q hoặc ESC: thoát.')

    def _on_robot_state(self, msg):
        try:
            state = json.loads(msg.data)
        except ValueError:
            return
        self._robot_state = state
        self._robot_state_rx = time.monotonic()

    def _analysis_loop(self):
        last_id = -1
        while self._running:
            with self._lock:
                frame, frame_id = self._frame, self._frame_id
            if frame is None or frame_id == last_id:
                time.sleep(0.005)
                continue
            last_id = frame_id
            started = time.monotonic()
            try:
                face = self._backend.analyze(frame)
                error = None
            except Exception as exc:  # keep running if one frame fails
                face, error = None, str(exc)[:80]
                self.get_logger().error(f'Lỗi phân tích biểu cảm: {exc}', throttle_duration_sec=5.0)

            # Ignore faces that are too small: they belong to people behind the user.
            if face is not None and not face_is_large_enough(face.box, frame.shape[1],
                                                              self._min_face_ratio):
                face = None

            label, conf = (NONE, 0.0) if face is None else pick_emotion(face.scores)
            vote = label if conf >= self._min_confidence else NONE
            stable = self._voter.update(vote)
            if label != NONE:
                self._last_conf[label] = conf
            with self._lock:
                self._face = face
                self._scores = None if face is None else face.scores
                self._raw = (label, conf)
                self._stable = stable
                self._result_time = time.monotonic()
                self._infer_ms = (time.monotonic() - started) * 1000.0
                self._error = error
                self._analyses += 1
            time.sleep(max(0.0, self._interval - (time.monotonic() - started)))

    def _snapshot(self):
        with self._lock:
            waiting = self._result_time == 0.0
            fresh = time.monotonic() - self._result_time < RESULT_TTL_S
            face = self._face if fresh else None
            stable = self._stable if fresh else NONE
            raw = self._raw if fresh else (NONE, 0.0)
            scores = self._scores if fresh else None
            infer_ms, error = self._infer_ms, self._error
        return face, scores, raw, stable, infer_ms, error, waiting

    def _maybe_publish(self, face, stable):
        now = time.monotonic()
        if now - self._last_publish < self._publish_period:
            return
        self._last_publish = now
        conf = self._last_conf.get(stable, 0.0) if stable != NONE else 0.0
        msg = String()
        msg.data = json.dumps({
            KEY_EMOTION: stable,
            KEY_CONFIDENCE: round(conf, 3),
            KEY_FACE: face is not None,
            KEY_ENABLED: self._enabled,
            KEY_STOP_ID: self._stop_id,
            KEY_STAMP: self.get_clock().now().nanoseconds * 1e-9,
        })
        self._pub.publish(msg)
        if stable != self._last_logged:
            self.get_logger().info(f'Biểu cảm ổn định: {stable} ({conf:.2f})')
            self._last_logged = stable

    def _handle_key(self, key):
        """Return False when the user asked to quit."""
        if key in (ord('q'), 27):
            return False
        if key == ord(' '):
            self._enabled = not self._enabled
            self.get_logger().info('Robot ' + ('BẬT' if self._enabled else 'TẮT'))
        elif key == ord('s'):
            self._stop_id += 1
            self.get_logger().info('Dừng chuyển động đang chạy')
        return True

    def spin_once_cycle(self):
        ok, frame = self._cap.read()
        if not ok:
            self.get_logger().warning('Không đọc được khung hình từ webcam',
                                      throttle_duration_sec=2.0)
            return True
        if self._mirror:
            frame = cv2.flip(frame, 1)
        with self._lock:
            self._frame = frame
            self._frame_id += 1

        face, scores, raw, stable, infer_ms, error, waiting = self._snapshot()
        self._maybe_publish(face, stable)

        if self._show:
            now = time.monotonic()
            if now - self._rate_mark >= 1.0:
                with self._lock:
                    self._analysis_rate = self._analyses / (now - self._rate_mark)
                    self._analyses = 0
                self._rate_mark = now
            state = self._robot_state if now - self._robot_state_rx < 2.0 else None
            display = draw_overlay(frame.copy(), face, scores, raw[0], raw[1], stable, state,
                                   self._analysis_rate, infer_ms, error, waiting)
            cv2.imshow('TB4 Emotion Recognition', display)
            return self._handle_key(cv2.waitKey(1) & 0xFF)
        return True

    def destroy_node(self):
        self._running = False
        try:
            self._cap.release()
            cv2.destroyAllWindows()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = EmotionRecognitionNode()
    try:
        running = True
        while rclpy.ok() and running:
            running = node.spin_once_cycle()
            rclpy.spin_once(node, timeout_sec=0.0)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
