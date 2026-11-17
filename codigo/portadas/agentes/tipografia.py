"""Agente tipográfico: propone cómo se ve el título de cada portada.

Un LLM local (temperatura 0) recibe medidas calculadas sobre la zona del título de ESA portada
(colores, brillo, cuánto trazo hay), el estilo y el ambiente elegidos, la edad y el largo del
título, y devuelve un JSON con valores de un espacio acotado: fuente del catálogo, tamaño, curva,
onda, inclinación, contorno y color. `portadas.titulo.limitar` recorta todo a sus límites y
`render_titulo` lo dibuja con Pillow, así que el agente puede deformar el título de forma lúdica
pero nunca escribir mal una letra. Si el agente falla o devuelve algo inválido, se usa una
disposición por defecto según la edad ("respaldo").

El título ya pasó por la lista de bloqueo antes de llegar aquí; el agente no ve la imagen ni
la historia, solo números.
"""
from __future__ import annotations

import json
from typing import Callable, Dict, Optional, Tuple

import numpy as np
from PIL import Image

from .. import config
from ..titulo import (CATALOGO, FUENTES_PRINCIPIANTES, LIMITES, caja_titulo, contraste, limitar,
                      render_titulo)

Generador = Callable[[str, str], str]
FUENTES = list(CATALOGO)

SISTEMA = f"""You choose the lettering for the title of a children's picture-book cover.
You get measurements of the area where the title goes. Answer with ONE JSON object and nothing else, with these keys:
- "fuente": one of {FUENTES}
- "tamano": letter height as a fraction of the cover height, from {LIMITES['tamano'][0]} to {LIMITES['tamano'][1]} (smaller for long titles)
- "curva": arc of the line, from {LIMITES['curva'][0]} to {LIMITES['curva'][1]} (0 = straight, positive = arch up)
- "onda": wave of the letters, from 0 to {LIMITES['onda'][1]}
- "inclinacion": degrees of alternating tilt per letter, from 0 to {LIMITES['inclinacion'][1]}
- "contorno": outline thickness as a fraction of the letter size, from {LIMITES['contorno'][0]} to {LIMITES['contorno'][1]}
- "color": text color as "#RRGGBB"
Rules: legibility comes first. Pick a color that contrasts strongly with the area colors (see contraste_oscuro and contraste_claro: they are the contrast ratios of dark and light text against the area; use the one that is at least 4.5, or a saturated color that clearly differs from colores_dominantes). If "bordes" is high the area is busy: use a thicker outline and a calmer lettering. Ages 0-3 and 4-6: only {list(FUENTES_PRINCIPIANTES)}, no wave and little tilt. Mood: "humor" and "alegre" allow curve and wave, "calma" and "misterio" stay calm. Long titles (many letters) need a smaller size.
Example input: {{"titulo": "El conejo jardinero", "n_letras": 19, "estilo": "acuarela", "ambiente": "calma", "edad": "4-6", "zona": "superior", "medidas": {{"bordes": 0.02, "color_medio": "#F2E8D5", "brillo": 0.82, "colores_dominantes": ["#F2E8D5", "#CFE3C0"], "contraste_oscuro": 14.1, "contraste_claro": 1.3}}}}
Example answer: {{"fuente": "Fredoka", "tamano": 0.062, "curva": 0.1, "onda": 0.0, "inclinacion": 1, "contorno": 0.04, "color": "#2E5E3A"}}"""


def medidas_zona(img: Image.Image, zona: str) -> Dict:
    """Números sobre la zona del título de una portada (lo único que ve el agente de la imagen)."""
    caja = caja_titulo(zona, *img.size)
    if caja is None:
        return {}
    area = img.convert("RGB").crop(caja)
    gris = np.asarray(area.convert("L"), dtype=float)
    gx, gy = np.abs(np.diff(gris, axis=1))[:-1, :], np.abs(np.diff(gris, axis=0))[:, :-1]
    bordes = float(((gx + gy) > 60).mean())
    medio = area.resize((1, 1), Image.BOX).getpixel((0, 0))
    paleta = area.quantize(colors=3, method=Image.Quantize.MEDIANCUT).convert("RGB")
    dominantes = [f"#{r:02X}{g:02X}{b:02X}" for _, (r, g, b) in sorted(paleta.getcolors(), reverse=True)]
    brillo = float(np.asarray(area.convert("L"), dtype=float).mean() / 255)
    return {"bordes": round(bordes, 3), "color_medio": "#%02X%02X%02X" % medio, "brillo": round(brillo, 2),
            "colores_dominantes": dominantes, "contraste_oscuro": round(contraste((25, 25, 25), medio), 1),
            "contraste_claro": round(contraste((255, 255, 255), medio), 1)}


def _json_de(respuesta: str) -> Dict:
    inicio, fin = respuesta.find("{"), respuesta.rfind("}")
    if inicio < 0 or fin <= inicio:
        raise ValueError("la respuesta no contiene JSON")
    datos = json.loads(respuesta[inicio: fin + 1])
    if not isinstance(datos, dict):
        raise ValueError("el JSON no es un objeto")
    return datos


def proponer(img: Image.Image, titulo: str, zona: str, params: Dict[str, str],
             llm: Optional[Generador], reintentos: int = 1) -> Tuple[Dict, Dict]:
    """Devuelve (estilo ya recortado a los límites, meta). meta["origen"] es 'agente' o 'respaldo'."""
    edad = params.get("P3", "sin")
    medidas = medidas_zona(img, zona)
    meta = {"origen": "respaldo", "intentos": 0, "medidas": medidas, "propuesta": None, "error": ""}
    if llm is None or not medidas:
        return limitar({}, edad), meta
    pedido = json.dumps({"titulo": titulo, "n_letras": len(titulo.replace(" ", "")), "estilo": params.get("P1"),
                         "ambiente": params.get("P4"), "edad": edad, "zona": zona, "medidas": medidas},
                        ensure_ascii=False)
    maximo = getattr(llm, "max_tokens", None)
    if maximo is not None:
        llm.max_tokens = min(maximo, 160)            # la respuesta es un JSON corto
    try:
        for intento in range(1, reintentos + 2):
            meta["intentos"] = intento
            try:
                propuesta = _json_de(llm(SISTEMA, pedido if not meta["error"] else
                                         f"{pedido}\n\nYour previous answer was invalid ({meta['error']}). "
                                         "Answer again with one valid JSON object."))
            except (ValueError, json.JSONDecodeError) as e:
                meta["error"] = str(e)[:100]
                continue
            meta["propuesta"], meta["origen"], meta["error"] = propuesta, "agente", ""
            return limitar(propuesta, edad), meta
    finally:
        if maximo is not None:
            llm.max_tokens = maximo
    return limitar({}, edad), meta


def titular_basico(img: Image.Image, titulo: str, zona: str, edad: str, params: Optional[Dict] = None):
    """Título con la disposición por defecto según la edad (sin agente)."""
    return render_titulo(img, titulo, zona, edad)


def titular_con_agente(img: Image.Image, titulo: str, zona: str, edad: str, params: Optional[Dict] = None,
                       llm: Optional[Generador] = None):
    """Pide el estilo al agente y dibuja el título. info["agente"] guarda de dónde salió el estilo."""
    params = dict(params or {})
    params.setdefault("P3", edad)
    estilo, meta = proponer(img, titulo, zona, params, llm)
    out, info = render_titulo(img, titulo, zona, edad, **estilo)
    info["agente"] = meta
    return out, info
