"""Guardrails de la imagen de entrada: no se procesan fotografías de personas reales.

Se usa MediaPipe si está instalado y, si no, el clasificador Haar de OpenCV.
Solo se aplica a entradas clasificadas como "foto": en bocetos limpios, una cara
dibujada es parte legítima del dibujo y el detector daría falsos positivos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from ..preprocesamiento import tipo_de_entrada


@dataclass
class ResultadoEntrada:
    ok: bool
    motivo: str = ""
    rostros: int = 0
    detector: str = ""


def _rostros_mediapipe(rgb: np.ndarray) -> Optional[int]:
    try:
        import mediapipe as mp  # type: ignore
    except Exception:
        return None
    try:
        with mp.solutions.face_detection.FaceDetection(model_selection=1,
                                                       min_detection_confidence=0.6) as det:
            res = det.process(rgb)
        return len(res.detections or [])
    except Exception:
        return None


def _rostros_haar(rgb: np.ndarray) -> int:
    gris = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    ruta = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    clasificador = cv2.CascadeClassifier(ruta)
    lado = max(40, min(gris.shape) // 10)
    caras = clasificador.detectMultiScale(gris, scaleFactor=1.1, minNeighbors=6, minSize=(lado, lado))
    return len(caras)


def revisar_imagen_entrada(img: Image.Image) -> ResultadoEntrada:
    rgb = np.array(img.convert("RGB"))
    gris = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    if tipo_de_entrada(gris) != "foto":
        return ResultadoEntrada(ok=True, detector="no aplica (boceto)")
    n = _rostros_mediapipe(rgb)
    detector = "mediapipe"
    if n is None:
        n, detector = _rostros_haar(rgb), "haar"
    if n > 0:
        return ResultadoEntrada(
            ok=False,
            motivo="La imagen parece una fotografía de una persona. El sistema solo trabaja con dibujos.",
            rostros=n,
            detector=detector,
        )
    return ResultadoEntrada(ok=True, rostros=0, detector=detector)
