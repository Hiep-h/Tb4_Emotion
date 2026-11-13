"""Facial-expression backends: ONNX FER+ (default, light), DeepFace or FER (both need TensorFlow).

Heavy libraries are imported lazily so the pure logic stays testable without them.
"""

import os
from dataclasses import dataclass

import numpy as np


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


MODEL_DIR = os.path.expanduser('~/.tb4_emotion')
FERPLUS_FILE = 'emotion-ferplus-8.onnx'
FERPLUS_URL = ('https://media.githubusercontent.com/media/onnx/models/main/validated/vision/'
               'body_analysis/emotion_ferplus/model/' + FERPLUS_FILE)
FERPLUS_SHA256 = 'a2a2ba6a335a3b29c21acb6272f962bd3d47f84952aaffa03b60986e04efa61c'
YUNET_FILE = 'face_detection_yunet_2023mar.onnx'
YUNET_URL = ('https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/'
             'face_detection_yunet/' + YUNET_FILE)
YUNET_SHA256 = '8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4'
# Output order of the FER+ network (ONNX model zoo), mapped to this package's names.
FERPLUS_LABELS = ('neutral', 'happy', 'surprise', 'sad', 'angry', 'disgust', 'fear', 'contempt')


def softmax(logits):
    e = np.exp(logits - np.max(logits))
    return e / e.sum()


def ferplus_scores(logits):
    """Raw FER+ logits -> {label: probability}."""
    return {label: float(p) for label, p in zip(FERPLUS_LABELS, softmax(np.asarray(logits)))}


def crop_face(gray, box, margin=0.1):
    """64x64 float32 input for FER+: the face box widened by `margin`, raw 0-255 pixels."""
    import cv2
    x, y, w, h = box
    m = int(margin * w)
    height, width = gray.shape
    crop = gray[max(0, y - m):min(height, y + h + m), max(0, x - m):min(width, x + w + m)]
    return cv2.resize(crop, (64, 64)).astype(np.float32).reshape(1, 1, 64, 64)


def largest_face(faces, frame_shape):
    """Rows [x, y, w, h, ..., score] from YuNet -> the largest face as (x, y, w, h), clamped."""
    if faces is None or len(faces) == 0:
        return None
    row = max(faces, key=lambda r: r[2] * r[3])
    height, width = frame_shape[:2]
    x, y = max(0, int(row[0])), max(0, int(row[1]))
    w, h = min(int(row[2]), width - x), min(int(row[3]), height - y)
    return (x, y, w, h) if w > 0 and h > 0 else None


class OnnxBackend:
    """Light: YuNet (OpenCV, 0.2 MB) finds faces, FER+ (ONNX, 35 MB) classifies 8 expressions.

    YuNet finds close, tilted and talking faces that the old Haar cascade missed, and needs only
    onnxruntime and OpenCV >= 4.8; no TensorFlow.
    """

    def __init__(self, model_path='', detector_path='', score_threshold=0.7):
        import cv2
        import onnxruntime as ort
        model_path = model_path or os.path.join(MODEL_DIR, FERPLUS_FILE)
        detector_path = detector_path or os.path.join(MODEL_DIR, YUNET_FILE)
        for path in (model_path, detector_path):
            if not os.path.isfile(path):
                raise FileNotFoundError(f'Thiếu file {path}. Tải bằng: bash scripts/download_models.sh')
        if not hasattr(cv2, 'FaceDetectorYN'):
            raise RuntimeError('OpenCV quá cũ, cần >= 4.8 (khuyên dùng opencv-contrib-python==4.11.0.86)')
        self._session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        self._input = self._session.get_inputs()[0].name
        self._cv2 = cv2
        self._detector = cv2.FaceDetectorYN.create(detector_path, '', (320, 320),
                                                   score_threshold, 0.3, 5000)

    def analyze(self, frame_bgr):
        cv2 = self._cv2
        height, width = frame_bgr.shape[:2]
        self._detector.setInputSize((width, height))
        _, faces = self._detector.detect(frame_bgr)
        box = largest_face(faces, frame_bgr.shape)
        if box is None:
            return None
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        logits = self._session.run(None, {self._input: crop_face(gray, box)})[0][0]
        return FaceResult(box, ferplus_scores(logits))


def make_backend(name, detector_backend='opencv', model_path=''):
    if name == 'onnx':
        return OnnxBackend(model_path)
    if name == 'deepface':
        return DeepFaceBackend(detector_backend)
    if name == 'fer':
        return FerBackend()
    raise RuntimeError(f'Backend không hợp lệ: {name} (onnx | deepface | fer)')
