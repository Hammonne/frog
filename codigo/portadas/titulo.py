"""Renderizador determinista del título (Pillow). El modelo de imagen nunca escribe texto.

Dibuja el título sobre la portada en la zona elegida (config.ZONAS_TITULO). Elige texto
claro u oscuro según el fondo y, si el contraste WCAG queda por debajo de 4.5:1, añade una
banda semitransparente detrás. Si no se pide una fuente, usa una por defecto según la edad
(el agente tipográfico podrá reemplazarla más adelante pasando `fuente`, `tamano`, `color`).

Fuentes: busca archivos .ttf en `codigo/fuentes/` (p. ej. Andika, Fredoka, Baloo 2, con
licencia SIL OFL); si no hay ninguno, usa DejaVu Sans Bold, que incluye matplotlib.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from . import config

FUENTES_DIR = config.RAIZ / "fuentes"
CONTRASTE_MIN = 4.5                       # WCAG 2.1, texto normal
OSCURO, CLARO = (25, 25, 25), (255, 255, 255)
# Altura de letra como fracción de la altura de la portada, según la edad (más grande si es menor).
TAMANO_POR_EDAD = {"0-3": 0.075, "4-6": 0.065, "7-9": 0.056, "10-12": 0.05, "sin": 0.06}
FUENTE_POR_EDAD = {"0-3": "Andika", "4-6": "Andika", "7-9": "Fredoka", "10-12": "Baloo2", "sin": "Andika"}
MAX_CARACTERES = 60


def fuentes_disponibles() -> List[str]:
    return sorted({p.stem.split("-")[0] for p in FUENTES_DIR.glob("*.ttf")}) if FUENTES_DIR.exists() else []


def _ruta_fuente(nombre: Optional[str]) -> Path:
    if nombre and FUENTES_DIR.exists():
        for p in sorted(FUENTES_DIR.glob("*.ttf")):
            if p.stem.lower().startswith(nombre.lower()):
                return p
    import matplotlib
    return Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans-Bold.ttf"


def _luminancia(rgb) -> float:
    def canal(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b) -> float:
    """Razón de contraste WCAG entre dos colores RGB (1 a 21)."""
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _caja(zona: str, ancho: int, alto: int) -> Optional[Tuple[int, int, int, int]]:
    """Zona (x0, y0, x1, y1) donde va el título; None si no se pide título."""
    if zona == "sin":
        return None
    margen = int(ancho * 0.07)
    if zona == "inferior":
        return margen, int(alto * 0.75), ancho - margen, int(alto * 0.97)
    if zona == "centrada":
        return margen, int(alto * 0.38), ancho - margen, int(alto * 0.62)
    return margen, int(alto * 0.03), ancho - margen, int(alto * (0.28 if zona == "superior" else 0.24))


def _ajustar(texto: str, ruta: Path, tamano: int, ancho_max: int, alto_max: int):
    """Reduce el tamaño hasta que el texto envuelto cabe en la caja. Devuelve (fuente, líneas)."""
    while True:
        fuente = ImageFont.truetype(str(ruta), tamano)
        lineas, actual = [], ""
        for palabra in texto.split():
            prueba = f"{actual} {palabra}".strip()
            if fuente.getlength(prueba) <= ancho_max or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = palabra
        lineas.append(actual)
        alto = len(lineas) * int(tamano * 1.2)
        if (alto <= alto_max and max(fuente.getlength(l) for l in lineas) <= ancho_max) or tamano <= 14:
            return fuente, lineas
        tamano -= 2


def render_titulo(img: Image.Image, titulo: str, zona: str = "superior", edad: str = "4-6",
                  fuente: Optional[str] = None, tamano: Optional[float] = None,
                  color: Optional[Tuple[int, int, int]] = None) -> Tuple[Image.Image, Dict]:
    """Devuelve (portada con título, info). `tamano` es fracción de la altura; `color` RGB.

    info = {"zona", "fuente", "tamano_px", "color", "contraste", "banda"}; si no hay título
    o la zona es "sin", devuelve la imagen sin cambios con info["banda"] = False."""
    titulo = " ".join((titulo or "").split())[:MAX_CARACTERES]
    caja = _caja(zona, *img.size)
    info = {"zona": zona, "fuente": None, "tamano_px": 0, "color": None, "contraste": None, "banda": False}
    if not titulo or caja is None:
        return img.convert("RGB"), info
    base = img.convert("RGBA")
    ancho, alto = base.size
    x0, y0, x1, y1 = caja
    ruta = _ruta_fuente(fuente or FUENTE_POR_EDAD.get(edad, "Andika"))
    px = int(alto * (tamano or TAMANO_POR_EDAD.get(edad, 0.06)))
    letra, lineas = _ajustar(titulo, ruta, px, x1 - x0, y1 - y0)
    interlineado = int(letra.size * 1.2)
    alto_texto = len(lineas) * interlineado
    ytop = y0 + max(0, (y1 - y0 - alto_texto) // 2)

    # Fondo bajo el texto: color medio de la caja de texto.
    caja_texto = (x0, ytop, x1, ytop + alto_texto)
    fondo = base.crop(caja_texto).convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0))
    texto_color = tuple(color) if color else max((OSCURO, CLARO), key=lambda c: contraste(c, fondo))
    ratio = contraste(texto_color, fondo)
    banda = zona == "centrada" or ratio < CONTRASTE_MIN
    if banda:
        opuesto = CLARO if _luminancia(texto_color) < 0.5 else OSCURO
        capa = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ImageDraw.Draw(capa).rounded_rectangle(
            (x0 - 8, ytop - 8, x1 + 8, ytop + alto_texto + 8), radius=14, fill=(*opuesto, 205))
        base = Image.alpha_composite(base, capa)
        fondo = tuple(int(0.8 * o + 0.2 * f) for o, f in zip(opuesto, fondo))   # fondo efectivo aprox.
        ratio = contraste(texto_color, fondo)
    dibujo = ImageDraw.Draw(base)
    contorno = CLARO if _luminancia(texto_color) < 0.5 else OSCURO
    for i, linea in enumerate(lineas):
        x = (ancho - letra.getlength(linea)) / 2
        dibujo.text((x, ytop + i * interlineado), linea, font=letra, fill=texto_color,
                    stroke_width=max(1, letra.size // 18), stroke_fill=contorno)
    info.update({"fuente": ruta.stem, "tamano_px": letra.size, "color": list(texto_color),
                 "contraste": round(ratio, 2), "banda": banda})
    return base.convert("RGB"), info
