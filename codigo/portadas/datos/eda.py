"""Análisis exploratorio (sección 6): estadísticas de D1 y de los bocetos D2/D3.

De D1 salen los rangos de referencia para las métricas de paleta y de densidad de
la zona del título (Tabla de métricas): se usan percentiles, no valores fijos.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

from ..metricas.bordes import densidad_por_tercios
from ..metricas.color import colorido, estadisticas_hsv, paleta_dominante


class LectorTitulo:
    """Posición del texto en la portada con EasyOCR (opcional, en Colab con GPU)."""

    def __init__(self, idiomas=("en",), gpu: bool = True):
        import easyocr

        self.reader = easyocr.Reader(list(idiomas), gpu=gpu, verbose=False)

    def tercio_titulo(self, img: Image.Image) -> Optional[str]:
        a = np.asarray(img.convert("RGB"))
        h = a.shape[0]
        area = {"sup": 0.0, "med": 0.0, "inf": 0.0}
        for caja, _texto, conf in self.reader.readtext(a):
            if conf < 0.3:
                continue
            ys = [p[1] for p in caja]
            xs = [p[0] for p in caja]
            cy = (min(ys) + max(ys)) / 2
            superficie = (max(xs) - min(xs)) * (max(ys) - min(ys))
            area["sup" if cy < h / 3 else "med" if cy < 2 * h / 3 else "inf"] += superficie
        if sum(area.values()) == 0:
            return None
        return max(area, key=area.get)


def metricas_portada(img: Image.Image, con_paleta: bool = True) -> Dict:
    img = img.convert("RGB")
    if img.height > 768:
        img = img.resize((int(img.width * 768 / img.height), 768))
    fila = {"ancho": img.width, "alto": img.height, "proporcion": img.height / img.width,
            "colorido": colorido(img)}
    fila.update(estadisticas_hsv(img))
    fila.update(densidad_por_tercios(img))
    if con_paleta:
        fila["paleta"] = ";".join(c["hex"] for c in paleta_dominante(img, k=5))
    return fila


def analizar_d1(carpeta: Path, salida_csv: Path, lector: Optional[LectorTitulo] = None,
                limite: Optional[int] = None) -> List[Dict]:
    rutas = sorted(Path(carpeta).glob("*.jpg"))[:limite]
    filas = []
    for i, ruta in enumerate(rutas):
        try:
            img = Image.open(ruta)
            fila = {"archivo": ruta.name, **metricas_portada(img)}
            if lector is not None:
                fila["tercio_titulo"] = lector.tercio_titulo(img)
            filas.append(fila)
        except Exception as e:
            print(f"[EDA] se omite {ruta.name}: {e}")
        if (i + 1) % 200 == 0:
            print(f"[EDA] {i + 1}/{len(rutas)}")
    _escribir_csv(filas, salida_csv)
    return filas


def rangos_referencia(filas: List[Dict]) -> Dict:
    """Percentiles 25/50/75 de cada métrica numérica y distribución de la posición del título."""
    numericas = [k for k, v in filas[0].items() if isinstance(v, (int, float))]
    resumen = {"n": len(filas), "metricas": {}}
    for k in numericas:
        x = np.array([f[k] for f in filas], float)
        resumen["metricas"][k] = {"p25": float(np.percentile(x, 25)), "p50": float(np.median(x)),
                                  "p75": float(np.percentile(x, 75)), "media": float(x.mean())}
    if "tercio_titulo" in filas[0]:
        cuenta: Dict[str, int] = {}
        for f in filas:
            cuenta[str(f["tercio_titulo"])] = cuenta.get(str(f["tercio_titulo"]), 0) + 1
        resumen["tercio_titulo"] = {k: v / len(filas) for k, v in cuenta.items()}
    # Umbral de la métrica de legibilidad: densidad de bordes de la zona del título <= p75 de D1.
    tercio = "dens_sup"
    if resumen.get("tercio_titulo"):
        mas_comun = max((k for k in resumen["tercio_titulo"] if k != "None"),
                        key=lambda k: resumen["tercio_titulo"][k], default="sup")
        tercio = f"dens_{mas_comun}"
    resumen["umbral_densidad_titulo"] = resumen["metricas"][tercio]["p75"]
    return resumen


def analizar_bocetos(rutas: List[Path], salida_csv: Path) -> List[Dict]:
    """Proporción de tinta, tamaño del contenido y grosor de trazo (para fijar umbrales)."""
    import cv2

    filas = []
    for ruta in rutas:
        gris = np.asarray(Image.open(ruta).convert("L"))
        _, m = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        m = m > 0
        ys, xs = np.nonzero(m)
        caja = ((xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1)) / m.size if len(xs) else 0.0
        dist = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 3)
        grosor = float(2 * np.median(dist[m])) if m.any() else 0.0
        filas.append({"archivo": Path(ruta).name, "tinta": float(m.mean()),
                      "area_contenido": float(caja), "grosor_trazo_px": grosor})
    _escribir_csv(filas, salida_csv)
    return filas


def _escribir_csv(filas: List[Dict], ruta: Path) -> None:
    if not filas:
        return
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    campos = list(dict.fromkeys(k for f in filas for k in f))
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)


def guardar_resumen(resumen: Dict, ruta: Path) -> None:
    Path(ruta).write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
