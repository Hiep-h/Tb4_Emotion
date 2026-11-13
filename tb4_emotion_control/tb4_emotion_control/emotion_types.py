"""Emotion vocabulary, topic names and score handling (no ROS, no ML libraries)."""

# The six states the assignment maps to robot actions. "disgust" is returned by
# both DeepFace and FER but has no action, so it is treated as "no decision".
EMOTIONS = ('happy', 'sad', 'neutral', 'angry', 'surprise', 'fear')
NONE = 'none'

DETECTED_EMOTION_TOPIC = '/detected_emotion'
CMD_VEL_TOPIC = '/cmd_vel'
ROBOT_STATE_TOPIC = '/emotion_robot_state'

KEY_EMOTION = 'emotion'
KEY_CONFIDENCE = 'confidence'
KEY_FACE = 'face'
KEY_STAMP = 'stamp'
KEY_ENABLED = 'enabled'
KEY_STOP_ID = 'stop_id'


def normalize_scores(scores):
    """Lowercase keys and scale to 0-1.

    DeepFace reports percentages (they sum to ~100); FER reports 0-1.
    """
    clean = {str(k).lower(): float(v) for k, v in scores.items()}
    if sum(clean.values()) > 1.5:
        clean = {k: v / 100.0 for k, v in clean.items()}
    return clean


def pick_emotion(scores):
    """Return (emotion, confidence) for the top score, or (NONE, 0.0)."""
    scores = normalize_scores(scores)
    if not scores:
        return NONE, 0.0
    best = max(scores, key=scores.get)
    if best not in EMOTIONS:
        return NONE, 0.0
    return best, scores[best]


def face_is_large_enough(box, frame_width, min_ratio):
    """True if the face is wide enough to be the person at the camera, not someone behind them.

    A person at 0.5-1 m is ~25-35% of the frame width; classmates in the background are ~5-10%.
    """
    return box[2] >= min_ratio * frame_width
