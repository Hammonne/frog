"""Métricas de color: colorido (Hasler y Süsstrunk, 2003), estadísticas HSV,
paleta dominante y adherencia a la paleta pedida (P2)."""
from __future__ import annotations

from typing import Dict, List, Optional

import cv2
import numpy as np
from PIL import Image


def _rgb(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGB"), dtype=np.float64)


def colorido(img: Image.Image) -> float:
    """M = sigma_rgyb + 0.3 * mu_rgyb (Hasler y Süsstrunk, 2003)."""
    a = _rgb(img)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    rg = r - g
    yb = 0.5 * (r + g) - b
    sigma = np.sqrt(rg.std() ** 2 + yb.std() ** 2)
    mu = np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    return float(sigma + 0.3 * mu)


def estadisticas_hsv(img: Image.Image) -> Dict[str, float]:
    hsv = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2HSV).astype(np.float64)
    h = hsv[..., 0] * 2.0          # OpenCV guarda el tono en 0-179 -> grados
    s = hsv[..., 1] / 255.0
    v = hsv[..., 2] / 255.0
    coloreados = s > 0.15          # el tono no tiene sentido en grises
    return {
        "brillo": float(v.mean()),
        "saturacion": float(s.mean()),
        "frac_coloreada": float(coloreados.mean()),
        "frac_calida": float(_frac_tono(h, coloreados, [(0, 50), (330, 360)])),
        "frac_fria": float(_frac_tono(h, coloreados, [(170, 260)])),
        "frac_tierra": float(_frac_tono(h, coloreados & (s < 0.65) & (v < 0.75), [(15, 45)])),
    }


def _frac_tono(h: np.ndarray, mascara: np.ndarray, rangos) -> float:
    n = mascara.sum()
    if n == 0:
        return 0.0
    dentro = np.zeros_like(mascara)
    for lo, hi in rangos:
        dentro |= (h >= lo) & (h < hi)
    return float((dentro & mascara).sum() / n)


def paleta_dominante(img: Image.Image, k: int = 5, muestras: int = 20000,
                     semilla: int = 0) -> List[Dict]:
    """k-means en CIELAB. Devuelve colores en hex con su proporción, ordenados."""
    from sklearn.cluster import KMeans

    rgb = np.asarray(img.convert("RGB"))
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float64)
    rng = np.random.default_rng(semilla)
    if len(lab) > muestras:
        lab = lab[rng.choice(len(lab), muestras, replace=False)]
    km = KMeans(n_clusters=k, n_init=4, random_state=semilla).fit(lab)
    proporciones = np.bincount(km.labels_, minlength=k) / len(lab)
    centros = km.cluster_centers_.clip(0, 255).astype(np.uint8).reshape(1, -1, 3)
    centros_rgb = cv2.cvtColor(centros, cv2.COLOR_LAB2RGB).reshape(-1, 3)
    salida = [
        {"hex": "#%02x%02x%02x" % tuple(int(c) for c in rgb_c), "proporcion": float(p)}
        for rgb_c, p in zip(centros_rgb, proporciones)
    ]
    return sorted(salida, key=lambda d: -d["proporcion"])


# Criterios por paleta, fijados con los percentiles de D1 (2 000 portadas infantiles,
# salidas/eda/resumen_d1.json). Regla: una portada "tiene" la paleta si está en el cuartil
# más característico de las portadas reales para ese rasgo (p75 o p25), o, en pastel, si es
# más clara y menos saturada que la portada mediana. Cada criterio abarca 18-29 % de D1
# (pastel 29 %, cálida 25 %, fría 25 %, primarios 18 %, tierra 25 %).
#   saturación  p25 0.282 · p50 0.392 · p75 0.513     brillo      p25 0.578 · p50 0.700
#   frac_calida p75 0.679 · frac_fria p75 0.445 · frac_tierra p75 0.357
CRITERIOS_PALETA = {
    "pastel": lambda e: e["saturacion"] <= 0.392 and e["brillo"] >= 0.700,   # < p50 sat., > p50 brillo
    "calida": lambda e: e["frac_calida"] >= 0.679,                           # >= p75
    "fria": lambda e: e["frac_fria"] >= 0.445,                               # >= p75
    "primarios": lambda e: e["saturacion"] >= 0.513 and e["brillo"] >= 0.578,  # >= p75 sat., no oscura
    "tierra": lambda e: e["frac_tierra"] >= 0.357,                           # >= p75
}


def adherencia_paleta(img: Image.Image, paleta: str,
                      criterios: Optional[Dict] = None) -> bool:
    criterios = criterios or CRITERIOS_PALETA
    return bool(criterios[paleta](estadisticas_hsv(img)))
