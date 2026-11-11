"""Fidelidad al boceto (F1 de bordes con tolerancia) y densidad de bordes por zona."""
from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

import cv2
import numpy as np
from PIL import Image


def bordes(img: Image.Image, detector: Optional[Callable[[Image.Image], Image.Image]] = None) -> np.ndarray:
    """Máscara de bordes. En Colab se pasa HED (controlnet_aux); sin él se usa Canny."""
    if detector is not None:
        e = np.asarray(detector(img.convert("RGB")).convert("L").resize(img.size))
        _, m = cv2.threshold(e, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return m > 0
    gris = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    gris = cv2.GaussianBlur(gris, (5, 5), 0)
    return cv2.Canny(gris, 50, 150) > 0


def f1_bordes(lineas_boceto: Image.Image, salida: Image.Image, tolerancia: int = 3,
              detector: Optional[Callable] = None) -> Dict[str, float]:
    """Precisión: bordes de la salida que caen cerca del boceto.
    Exhaustividad (recall): trazo del boceto que la salida respeta.
    `lineas_boceto` es negro sobre blanco (Boceto.lineas). Se comparan bordes con
    bordes, con el mismo detector en ambas imágenes, para que el grosor del trazo
    no penalice."""
    boceto = bordes(lineas_boceto.convert("RGB").resize(salida.size), detector)
    salida_b = bordes(salida, detector)
    if boceto.sum() == 0 or salida_b.sum() == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    dist_a_boceto = cv2.distanceTransform((~boceto).astype(np.uint8), cv2.DIST_L2, 3)
    dist_a_salida = cv2.distanceTransform((~salida_b).astype(np.uint8), cv2.DIST_L2, 3)
    precision = float((dist_a_boceto[salida_b] <= tolerancia).mean())
    recall = float((dist_a_salida[boceto] <= tolerancia).mean())
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": float(f1)}


def franja(zona: str, alto: int, reservas: Dict[str, Tuple[float, float]]) -> Tuple[int, int]:
    arriba, abajo = reservas[zona]
    if arriba > 0:
        return 0, int(alto * arriba)
    if abajo > 0:
        return int(alto * (1 - abajo)), alto
    return 0, 0


def densidad_bordes(img: Image.Image, y0: int = 0, y1: Optional[int] = None) -> float:
    """Fracción de píxeles de borde en la franja [y0, y1). Mide si el modelo dejó
    libre el espacio pedido para el título."""
    m = bordes(img)
    y1 = m.shape[0] if y1 is None else y1
    if y1 <= y0:
        return 0.0
    return float(m[y0:y1].mean())


def densidad_por_tercios(img: Image.Image) -> Dict[str, float]:
    m = bordes(img)
    h = m.shape[0]
    return {
        "dens_sup": float(m[: h // 3].mean()),
        "dens_med": float(m[h // 3: 2 * h // 3].mean()),
        "dens_inf": float(m[2 * h // 3:].mean()),
        "dens_total": float(m.mean()),
    }
