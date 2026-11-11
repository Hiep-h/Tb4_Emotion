"""Emotion vocabulary, topic names and score handling (no ROS, no ML libraries)."""

# The six states the assignment maps to robot actions. "disgust" is returned by
# both DeepFace and FER but has no action, so it is treated as "no decision".
EMOTIONS = ('happy', 'sad', 'neutral', 'angry', 'surprise', 'fear')
NONE = 'none'

DETECTED_EMOTION_TOPIC = '/detected_emotion'
CMD_VEL_TOPIC = '/cmd_vel'

KEY_EMOTION = 'emotion'
KEY_CONFIDENCE = 'confidence'
KEY_FACE = 'face'
KEY_STAMP = 'stamp'


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
