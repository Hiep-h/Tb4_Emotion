import numpy as np
import pytest

from tb4_emotion_control.backends import (
    FERPLUS_LABELS,
    crop_face,
    ferplus_scores,
    largest_face,
    softmax,
)
from tb4_emotion_control.emotion_types import EMOTIONS, face_is_large_enough, pick_emotion


def test_softmax_sums_to_one_and_keeps_order():
    p = softmax(np.array([1.0, 3.0, 2.0]))
    assert p.sum() == pytest.approx(1.0) and p.argmax() == 1


def test_ferplus_label_order_matches_the_model_zoo():
    assert FERPLUS_LABELS[:3] == ('neutral', 'happy', 'surprise')
    logits = np.zeros(8)
    logits[1] = 6.0                                   # index 1 = happy
    scores = ferplus_scores(logits)
    assert sum(scores.values()) == pytest.approx(1.0)
    assert pick_emotion(scores)[0] == 'happy'


def test_contempt_and_disgust_give_no_decision():
    for index in (5, 7):                               # disgust, contempt
        logits = np.zeros(8)
        logits[index] = 6.0
        assert pick_emotion(ferplus_scores(logits)) == ('none', 0.0)
    assert set(FERPLUS_LABELS) - set(EMOTIONS) == {'disgust', 'contempt'}


def test_largest_face_picks_biggest_and_clamps_to_frame():
    faces = np.array([[10, 10, 30, 30, 0.9], [100, 50, 200, 200, 0.95], [5, 5, 40, 40, 0.8]])
    assert largest_face(faces, (240, 320, 3)) == (100, 50, 200, 190)
    assert largest_face(None, (240, 320, 3)) is None
    assert largest_face(np.zeros((0, 5)), (240, 320, 3)) is None
    assert largest_face(np.array([[-20, -10, 50, 60, 0.9]]), (240, 320, 3)) == (0, 0, 50, 60)


def test_crop_face_shape_dtype_and_range():
    gray = (np.random.default_rng(0).random((240, 320)) * 255).astype(np.uint8)
    crop = crop_face(gray, (100, 60, 80, 80))
    assert crop.shape == (1, 1, 64, 64) and crop.dtype == np.float32
    assert 0.0 <= crop.min() and crop.max() <= 255.0          # raw pixels, not normalised
    assert crop_face(gray, (0, 0, 50, 50)).shape == (1, 1, 64, 64)   # margin clipped at the edge


def test_small_background_faces_are_rejected():
    assert not face_is_large_enough((0, 0, 40, 40), 640, 0.15)      # classmate behind: ~40 px
    assert face_is_large_enough((200, 100, 185, 185), 640, 0.15)     # the user: ~185 px
