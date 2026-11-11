"""Filtro de texto para la historia, el título, la instrucción libre y los elementos
que extrae el agente de historia (guardrail 1 de la sección 12).

Es una lista de bloqueo deliberadamente simple y auditable. Tiene falsos positivos y
negativos conocidos; E5 mide ambos con 30 entradas adversariales.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List

# Categoría -> términos (sin tildes, en minúscula). Español e inglés.
BLOQUEO: Dict[str, List[str]] = {
    "violencia": [
        "sangre", "sangriento", "ensangrentado", "matar", "mata", "asesinar", "asesinato", "cadaver",
        "arma", "armas", "pistola", "fusil", "cuchillo", "bomba", "tortura", "decapitar", "gore",
        "blood", "bloody", "kill", "killing", "murder", "corpse", "gun", "rifle", "knife", "weapon",
        "bomb", "torture", "behead",
    ],
    "sexual": [
        "desnudo", "desnuda", "desnudez", "sexual", "sexo", "erotico", "erotica", "porno", "pornografia",
        "lenceria", "sensual", "nude", "naked", "nudity", "sex", "sexy", "erotic", "porn", "lingerie", "nsfw",
    ],
    "odio": [
        "nazi", "esvastica", "racista", "terrorista", "swastika", "racist", "terrorist", "kkk",
    ],
    "miedo_extremo": [
        "terror", "horror", "demonio", "satanico", "zombi", "zombie", "demon", "satanic",
    ],
}

# Nombres de ilustradores, estudios y personajes con marca: el sistema no imita
# estilos con nombre propio ni reproduce personajes protegidos (sección 12).
NOMBRES_PROTEGIDOS: List[str] = [
    # estudios y marcas
    "disney", "pixar", "dreamworks", "ghibli", "studio ghibli", "marvel", "dc comics", "nickelodeon",
    "cartoon network", "illumination", "sanrio", "nintendo", "pokemon", "lego",
    # personajes
    "mickey", "minnie", "donald duck", "elsa", "frozen", "simba", "peppa", "bluey", "paw patrol",
    "patrulla canina", "pikachu", "hello kitty", "spiderman", "spider-man", "batman", "superman",
    "winnie the pooh", "winnie pooh", "paddington", "gruffalo", "minion", "minions", "shrek",
    "harry potter", "totoro", "snoopy", "garfield", "dora la exploradora", "dora the explorer",
    "barbie", "sonic", "mario bros", "super mario",
    # ilustradores y autores con estilo reconocible
    "eric carle", "beatrix potter", "dr seuss", "dr. seuss", "maurice sendak", "quentin blake",
    "oliver jeffers", "jon klassen", "mo willems", "axel scheffler", "julia donaldson", "miyazaki",
    "anthony browne", "tomie depaola", "chris van allsburg", "shel silverstein",
]

# Pedidos explícitos de imitar un estilo ajeno.
PATRONES_ESTILO = [
    r"\bal estilo de\b", r"\bestilo de [a-z]+ [a-z]+", r"\bin the style of\b", r"\bstyle of\b",
    r"\bcomo lo dibujaria\b", r"\bdrawn by\b", r"\bby artist\b",
]


@dataclass
class ResultadoFiltro:
    ok: bool
    motivos: List[str] = field(default_factory=list)
    coincidencias: List[str] = field(default_factory=list)


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", texto.lower()).strip()


def _buscar(texto: str, terminos: List[str]) -> List[str]:
    encontrados = []
    for t in terminos:
        patron = r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])"
        if re.search(patron, texto):
            encontrados.append(t)
    return encontrados


def filtrar_texto(texto: str) -> ResultadoFiltro:
    """Devuelve ok=False si el texto contiene contenido no apto o nombres protegidos."""
    if not texto:
        return ResultadoFiltro(ok=True)
    t = normalizar(texto)
    res = ResultadoFiltro(ok=True)
    for categoria, terminos in BLOQUEO.items():
        hallados = _buscar(t, terminos)
        if hallados:
            res.ok = False
            res.motivos.append(categoria)
            res.coincidencias.extend(hallados)
    hallados = _buscar(t, NOMBRES_PROTEGIDOS)
    if hallados:
        res.ok = False
        res.motivos.append("nombre_protegido")
        res.coincidencias.extend(hallados)
    for patron in PATRONES_ESTILO:
        m = re.search(patron, t)
        if m:
            res.ok = False
            if "imitacion_estilo" not in res.motivos:
                res.motivos.append("imitacion_estilo")
            res.coincidencias.append(m.group(0))
    return res


def mensaje_usuario(res: ResultadoFiltro) -> str:
    """Explicación para mostrar en la interfaz (sin repetir las palabras bloqueadas)."""
    if res.ok:
        return ""
    textos = {
        "violencia": "contenido violento",
        "sexual": "contenido sexual",
        "odio": "contenido de odio",
        "miedo_extremo": "contenido de terror",
        "nombre_protegido": "nombres de personajes, marcas o ilustradores con derechos",
        "imitacion_estilo": "pedidos de imitar el estilo de otra persona",
    }
    partes = ", ".join(textos[m] for m in res.motivos)
    return f"Este sistema crea portadas para niños y no acepta {partes}. Reformula el texto, por favor."
