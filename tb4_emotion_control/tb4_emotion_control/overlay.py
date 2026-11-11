"""Draws the live result on a webcam frame. OpenCV fonts cannot render Vietnamese, so labels are English."""

import cv2

from tb4_emotion_control.emotion_types import EMOTIONS, NONE, normalize_scores

ACTION_TEXT = {
    'happy': 'curve left',
    'sad': 'curve right',
    'neutral': 'stop',
    'angry': 'back up',
    'surprise': 'spin 360',
    'fear': 'forward',
}

GREEN = (0, 200, 0)
ORANGE = (0, 165, 255)
WHITE = (255, 255, 255)
GREY = (90, 90, 90)


def draw_overlay(frame, face, scores, raw_label, raw_conf, stable, fps=None):
    """Draw face box, six score bars and the stable action. Returns the same frame."""
    active = stable != NONE
    color = GREEN if active else ORANGE

    if face is not None:
        x, y, w, h = (int(v) for v in face.box)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        text = f'{raw_label} {raw_conf * 100:.0f}%' if raw_label != NONE else 'unsure'
        cv2.putText(frame, text, (x, max(18, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    scores = normalize_scores(scores) if scores else {}
    base_y = frame.shape[0] - 12 - 22 * (len(EMOTIONS) - 1)
    for i, emotion in enumerate(EMOTIONS):
        y = base_y + 22 * i
        value = max(0.0, min(1.0, scores.get(emotion, 0.0)))
        cv2.putText(frame, emotion, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)
        cv2.rectangle(frame, (95, y - 11), (195, y + 2), GREY, 1)
        cv2.rectangle(frame, (95, y - 11), (95 + int(100 * value), y + 2),
                      GREEN if emotion == stable else ORANGE, -1)

    if active:
        header = f'Action: {stable.upper()} -> {ACTION_TEXT[stable]}'
    else:
        header = 'No stable emotion' if face is not None else 'No face'
    cv2.putText(frame, header, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    if fps is not None:
        cv2.putText(frame, f'{fps:.1f} analyses/s', (10, 54), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, WHITE, 1)
    return frame
