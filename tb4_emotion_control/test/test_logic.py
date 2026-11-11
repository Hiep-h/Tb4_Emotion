import math

import pytest

from tb4_emotion_control.behaviors import (
    MAX_ANGULAR,
    MAX_LINEAR,
    BehaviorParams,
    build_behaviors,
    total_duration,
    validate,
    velocity_at,
)
from tb4_emotion_control.emotion_types import EMOTIONS, NONE, normalize_scores, pick_emotion
from tb4_emotion_control.stabilizer import EdgeTracker, MajorityVoter

B = build_behaviors(BehaviorParams())


# ---- scores ----------------------------------------------------------------

def test_deepface_percentages_are_scaled():
    label, conf = pick_emotion({'angry': 1.0, 'disgust': 0.0, 'fear': 2.0, 'happy': 90.0,
                                'sad': 3.0, 'surprise': 2.0, 'neutral': 2.0})
    assert label == 'happy' and conf == pytest.approx(0.9)


def test_fer_fractions_are_kept():
    label, conf = pick_emotion({'Angry': 0.05, 'disgust': 0.0, 'fear': 0.05, 'happy': 0.1,
                                'sad': 0.6, 'surprise': 0.1, 'neutral': 0.1})
    assert label == 'sad' and conf == pytest.approx(0.6)


def test_disgust_and_empty_give_no_decision():
    assert pick_emotion({'disgust': 80.0, 'neutral': 20.0}) == (NONE, 0.0)
    assert pick_emotion({}) == (NONE, 0.0)


def test_normalize_scores_lowercases():
    assert 'happy' in normalize_scores({'HAPPY': 0.5, 'sad': 0.5})


# ---- behaviours ------------------------------------------------------------

def test_all_six_emotions_have_a_behaviour():
    assert set(B) == set(EMOTIONS)


def test_neutral_is_stop():
    assert B['neutral'] == []
    assert velocity_at(B['neutral'], 0.0) is None


def test_happy_curves_left_and_sad_curves_right():
    (hl, ha), (sl, sa) = velocity_at(B['happy'], 0.1), velocity_at(B['sad'], 0.1)
    assert hl > 0 and ha > 0      # forward + counter-clockwise = left
    assert sl > 0 and sa < 0      # forward + clockwise = right
    assert hl == sl and ha == -sa


def test_angry_backs_up_and_fear_goes_forward_a_little():
    angry, fear = velocity_at(B['angry'], 0.1), velocity_at(B['fear'], 0.1)
    assert angry[0] < 0 and angry[1] == 0
    assert fear[0] > 0 and fear[1] == 0
    for seg in (*B['angry'], *B['fear']):
        assert abs(seg.linear) * seg.duration < 0.3     # "slightly"


def test_surprise_spins_exactly_one_turn_in_place():
    seg = B['surprise'][0]
    assert seg.linear == 0
    assert seg.angular * seg.duration == pytest.approx(2 * math.pi)
    two = build_behaviors(BehaviorParams(spin_turns=2.0))['surprise'][0]
    assert two.angular * two.duration == pytest.approx(4 * math.pi)


def test_velocity_at_ends_after_total_duration():
    segs = B['happy']
    assert velocity_at(segs, total_duration(segs) - 0.01) is not None
    assert velocity_at(segs, total_duration(segs)) is None


def test_unsafe_parameters_are_rejected():
    with pytest.raises(ValueError):
        validate(BehaviorParams(curve_linear=MAX_LINEAR + 0.1))
    with pytest.raises(ValueError):
        validate(BehaviorParams(spin_speed=MAX_ANGULAR + 0.1))
    with pytest.raises(ValueError):
        validate(BehaviorParams(back_duration=0.0))


# ---- noise rejection --------------------------------------------------------

def test_voter_needs_majority_and_full_window():
    v = MajorityVoter(window=5, min_votes=3)
    out = [v.update(x) for x in ['happy', 'happy', 'happy', 'sad', 'happy']]
    assert out[:4] == [NONE] * 4 and out[4] == 'happy'


def test_voter_rejects_flicker():
    v = MajorityVoter(window=5, min_votes=3)
    assert [v.update(x) for x in ['happy', 'sad', 'angry', 'fear', 'happy']][-1] == NONE


def test_edge_tracker_fires_once_per_hold():
    e = EdgeTracker(required_consecutive=3, min_interval=0.0)
    fired = [e.process('happy', i * 0.1) for i in range(10)]
    assert fired.count('happy') == 1 and fired[2] == 'happy'


def test_edge_tracker_refires_after_change():
    e = EdgeTracker(required_consecutive=2, min_interval=0.0)
    seq = ['happy'] * 3 + ['sad'] * 3 + ['happy'] * 3
    fired = [f for i, x in enumerate(seq) if (f := e.process(x, i * 0.1))]
    assert fired == ['happy', 'sad', 'happy']


def test_edge_tracker_retrigger_while_held():
    e = EdgeTracker(required_consecutive=2, min_interval=0.0, retrigger_s=3.0)
    fired = [e.process('happy', i * 0.5) for i in range(14)]
    assert fired.count('happy') == 3        # at 0.5 s, 3.5 s and 6.5 s


def test_edge_tracker_min_interval_blocks_rapid_changes():
    e = EdgeTracker(required_consecutive=1, min_interval=1.0)
    assert e.process('happy', 0.0) == 'happy'
    assert e.process('sad', 0.2) is None
    assert e.process('sad', 1.5) == 'sad'


def test_none_resets_so_same_emotion_can_fire_again():
    e = EdgeTracker(required_consecutive=2, min_interval=0.0)
    seq = ['happy'] * 2 + [NONE] + ['happy'] * 2
    assert [f for i, x in enumerate(seq) if (f := e.process(x, i * 0.1))] == ['happy', 'happy']
