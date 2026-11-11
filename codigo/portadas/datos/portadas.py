"""D1: portadas de la categoría Children's Books del Book Cover Dataset (Iwana et al., 2016).

Las portadas tienen derechos de autor (sección 6.1). Se descargan solo para el
análisis exploratorio y como referencia del KID/FID: no se muestran, no se
redistribuyen (la carpeta está en .gitignore) y no se usan para entrenar.
"""
from __future__ import annotations

import csv
import io
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List

from PIL import Image

from .. import config

COLUMNAS = ["asin", "archivo", "url", "titulo", "autor", "categoria_id", "categoria"]


def leer_listado(texto: str) -> List[Dict[str, str]]:
    filas = csv.reader(io.StringIO(texto))
    return [dict(zip(COLUMNAS, f)) for f in filas if len(f) == len(COLUMNAS)]


def descargar_listado(sesion=None) -> str:
    import requests

    sesion = sesion or requests.Session()
    r = sesion.get(config.BOOK32_URL, timeout=120)
    r.raise_for_status()
    # El CSV no es UTF-8 puro: se decodifica en latin-1 para no perder filas.
    return r.content.decode("latin-1")


def muestrear_infantiles(filas: List[Dict[str, str]], n: int = 2000,
                         semilla: int = config.SEMILLA_GLOBAL) -> List[Dict[str, str]]:
    infantiles = [f for f in filas if f["categoria_id"] == config.BOOK32_CATEGORIA_INFANTIL]
    random.Random(semilla).shuffle(infantiles)
    return infantiles[:n]


def url_actual(url: str) -> str:
    """Los enlaces de 2016 (http://ecx.images-amazon.com) responden muy lento; el mismo
    identificador de imagen sirve en el CDN actual de Amazon por HTTPS."""
    return url.replace("http://ecx.images-amazon.com/", "https://m.media-amazon.com/")


def _bajar_una(sesion, fila: Dict[str, str], carpeta: Path) -> bool:
    ruta = carpeta / fila["archivo"]
    if ruta.exists():
        return True
    try:
        r = sesion.get(url_actual(fila["url"]), timeout=30)
        if r.status_code != 200 or len(r.content) < 1000:
            return False
        Image.open(io.BytesIO(r.content)).convert("RGB").save(ruta, quality=95)
        return True
    except Exception:
        return False


def preparar_d1(destino: Path = config.DATOS / "d1_portadas", n: int = 2000, hilos: int = 8) -> Dict:
    import requests

    destino = Path(destino)
    (destino / "img").mkdir(parents=True, exist_ok=True)
    sesion = requests.Session()
    filas = leer_listado(descargar_listado(sesion))
    total_infantiles = sum(f["categoria_id"] == config.BOOK32_CATEGORIA_INFANTIL for f in filas)
    muestra = muestrear_infantiles(filas, n)
    with ThreadPoolExecutor(hilos) as ex:
        ok = list(ex.map(lambda f: _bajar_una(sesion, f, destino / "img"), muestra))
    bajadas = [f for f, b in zip(muestra, ok) if b]
    with open(destino / "muestra.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(bajadas)
    (destino / "NO_REDISTRIBUIR.txt").write_text(
        "Portadas con derechos de autor (Amazon.com, Inc. y titulares). Uso exclusivo para "
        "estadísticas del proyecto académico. No compartir, no publicar, no entrenar.\n",
        encoding="utf-8")
    resumen = {"listado_total": len(filas), "infantiles_total": total_infantiles,
               "muestra_pedida": len(muestra), "descargadas": len(bajadas)}
    print(f"[D1] {resumen}")
    return resumen
