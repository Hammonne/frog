"""D2: bocetos de Quick, Draw! (CC BY 4.0, Google Creative Lab).

Los archivos `simplified/*.ndjson` tienen trazos en coordenadas 0-255. Se leen en
streaming y se corta en cuanto hay suficientes dibujos reconocidos, para no bajar
los ~100 MB de cada categoría.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, Iterable, List

import cv2
import numpy as np
from PIL import Image

from .. import config


def renderizar(trazos: List[List[List[int]]], lado: int = 512, grosor: int = 6,
               margen: int = 16) -> Image.Image:
    """Dibuja los trazos en negro sobre blanco, escalados al lienzo."""
    xs = np.concatenate([np.asarray(t[0], float) for t in trazos])
    ys = np.concatenate([np.asarray(t[1], float) for t in trazos])
    ancho, alto = max(xs.max() - xs.min(), 1), max(ys.max() - ys.min(), 1)
    escala = (lado - 2 * margen) / max(ancho, alto)
    ox = margen + ((lado - 2 * margen) - ancho * escala) / 2 - xs.min() * escala
    oy = margen + ((lado - 2 * margen) - alto * escala) / 2 - ys.min() * escala
    lienzo = np.full((lado, lado), 255, np.uint8)
    for x, y in trazos:
        pts = np.stack([np.asarray(x) * escala + ox, np.asarray(y) * escala + oy], 1)
        cv2.polylines(lienzo, [pts.round().astype(np.int32)], False, 0, grosor, cv2.LINE_AA)
    return Image.fromarray(lienzo)


def leer_lineas(lineas: Iterable[str], n: int, pool: int = 300, semilla: int = config.SEMILLA_GLOBAL) -> List[Dict]:
    """Toma los primeros `pool` dibujos reconocidos y elige `n` al azar (reproducible)."""
    candidatos = []
    for linea in lineas:
        if not linea:
            continue
        d = json.loads(linea)
        if d.get("recognized"):
            candidatos.append(d)
        if len(candidatos) >= pool:
            break
    random.Random(semilla).shuffle(candidatos)
    return candidatos[:n]


def descargar_categoria(categoria: str, n: int = 20, pool: int = 300, sesion=None) -> List[Dict]:
    import requests

    sesion = sesion or requests.Session()
    url = config.QUICKDRAW_URL.format(categoria=categoria.replace(" ", "%20"))
    with sesion.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        lineas = (l.decode("utf-8") for l in r.iter_lines())
        return leer_lineas(lineas, n=n, pool=pool)


def preparar_d2(destino: Path = config.DATOS / "d2_quickdraw", n_por_categoria: int = 20,
                categorias: List[str] = config.QUICKDRAW_CATEGORIAS) -> Path:
    destino = Path(destino)
    (destino / "png").mkdir(parents=True, exist_ok=True)
    indice = []
    for cat in categorias:
        dibujos = descargar_categoria(cat, n=n_por_categoria)
        for i, d in enumerate(dibujos):
            nombre = f"{cat}_{i:02d}.png"
            renderizar(d["drawing"]).save(destino / "png" / nombre)
            indice.append({"archivo": f"png/{nombre}", "categoria": cat, "key_id": d["key_id"],
                           "countrycode": d.get("countrycode")})
        print(f"[D2] {cat}: {len(dibujos)} bocetos")
    (destino / "indice.json").write_text(json.dumps(indice, indent=1), encoding="utf-8")
    (destino / "ATRIBUCION.txt").write_text(
        "Dibujos de The Quick, Draw! Dataset, Google Creative Lab, bajo licencia CC BY 4.0.\n"
        "https://github.com/googlecreativelab/quickdraw-dataset\n", encoding="utf-8")
    return destino
