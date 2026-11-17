"""Acceso a los recursos gráficos de FROG (`app/assets/<categoría>/<nombre>.png`).

Las imágenes se incrustan en el HTML como datos en base64 (data URI): así funcionan igual en
Colab, con el enlace público de Gradio y en local, sin configurar rutas de archivos ni
depender de la versión de Gradio. Cada imagen se codifica una sola vez.

Los recursos se generan con `python -m scripts.recortar_recursos` a partir de la hoja
`recursos visuales.png`. Si falta alguno, `img()` devuelve una cadena vacía y la interfaz
sigue funcionando (las funciones de `estilo.py` usan un emoji de respaldo).
"""
from __future__ import annotations

import base64
import html
import io
from functools import lru_cache
from pathlib import Path
from typing import Optional

ASSETS = Path(__file__).parent / "assets"
CATEGORIAS = ("mascotas", "fondos", "escenas", "iconos", "decoraciones")


@lru_cache(maxsize=None)
def ruta(nombre: str) -> Optional[Path]:
    """Ruta del recurso `nombre` (sin extensión) en cualquiera de las categorías."""
    for categoria in CATEGORIAS:
        for extension in (".webp", ".png"):          # en Colab basta con subir los .webp
            p = ASSETS / categoria / f"{nombre}{extension}"
            if p.exists():
                return p
    return None


def _codificar(p: Path) -> tuple:
    """(bytes, tipo MIME) para incrustar. Se usa el WebP que deja `scripts.recortar_recursos`
    junto a cada PNG (calidad alta, transparencia intacta, ~4 veces menos peso y sin codificar
    al arrancar). Si falta, se codifica en el momento y, si Pillow no lo admite, se usa el PNG."""
    webp = p.with_suffix(".webp")
    if p.suffix == ".webp" or webp.exists():
        return (p if p.suffix == ".webp" else webp).read_bytes(), "image/webp"
    try:
        from PIL import Image
        with Image.open(p) as im:
            salida = io.BytesIO()
            im.convert("RGBA").save(salida, "WEBP", quality=90, alpha_quality=100, method=2)
        return salida.getvalue(), "image/webp"
    except Exception:
        return p.read_bytes(), "image/png"


@lru_cache(maxsize=None)
def uri(nombre: str) -> str:
    """El recurso como data URI, o "" si no existe."""
    p = ruta(nombre)
    if not p:
        return ""
    datos, tipo = _codificar(p)
    return f"data:{tipo};base64," + base64.b64encode(datos).decode()


def img(nombre: str, ancho: Optional[int] = None, alto: Optional[int] = None, clase: str = "",
        alt: str = "") -> str:
    """Etiqueta <img> del recurso. Con `alt` vacío la imagen es decorativa y se oculta a los
    lectores de pantalla."""
    u = uri(nombre)
    if not u:
        return ""
    # El tamaño va en el estilo de la propia imagen: el CSS de Gradio pisa los atributos width/height.
    # La medida que no se da se calcula sola, conservando la proporción.
    medidas = ";".join(m for m in (f"width:{ancho}px" if ancho else "width:auto" if alto else "",
                                   f"height:{alto}px" if alto else "height:auto" if ancho else "") if m)
    estilo = f' style="{medidas}"' if medidas else ""
    accesible = f'alt="{html.escape(alt)}"' if alt else 'alt="" aria-hidden="true"'
    return f'<img class="frog-img {clase}" src="{u}"{estilo} {accesible}>'
