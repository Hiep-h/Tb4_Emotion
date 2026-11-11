"""Facial-expression backends (DeepFace or FER). Imported lazily: both pull in TensorFlow."""

from dataclasses import dataclass


@dataclass
class FaceResult:
    box: tuple    # (x, y, w, h) in pixels
    scores: dict  # raw emotion scores, any scale; see emotion_types.normalize_scores


def _largest(items, area):
    return max(items, key=area) if items else None


class DeepFaceBackend:

    def __init__(self, detector_backend='opencv'):
        try:
            from deepface import DeepFace
        except ImportError as exc:
            raise RuntimeError('Cài DeepFace: pip install deepface') from exc
        self._deepface = DeepFace
        self._detector = detector_backend

    def analyze(self, frame_bgr):
        try:
            results = self._deepface.analyze(
                frame_bgr, actions=['emotion'], enforce_detection=True,
                detector_backend=self._detector, silent=True)
        except ValueError:
            return None  # DeepFace raises ValueError when no face is found
        if isinstance(results, dict):
            results = [results]
        best = _largest(results, lambda r: r['region']['w'] * r['region']['h'])
        if best is None:
            return None
        region = best['region']
        return FaceResult((region['x'], region['y'], region['w'], region['h']),
                          best['emotion'])


class FerBackend:

    def __init__(self, **_):
        try:
            try:
                from fer.fer import FER   # fer >= 25
            except ImportError:
                from fer import FER       # older releases
        except ImportError as exc:
            raise RuntimeError('Cài FER: pip install fer') from exc
        self._detector = FER(mtcnn=False)

    def analyze(self, frame_bgr):
        results = self._detector.detect_emotions(frame_bgr)
        best = _largest(results, lambda r: r['box'][2] * r['box'][3])
        if best is None:
            return None
        return FaceResult(tuple(int(v) for v in best['box']), best['emotions'])


def make_backend(name, detector_backend='opencv'):
    if name == 'deepface':
        return DeepFaceBackend(detector_backend)
    if name == 'fer':
        return FerBackend()
    raise RuntimeError(f'Backend không hợp lệ: {name} (deepface | fer)')
