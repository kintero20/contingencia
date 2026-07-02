import os
import logging
import threading
from typing import Optional, List
import numpy as np

logger = logging.getLogger(__name__)

_face_model = None
_face_detector = None
_cv2_available = False
_model_loading = False


def load_model():
    global _face_model, _face_detector, _model_loading
    if _model_loading:
        return
    _model_loading = True
    try:
        import insightface
        from insightface.app import FaceAnalysis

        buf_path = os.path.expanduser("~/.insightface/models/buffalo_l")
        if not os.path.exists(buf_path) or not any(fname.endswith(".onnx") for fname in os.listdir(buf_path)):
            logger.info("Modelos de InsightFace no encontrados, descargando en segundo plano...")
            t = threading.Thread(target=_download_and_load, daemon=True)
            t.start()
            return

        _init_face_models(insightface, FaceAnalysis)
    except ImportError:
        logger.warning("insightface no instalado, funciones faciales no disponibles")
    except Exception as e:
        logger.error(f"Error al cargar modelo facial: {e}")
    finally:
        _model_loading = False


def _download_and_load():
    global _face_model, _face_detector, _model_loading
    try:
        import insightface
        from insightface.app import FaceAnalysis
        _init_face_models(insightface, FaceAnalysis)
    except Exception as e:
        logger.error(f"Error descargando/cargando modelo facial: {e}")
    finally:
        _model_loading = False


def _init_face_models(insightface, FaceAnalysis):
    global _face_model, _face_detector
    _face_detector = FaceAnalysis(
        providers=["CPUExecutionProvider"],
        allowed_modules=["detection", "recognition"],
    )
    _face_detector.prepare(ctx_id=-1, det_size=(640, 640))
    _face_model = _face_detector.models["recognition"]
    logger.info("InsightFace model loaded successfully")


def is_model_loaded() -> bool:
    return _face_model is not None and _face_detector is not None


def _ensure_cv2():
    global _cv2_available
    if not _cv2_available:
        try:
            import cv2
            globals()["cv2"] = cv2
            _cv2_available = True
        except ImportError:
            logger.warning("opencv-python-headless no está instalado, funciones faciales no disponibles")
            _cv2_available = False
    return _cv2_available


def _can_extract() -> bool:
    if not _ensure_cv2():
        return False
    if not is_model_loaded():
        load_model()
    if not is_model_loaded():
        return False
    return True


def extract_embedding(image_path: str) -> Optional[list]:
    if not _can_extract():
        return None

    try:
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Could not read image: {image_path}")
            return None

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        faces = _face_detector.get(img_rgb)

        if not faces:
            logger.warning(f"No face detected in: {image_path}")
            return None

        face = faces[0]
        embedding = face.embedding

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error extracting embedding: {e}")
        return None


def extract_embedding_from_bytes(image_bytes: bytes) -> Optional[list]:
    if not _can_extract():
        return None

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            logger.error("Could not decode image bytes")
            return None

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        faces = _face_detector.get(img_rgb)

        if not faces:
            logger.warning("No face detected in uploaded image")
            return None

        face = faces[0]
        embedding = face.embedding

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error extracting embedding from bytes: {e}")
        return None
