"""Preprocesamiento de la entrada (sección 6 del informe).

Pasos: (1) EXIF fuera y escala de grises; (2) líneas por Otsu (bocetos limpios) o
umbral adaptativo / HED (fotos de dibujos); (3) validación de tinta; (4) recorte al
contenido y ubicación en un lienzo 2:3 dejando libre la zona del título;
(5) 512x768. Devuelve las líneas en dos polaridades:
- `lineas`: trazo negro sobre blanco (API de Stability, métricas).
- `control`: trazo blanco sobre negro (ControlNet scribble/lineart).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

from . import config


class BocetoInvalido(ValueError):
    """La entrada no sirve como boceto (vacía, saturada o ilegible)."""


@dataclass
class Boceto:
    lineas: Image.Image           # L, negro sobre blanco, ANCHO x ALTO
    control: Image.Image          # RGB, blanco sobre negro, ANCHO x ALTO
    tipo: str                     # "boceto" | "foto"
    tinta: float                  # fracción de píxeles con trazo (antes de ubicar)
    color_original: Optional[Image.Image] = None  # RGB en el lienzo, para modo img2img
    info: dict = field(default_factory=dict)


def limpiar_metadatos(img: Image.Image) -> Image.Image:
    """Aplica la orientación EXIF y devuelve una copia sin metadatos."""
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("L", "RGB", "RGBA", "LA"):
        img = img.convert("RGBA")
    # Reconstruir desde los píxeles descarta EXIF, GPS y cualquier otro metadato.
    return Image.fromarray(np.array(img))


def reducir(img: Image.Image, lado_max: int = 1536) -> Image.Image:
    if max(img.size) <= lado_max:
        return img
    img = img.copy()
    img.thumbnail((lado_max, lado_max), Image.LANCZOS)
    return img


def tipo_de_entrada(gris: np.ndarray) -> str:
    """Heurística: un boceto limpio es casi bimodal (papel y trazo); una foto de un
    dibujo tiene muchos tonos intermedios por la iluminación y la textura del papel."""
    intermedios = np.mean((gris > 60) & (gris < 200))
    return "foto" if intermedios > 0.30 else "boceto"


def extraer_lineas(gris: np.ndarray, tipo: str,
                   detector_hed: Optional[Callable[[Image.Image], Image.Image]] = None) -> np.ndarray:
    """Devuelve una máscara booleana con True donde hay trazo."""
    if tipo == "foto" and detector_hed is not None:
        bordes = np.array(detector_hed(Image.fromarray(gris).convert("RGB")).convert("L"))
        bordes = cv2.resize(bordes, (gris.shape[1], gris.shape[0]))
        _, mascara = cv2.threshold(bordes, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return mascara > 0
    suave = cv2.GaussianBlur(gris, (3, 3), 0)
    if tipo == "foto":
        lado = max(15, (min(gris.shape) // 30) | 1)
        mascara = cv2.adaptiveThreshold(suave, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY_INV, lado, 10)
    else:
        _, mascara = cv2.threshold(suave, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return mascara > 0


def quitar_ruido(mascara: np.ndarray, area_min: int = 20) -> np.ndarray:
    m = mascara.astype(np.uint8)
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    limpia = np.zeros_like(m)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= area_min:
            limpia[etiquetas == i] = 1
    return limpia.astype(bool)


def validar_tinta(mascara: np.ndarray) -> float:
    tinta = float(mascara.mean())
    if tinta < config.TINTA_MIN:
        raise BocetoInvalido(f"El boceto parece vacío (tinta {tinta:.2%} < {config.TINTA_MIN:.1%}).")
    if tinta > config.TINTA_MAX:
        raise BocetoInvalido(f"El boceto está demasiado lleno (tinta {tinta:.1%} > {config.TINTA_MAX:.0%}).")
    return tinta


def region_libre(zona_titulo: str, tam: Tuple[int, int] = (config.ANCHO, config.ALTO),
                 margen: float = 0.06) -> Tuple[int, int, int, int]:
    """Caja (x0, y0, x1, y1) donde se puede ubicar el dibujo sin invadir la zona del título."""
    ancho, alto = tam
    arriba, abajo = config.ZONAS_TITULO[zona_titulo]["reserva"]
    mx, my = int(ancho * margen), int(alto * margen)
    y0 = max(my, int(alto * arriba))
    y1 = min(alto - my, int(alto * (1 - abajo)))
    return mx, y0, ancho - mx, y1


def ubicar_en_lienzo(mascara: np.ndarray, zona_titulo: str,
                     tam: Tuple[int, int] = (config.ANCHO, config.ALTO),
                     color: Optional[np.ndarray] = None):
    """Recorta al contenido y lo escala para que quepa en la región libre, centrado."""
    ys, xs = np.nonzero(mascara)
    y_a, y_b, x_a, x_b = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    recorte = mascara[y_a:y_b, x_a:x_b].astype(np.uint8) * 255
    x0, y0, x1, y1 = region_libre(zona_titulo, tam)
    escala = min((x1 - x0) / recorte.shape[1], (y1 - y0) / recorte.shape[0])
    nuevo = (max(1, int(recorte.shape[1] * escala)), max(1, int(recorte.shape[0] * escala)))
    recorte = cv2.resize(recorte, nuevo, interpolation=cv2.INTER_AREA)
    lienzo = np.zeros((tam[1], tam[0]), np.uint8)
    ox = x0 + ((x1 - x0) - nuevo[0]) // 2
    oy = y0 + ((y1 - y0) - nuevo[1]) // 2
    lienzo[oy:oy + nuevo[1], ox:ox + nuevo[0]] = recorte
    color_lienzo = None
    if color is not None:
        c = cv2.resize(color[y_a:y_b, x_a:x_b], nuevo, interpolation=cv2.INTER_AREA)
        color_lienzo = np.full((tam[1], tam[0], 3), 255, np.uint8)
        color_lienzo[oy:oy + nuevo[1], ox:ox + nuevo[0]] = c
    return lienzo > 127, color_lienzo


def engrosar(mascara: np.ndarray, grosor: int) -> np.ndarray:
    if grosor <= 1:
        return mascara
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grosor, grosor))
    return cv2.dilate(mascara.astype(np.uint8), k) > 0


def preparar_boceto(img: Image.Image, zona_titulo: str = "superior",
                    detector_hed: Optional[Callable] = None, grosor_min: int = 3) -> Boceto:
    """Pipeline completo de la entrada del usuario (o de un dibujo de D2/D3)."""
    if zona_titulo not in config.ZONAS_TITULO:
        raise ValueError(f"Zona de título inválida: {zona_titulo}")
    tam_original = img.size
    img = reducir(limpiar_metadatos(img))
    if img.mode in ("RGBA", "LA"):
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        fondo.paste(img, mask=img.split()[-1])
        img = fondo
    rgb = np.array(img.convert("RGB"))
    gris = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    if min(gris.shape) < 64:
        raise BocetoInvalido("La imagen es demasiado pequeña (mínimo 64 px por lado).")
    tipo = tipo_de_entrada(gris)
    mascara = quitar_ruido(extraer_lineas(gris, tipo, detector_hed))
    tinta = validar_tinta(mascara)
    ubicada, color_lienzo = ubicar_en_lienzo(mascara, zona_titulo,
                                             color=rgb if tipo == "foto" else None)
    ubicada = engrosar(ubicada, grosor_min)
    lineas = Image.fromarray(np.where(ubicada, 0, 255).astype(np.uint8))
    control = Image.fromarray(np.where(ubicada, 255, 0).astype(np.uint8)).convert("RGB")
    return Boceto(
        lineas=lineas,
        control=control,
        tipo=tipo,
        tinta=tinta,
        color_original=Image.fromarray(color_lienzo) if color_lienzo is not None else None,
        info={"zona_titulo": zona_titulo, "tam_original": tam_original},
    )
