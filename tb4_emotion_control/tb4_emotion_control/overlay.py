"""Live result drawn on the webcam frame. OpenCV fonts cannot render Vietnamese accents, so labels
are written without them."""

import cv2

from tb4_emotion_control.emotion_types import EMOTIONS, NONE, normalize_scores

COLORS = {  # BGR
    'happy': (0, 200, 255), 'sad': (255, 120, 0), 'neutral': (200, 200, 200),
    'angry': (0, 0, 255), 'surprise': (255, 0, 255), 'fear': (0, 160, 0),
}
VI_NAMES = {'happy': 'Vui ve', 'sad': 'Buon', 'neutral': 'Binh thuong',
            'angry': 'Tuc gian', 'surprise': 'Ngac nhien', 'fear': 'So hai'}
ACTION_TEXT = {
    'happy': 'Curve LEFT', 'sad': 'Curve RIGHT', 'neutral': 'STOP',
    'angry': 'Back up', 'surprise': 'Spin 360', 'fear': 'Step forward',
}
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)


def action_line(robot_state):
    """(text, color) describing what the robot is doing, from /emotion_robot_state."""
    if robot_state is None:
        return 'Chua nhan trang thai robot', YELLOW
    if not robot_state.get('enabled', True):
        return 'ROBOT TAT - nhan SPACE de bat', RED
    running = robot_state.get('running')
    if running in ACTION_TEXT:
        return f"Dang chay: {ACTION_TEXT[running]} (con {robot_state.get('remaining', 0.0):.1f}s)", GREEN
    return 'Dung yen', GREEN


def draw_overlay(frame, face, scores, raw_label, raw_conf, stable, robot_state=None,
                 fps=None, infer_ms=None, error=None, waiting=False):
    """Face box, six score bars, status bar and robot action. Returns the same frame."""
    height, width = frame.shape[:2]

    if face is not None:
        x, y, w, h = (int(v) for v in face.box)
        color = COLORS.get(raw_label, WHITE)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        text = f'{raw_label} {raw_conf * 100:.0f}%' if raw_label != NONE else 'unsure'
        cv2.putText(frame, text, (x, max(80, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    scores = normalize_scores(scores) if scores else {}
    if scores:
        for i, emotion in enumerate(EMOTIONS):
            y0 = 70 + i * 22
            value = max(0.0, min(1.0, scores.get(emotion, 0.0)))
            cv2.rectangle(frame, (width - 170, y0), (width - 170 + int(100 * value), y0 + 15),
                          COLORS[emotion], -1)
            cv2.putText(frame, emotion, (width - 65, y0 + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        WHITE, 1)

    cv2.rectangle(frame, (0, 0), (width, 60), (0, 0, 0), -1)
    if waiting:
        status = 'Dang nap model... (lan dau co the lau)'
    elif stable != NONE:
        status = f'Bieu cam: {VI_NAMES.get(stable, stable)}'
    else:
        status = 'Bieu cam: (chua chac)' if face is not None else 'Bieu cam: (khong thay mat)'
    text, color = action_line(robot_state)
    cv2.putText(frame, status, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)
    cv2.putText(frame, text, (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    info = []
    if fps is not None:
        info.append(f'{fps:.0f} FPS')
    if infer_ms is not None:
        info.append(f'infer {infer_ms:.0f} ms')
    if error:
        info.append('loi: ' + error[:40])
    info.append('SPACE bat/tat | s dung | q thoat')
    cv2.putText(frame, ' | '.join(info), (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                YELLOW, 1)
    return frame
