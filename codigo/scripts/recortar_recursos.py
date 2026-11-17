"""Recorta los recursos gráficos de FROG a partir de la hoja `assets/recursos_visuales.png`.

Genera un PNG con fondo transparente por cada elemento en `app/assets/<categoría>/`.
Para cada uno se parte de una caja sobre la hoja que deja fuera las etiquetas de texto que
la acompañan (eso lo garantizan las cajas, no un filtro). Dentro de la caja se descartan los
píxeles casi transparentes (la hoja trae ruido de alfa 1-30 que dejaría halos de color sobre
otros fondos) y las motas diminutas, y se ajusta el recorte al contenido. Las piezas sueltas
legítimas, como los rayos del sol de la ranita, se conservan.

Uso (desde la carpeta `codigo`):
    python -m scripts.recortar_recursos
    python -m scripts.recortar_recursos --hoja "../assets/recursos_visuales.png" --muestra salida/contacto.png
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Tuple

import cv2
import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
HOJA = RAIZ.parent / "assets" / "recursos_visuales.png"
SALIDA = RAIZ / "app" / "assets"
ALFA_MIN = 40            # por debajo, el píxel se considera ruido y queda transparente
AREA_MIN = 60            # motas más pequeñas que esto (en píxeles) se descartan
MARGEN = 3               # píxeles transparentes que se dejan alrededor del recorte

Caja = Tuple[int, int, int, int]       # x0, y0, x1, y1 sobre la hoja de 1672 x 941

# categoría -> nombre -> caja aproximada (sin las etiquetas de texto que van debajo de cada recurso)
RECURSOS: Dict[str, Dict[str, Caja]] = {
    "mascotas": {
        "frog_hero": (40, 18, 402, 380),          # portada / inicio
        "frog_analiza": (430, 66, 736, 326),      # analizando la historia (lupa)
        "frog_idea": (740, 18, 1064, 332),        # definiendo parámetros (globo de ideas)
        "frog_generando": (1056, 74, 1358, 316),  # generando propuestas (saltando)
        "frog_resumen": (1390, 94, 1650, 326),    # resumen final (lista de verificación)
    },
    "fondos": {
        "fondo_bosque": (6, 452, 498, 594),       # decorativo inferior
        "textura_papel": (536, 474, 780, 572),    # interior opaco: las esquinas redondeadas de la hoja quedan fuera
    },
    "escenas": {
        "escena_noche": (816, 448, 1084, 592),
        "escena_dia": (1104, 442, 1358, 592),
        "escena_bosque": (1378, 436, 1658, 592),
    },
    "iconos": {
        "ico_estilo": (26, 660, 142, 754),
        "ico_colores": (190, 662, 310, 748),
        "ico_ilustracion": (336, 664, 478, 748),
        "ico_composicion": (512, 666, 614, 748),
        "ico_tipografia": (656, 666, 772, 748),
        "ico_ambiente": (802, 656, 904, 750),
        "ico_check": (990, 686, 1060, 750),
        "ico_x": (1102, 690, 1170, 754),
        "ico_bloqueo": (1222, 680, 1284, 750),
        "ico_alerta": (1340, 684, 1412, 750),
        "ico_info": (1456, 684, 1528, 750),
        "ico_brillo": (1568, 678, 1642, 748),
    },
    "decoraciones": {
        "deco_rayitas": (38, 832, 166, 912),
        "deco_destellos": (238, 826, 348, 922),
        "deco_espiral": (382, 842, 554, 914),
        "deco_estrellas": (602, 826, 774, 920),
        "deco_nube": (816, 830, 1062, 922),
        "deco_hierbas": (1108, 838, 1316, 912),
        "deco_libros": (1360, 810, 1658, 924),
    },
}
# Recursos opacos por naturaleza (rectángulos con fondo propio): no se recortan por contenido.
SIN_AJUSTE = {"textura_papel"}


def recortar(hoja: np.ndarray, caja: Caja, ajustar: bool = True) -> Image.Image:
    x0, y0, x1, y1 = caja
    zona = hoja[y0:y1, x0:x1].copy()
    zona[..., 3] = np.where(zona[..., 3] < ALFA_MIN, 0, zona[..., 3])
    if not ajustar:
        zona[..., :3] = np.where(zona[..., 3:4] == 0, 0, zona[..., :3])
        return Image.fromarray(zona, "RGBA")
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats((zona[..., 3] > 0).astype(np.uint8), connectivity=8)
    conservar = np.zeros(zona.shape[:2], bool)
    for k in range(1, n):
        if stats[k, cv2.CC_STAT_AREA] >= AREA_MIN:
            conservar |= etiquetas == k
    if not conservar.any():
        raise ValueError(f"no hay contenido en la caja {caja}")
    zona[~conservar] = 0
    filas, cols = np.where(conservar)
    zona = zona[max(filas.min() - MARGEN, 0): filas.max() + MARGEN + 1,
                max(cols.min() - MARGEN, 0): cols.max() + MARGEN + 1]
    zona[..., :3] = np.where(zona[..., 3:4] == 0, 0, zona[..., :3])      # sin color oculto bajo lo transparente
    return Image.fromarray(zona, "RGBA")


def muestra(piezas: Dict[str, Image.Image], ruta: Path) -> None:
    """Hoja de contacto sobre crema y sobre blanco para revisar los recortes a simple vista."""
    ancho, fila_alto, x, y, fila_max = 1500, 0, 10, 10, 0
    lienzo = Image.new("RGB", (ancho, 1400), (255, 247, 227))
    for nombre, im in piezas.items():
        w, h = im.size
        escala = min(1, 220 / max(w, h))
        im2 = im.resize((max(1, int(w * escala)), max(1, int(h * escala))))
        if x + im2.width + 10 > ancho:
            x, y, fila_max = 10, y + fila_max + 14, 0
        lienzo.paste(im2, (x, y), im2)
        x += im2.width + 14
        fila_max = max(fila_max, im2.height)
    lienzo.crop((0, 0, ancho, y + fila_max + 14)).save(ruta)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hoja", default=str(HOJA))
    ap.add_argument("--salida", default=str(SALIDA))
    ap.add_argument("--muestra", default=None, help="guarda una hoja de contacto para revisar los recortes")
    args = ap.parse_args()

    hoja = np.asarray(Image.open(args.hoja).convert("RGBA")).copy()
    piezas: Dict[str, Image.Image] = {}
    for categoria, recursos in RECURSOS.items():
        carpeta = Path(args.salida) / categoria
        carpeta.mkdir(parents=True, exist_ok=True)
        for nombre, caja in recursos.items():
            im = recortar(hoja, caja, ajustar=nombre not in SIN_AJUSTE)
            im.save(carpeta / f"{nombre}.png", optimize=True)
            # Versión WebP para incrustar en la página: pesa ~4 veces menos y se lee sin codificar.
            im.save(carpeta / f"{nombre}.webp", quality=90, alpha_quality=100, method=6)
            piezas[nombre] = im
            print(f"{categoria}/{nombre}.png  {im.size[0]}x{im.size[1]}")
    if args.muestra:
        muestra(piezas, Path(args.muestra))


if __name__ == "__main__":
    main()
