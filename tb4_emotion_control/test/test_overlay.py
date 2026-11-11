import numpy as np

from tb4_emotion_control.backends import FaceResult
from tb4_emotion_control.overlay import ACTION_TEXT, draw_overlay
from tb4_emotion_control.emotion_types import EMOTIONS

SCORES = {'happy': 80.0, 'sad': 5.0, 'neutral': 5.0, 'angry': 5.0, 'surprise': 3.0,
          'fear': 2.0, 'disgust': 0.0}


def blank():
    return np.zeros((480, 640, 3), np.uint8)


def test_every_emotion_has_an_action_text():
    assert set(ACTION_TEXT) == set(EMOTIONS)


def test_overlay_draws_on_the_frame_with_a_face():
    frame = blank()
    out = draw_overlay(frame, FaceResult((200, 100, 120, 120), SCORES), SCORES,
                       'happy', 0.8, 'happy', fps=6.0)
    assert out is frame and frame.any()


def test_overlay_without_face_or_scores_does_not_crash():
    frame = draw_overlay(blank(), None, None, 'none', 0.0, 'none')
    assert frame.any()      # header text is still drawn


def test_face_box_pixels_are_drawn():
    frame = draw_overlay(blank(), FaceResult((200, 150, 100, 100), SCORES), SCORES,
                         'happy', 0.8, 'happy')
    assert frame[150, 250].any() and not frame[300, 400].any()
