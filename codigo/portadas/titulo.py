"""Renderizador determinista del título (Pillow). El modelo de imagen nunca escribe texto.

Dibuja el título sobre la portada en la zona elegida (config.ZONAS_TITULO), letra por letra, con
los valores de un estilo acotado: fuente de un catálogo con licencia SIL OFL, tamaño, curva del
arco, onda, inclinación alterna de las letras, grosor del contorno y color. Los valores se
recortan a límites fijos (`LIMITES`), de modo que quien los proponga (el agente tipográfico o la
persona) puede deformar el título de forma lúdica pero nunca escribir mal una letra ni sacarlo
de su zona. El contraste WCAG con el fondo siempre llega a 4.5:1: si el color pedido no lo logra,
se añade una banda semitransparente y, si aun así no alcanza, se usa texto oscuro o claro.

Fuentes: archivos .ttf de `codigo/fuentes/` (Andika, Fredoka, Baloo 2 y Lilita One, todas SIL OFL;
las licencias están en la misma carpeta). Si falta alguno, usa DejaVu Sans Bold de matplotlib.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import config

FUENTES_DIR = config.RAIZ / "fuentes"
CONTRASTE_MIN = 4.5                       # WCAG 2.1, texto normal
OSCURO, CLARO = (25, 25, 25), (255, 255, 255)
# Altura de letra como fracción de la altura de la portada, según la edad (más grande si es menor).
TAMANO_POR_EDAD = {"0-3": 0.075, "4-6": 0.065, "7-9": 0.056, "10-12": 0.05, "sin": 0.06}
FUENTE_POR_EDAD = {"0-3": "Andika", "4-6": "Andika", "7-9": "Fredoka", "10-12": "Baloo2", "sin": "Andika"}
MAX_CARACTERES = 60

# Catálogo: nombre -> (archivo, ajustes de fuentes variables por nombre de eje).
CATALOGO: Dict[str, Tuple[str, Dict[str, float]]] = {
    "Andika": ("Andika-Bold.ttf", {}),
    "Fredoka": ("Fredoka.ttf", {"Weight": 600, "Width": 100}),
    "Baloo2": ("Baloo2.ttf", {"Weight": 700}),
    "LilitaOne": ("LilitaOne-Regular.ttf", {}),
}
# Lectores que empiezan a leer: fuentes de trazo simple y poca deformación.
FUENTES_PRINCIPIANTES = ("Andika", "Fredoka")
LIMITES = {"tamano": (0.04, 0.10), "curva": (-0.4, 0.4), "onda": (0.0, 0.15),
           "inclinacion": (0.0, 8.0), "contorno": (0.03, 0.10)}
LIMITES_PRINCIPIANTES = {"inclinacion": 4.0, "onda": 0.06}
CONTORNO_POR_DEFECTO = 0.055


def fuentes_disponibles() -> List[str]:
    return [n for n, (archivo, _) in CATALOGO.items() if (FUENTES_DIR / archivo).exists()]


def _cargar_fuente(nombre: Optional[str], tamano: int) -> ImageFont.FreeTypeFont:
    archivo, ejes = CATALOGO.get(nombre or "", CATALOGO["Andika"])
    ruta = FUENTES_DIR / archivo
    if not ruta.exists():
        import matplotlib
        ruta, ejes = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans-Bold.ttf", {}
    fuente = ImageFont.truetype(str(ruta), tamano)
    if ejes:
        try:
            fuente.set_variation_by_axes([ejes.get(a["name"].decode(), a["default"])
                                          for a in fuente.get_variation_axes()])
        except Exception:      # sin soporte de fuentes variables: queda el peso por defecto
            pass
    return fuente


def _color(valor) -> Optional[Tuple[int, int, int]]:
    """'#RRGGBB' o (r, g, b) -> tupla RGB; None si no es válido."""
    try:
        if isinstance(valor, str):
            if valor.strip().lower().startswith("rgb"):          # "rgba(255, 0, 0, 1)" del selector de color
                return _color([float(x) for x in re.findall(r"[\d.]+", valor)[:3]])
            v = valor.strip().lstrip("#")
            if len(v) == 3:
                v = "".join(c * 2 for c in v)
            if len(v) != 6:
                return None
            return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
        rgb = tuple(int(round(float(c))) for c in valor)
        return rgb if len(rgb) == 3 and all(0 <= c <= 255 for c in rgb) else None
    except (TypeError, ValueError):
        return None


def limitar(estilo: Optional[Dict], edad: str = "sin", restringir_edad: bool = True) -> Dict:
    """Deja un estilo propuesto dentro de lo permitido: fuente del catálogo, números en sus
    límites y color válido (None = lo elige el renderizador por contraste). Las reglas para lectores
    principiantes se aplican a lo que propone el agente; lo que la persona elige a mano
    (`restringir_edad=False`) solo se recorta a los límites generales."""
    e = dict(estilo or {})
    fuente = e.get("fuente") if e.get("fuente") in CATALOGO else FUENTE_POR_EDAD.get(edad, "Andika")
    principiante = restringir_edad and edad in ("0-3", "4-6")
    if principiante and fuente not in FUENTES_PRINCIPIANTES:
        fuente = FUENTE_POR_EDAD[edad]

    def num(clave, defecto):
        try:
            x = float(e.get(clave, defecto))
        except (TypeError, ValueError):
            x = defecto
        if math.isnan(x):
            x = defecto
        lo, hi = LIMITES[clave]
        return min(max(x, lo), hi)

    out = {"fuente": fuente, "tamano": num("tamano", TAMANO_POR_EDAD.get(edad, 0.06)),
           "curva": num("curva", 0.0), "onda": num("onda", 0.0), "inclinacion": num("inclinacion", 0.0),
           "contorno": num("contorno", CONTORNO_POR_DEFECTO), "color": _color(e.get("color"))}
    if principiante:
        out["inclinacion"] = min(out["inclinacion"], LIMITES_PRINCIPIANTES["inclinacion"])
        out["onda"] = min(out["onda"], LIMITES_PRINCIPIANTES["onda"])
    return out


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


def caja_titulo(zona: str, ancho: int, alto: int) -> Optional[Tuple[int, int, int, int]]:
    """Zona (x0, y0, x1, y1) donde va el título; None si no se pide título."""
    if zona == "sin":
        return None
    margen = int(ancho * 0.07)
    if zona == "inferior":
        return margen, int(alto * 0.75), ancho - margen, int(alto * 0.97)
    if zona == "centrada":
        return margen, int(alto * 0.38), ancho - margen, int(alto * 0.62)
    return margen, int(alto * 0.03), ancho - margen, int(alto * (0.28 if zona == "superior" else 0.24))


_caja = caja_titulo


def _envolver(texto: str, fuente, ancho_max: int) -> List[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if fuente.getlength(prueba) <= ancho_max or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


def _margen_vertical(tamano: int, curva: float, onda: float, inclinacion: float) -> int:
    """Holgura arriba y abajo que necesitan el arco, la onda y la inclinación."""
    return int(tamano * (abs(curva) * 1.2 + onda + 0.6 * math.sin(math.radians(inclinacion))))


def _disponer(texto: str, nombre: str, tamano: int, ancho_max: int, alto_max: int,
              curva: float, onda: float, inclinacion: float):
    """Reduce el tamaño hasta que el texto envuelto, con su arco y su onda, cabe en la caja."""
    while True:
        fuente = _cargar_fuente(nombre, tamano)
        lineas = _envolver(texto, fuente, ancho_max)
        margen = _margen_vertical(tamano, curva, onda, inclinacion)
        alto = len(lineas) * int(tamano * 1.2) + 2 * margen
        if (alto <= alto_max and max(fuente.getlength(l) for l in lineas) <= ancho_max) or tamano <= 14:
            return fuente, lineas, margen
        tamano -= 2


def _pintar_letra(capa: Image.Image, letra: str, fuente, centro: Tuple[float, float], angulo: float,
                  relleno, contorno_px: int, contorno_color) -> None:
    ancho = int(fuente.getlength(letra)) + 2 * contorno_px + 4
    alto = int(fuente.size * 1.5) + 2 * contorno_px + 4
    mini = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    ImageDraw.Draw(mini).text((contorno_px + 2, contorno_px + 2), letra, font=fuente, fill=relleno,
                              stroke_width=contorno_px, stroke_fill=contorno_color)
    if abs(angulo) > 0.05:
        mini = mini.rotate(angulo, resample=Image.BICUBIC, expand=True)
    capa.alpha_composite(mini, (int(centro[0] - mini.width / 2), int(centro[1] - mini.height / 2)))


def render_titulo(img: Image.Image, titulo: str, zona: str = "superior", edad: str = "4-6",
                  fuente: Optional[str] = None, tamano: Optional[float] = None,
                  color=None, curva: float = 0.0, onda: float = 0.0, inclinacion: float = 0.0,
                  contorno: Optional[float] = None, restringir_edad: bool = True) -> Tuple[Image.Image, Dict]:
    """Devuelve (portada con título, info). `tamano` es fracción de la altura; `color` '#RRGGBB' o RGB.

    info = {"zona", "fuente", "tamano_px", "color", "contraste", "banda", "estilo"}; si no hay
    título o la zona es "sin", devuelve la imagen sin cambios con info["banda"] = False."""
    titulo = " ".join((titulo or "").split())[:MAX_CARACTERES]
    caja = caja_titulo(zona, *img.size)
    info = {"zona": zona, "fuente": None, "tamano_px": 0, "color": None, "contraste": None, "banda": False,
            "estilo": None}
    if not titulo or caja is None:
        return img.convert("RGB"), info
    estilo = limitar({"fuente": fuente, "tamano": tamano, "color": color, "curva": curva, "onda": onda,
                      "inclinacion": inclinacion, "contorno": contorno}, edad, restringir_edad)
    base = img.convert("RGBA")
    ancho, alto = base.size
    x0, y0, x1, y1 = caja
    px = int(alto * estilo["tamano"])
    letra_fuente, lineas, margen = _disponer(titulo, estilo["fuente"], px, x1 - x0, y1 - y0,
                                             estilo["curva"], estilo["onda"], estilo["inclinacion"])
    tam = letra_fuente.size
    interlineado = int(tam * 1.2)
    alto_texto = len(lineas) * interlineado + 2 * margen
    ytop = y0 + max(0, (y1 - y0 - alto_texto) // 2)

    # Fondo bajo el texto: color medio de la caja de texto.
    caja_texto = (x0, ytop, x1, ytop + alto_texto)
    fondo = base.crop(caja_texto).convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0))
    texto_color = estilo["color"] or max((OSCURO, CLARO), key=lambda c: contraste(c, fondo))
    ratio = contraste(texto_color, fondo)
    gris = np.asarray(base.crop(caja_texto).convert("L"), dtype=float)
    bordes = float(((np.abs(np.diff(gris, axis=1))[:-1, :] + np.abs(np.diff(gris, axis=0))[:, :-1]) > 60).mean())
    banda = zona == "centrada" or ratio < CONTRASTE_MIN
    if banda:
        opuesto = CLARO if _luminancia(texto_color) < 0.5 else OSCURO
        efectivo = tuple(int(0.8 * o + 0.2 * f) for o, f in zip(opuesto, fondo))
        if contraste(texto_color, efectivo) < CONTRASTE_MIN:        # el color pedido no sirve ni con banda
            texto_color, opuesto = OSCURO, CLARO
            efectivo = tuple(int(0.8 * o + 0.2 * f) for o, f in zip(opuesto, fondo))
        capa = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ImageDraw.Draw(capa).rounded_rectangle(
            (x0 - 8, ytop - 8, x1 + 8, ytop + alto_texto + 8), radius=14, fill=(*opuesto, 205))
        base = Image.alpha_composite(base, capa)
        ratio = contraste(texto_color, efectivo)
    texto_color = tuple(texto_color)

    contorno_px = max(1, round(tam * estilo["contorno"]))
    contorno_color = CLARO if _luminancia(texto_color) < 0.5 else OSCURO
    capa_texto = Image.new("RGBA", base.size, (0, 0, 0, 0))
    A = 1.2 * tam
    for n, linea in enumerate(lineas):
        total = max(letra_fuente.getlength(linea), 1.0)
        inicio = (ancho - total) / 2
        y_linea = ytop + margen + n * interlineado + tam * 0.6
        for i, letra in enumerate(linea):
            if letra == " ":
                continue
            xi = letra_fuente.getlength(linea[:i])
            xc = xi + letra_fuente.getlength(letra) / 2
            t = 2 * xc / total - 1                                   # -1 (izquierda) a 1 (derecha)
            dy = -estilo["curva"] * A * (1 - t * t) + estilo["onda"] * tam * math.sin(2 * math.pi * i / 6)
            pendiente = 4 * estilo["curva"] * A * t / total
            angulo = math.degrees(math.atan(-pendiente)) + estilo["inclinacion"] * (1 if i % 2 == 0 else -1)
            _pintar_letra(capa_texto, letra, letra_fuente, (inicio + xc, y_linea + dy), angulo,
                          (*texto_color, 255), contorno_px, (*contorno_color, 255))
    base = Image.alpha_composite(base, capa_texto)
    estilo_aplicado = {**{k: (round(v, 3) if isinstance(v, float) else v) for k, v in estilo.items()},
                       "color": list(texto_color)}
    info.update({"fuente": estilo["fuente"], "tamano_px": tam, "color": list(texto_color),
                 "contraste": round(ratio, 2), "banda": banda, "bordes": round(bordes, 3), "estilo": estilo_aplicado})
    return base.convert("RGB"), info
