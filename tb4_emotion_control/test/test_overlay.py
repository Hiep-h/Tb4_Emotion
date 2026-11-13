import numpy as np

from tb4_emotion_control.backends import FaceResult
from tb4_emotion_control.emotion_types import EMOTIONS
from tb4_emotion_control.overlay import ACTION_TEXT, VI_NAMES, action_line, draw_overlay

SCORES = {'happy': 0.8, 'sad': 0.05, 'neutral': 0.05, 'angry': 0.05, 'surprise': 0.03,
          'fear': 0.02, 'disgust': 0.0}


def blank():
    return np.zeros((480, 640, 3), np.uint8)


def test_every_emotion_has_texts():
    assert set(ACTION_TEXT) == set(EMOTIONS) == set(VI_NAMES)


def test_action_line_states():
    assert 'chua nhan' in action_line(None)[0].lower()
    assert 'TAT' in action_line({'enabled': False})[0]
    text, _ = action_line({'enabled': True, 'running': 'surprise', 'remaining': 3.26})
    assert 'Spin 360' in text and '3.3' in text
    assert action_line({'enabled': True, 'running': None})[0] == 'Dung yen'


def test_overlay_draws_face_box_scores_and_status():
    frame = blank()
    out = draw_overlay(frame, FaceResult((200, 150, 120, 120), SCORES), SCORES, 'happy', 0.8,
                       'happy', {'enabled': True, 'running': 'happy', 'remaining': 2.0},
                       fps=25.0, infer_ms=12.0)
    assert out is frame
    assert frame[150, 260].any()            # face box edge
    assert frame[5:55, 5:300].any()         # status bar text
    assert frame[70:80, 480:560].any()      # score bar


def test_overlay_without_face_scores_or_state_does_not_crash():
    assert draw_overlay(blank(), None, None, 'none', 0.0, 'none').any()
    assert draw_overlay(blank(), None, None, 'none', 0.0, 'none', waiting=True,
                        error='boom').any()
