"""Noise rejection for emotion labels (no ROS)."""

from collections import Counter, deque

from tb4_emotion_control.emotion_types import NONE


class MajorityVoter:
    """Reports a label only when it wins most of the last few votes."""

    def __init__(self, window=5, min_votes=3):
        self.min_votes = min_votes
        self._votes = deque(maxlen=window)

    def update(self, label):
        self._votes.append(label)
        if len(self._votes) < self._votes.maxlen:
            return NONE
        winner, count = Counter(self._votes).most_common(1)[0]
        return winner if count >= self.min_votes else NONE

    def reset(self):
        self._votes.clear()


class EdgeTracker:
    """Turns a continuous stream of labels into one-shot triggers.

    A label fires once it has been seen `required_consecutive` times in a row,
    and cannot fire again until the stream changes (or, if retrigger_s > 0,
    until that many seconds have passed while it is still held).
    """

    def __init__(self, required_consecutive=3, min_interval=0.5, retrigger_s=0.0):
        self.required_consecutive = required_consecutive
        self.min_interval = min_interval
        self.retrigger_s = retrigger_s
        self._last = NONE
        self._count = 0
        self._armed = None
        self._last_fire = -1e9

    def process(self, label, now):
        if label != self._last:
            self._last = label
            self._count = 1
        else:
            self._count += 1

        if label == NONE:
            self._armed = None
            return None
        if self._count < self.required_consecutive:
            return None
        if now - self._last_fire < self.min_interval:
            return None

        held_again = (label == self._armed and self.retrigger_s > 0
                      and now - self._last_fire >= self.retrigger_s)
        if label != self._armed or held_again:
            self._armed = label
            self._last_fire = now
            return label
        return None
