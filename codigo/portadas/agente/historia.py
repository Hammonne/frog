"""Agente de historia (sección 5 del informe).

Convierte la historia del usuario en elementos visuales. Cada elemento viene en los dos idiomas,
{"es": "conejo", "en": "rabbit"}: el verificador busca la versión del idioma de la historia
(sin tildes y aceptando plurales) y al prompt de Stable Diffusion solo va el inglés.

Flujo: filtro de texto -> LLM (temperatura 0) -> JSON -> verificación contra el texto ->
filtro de texto sobre los elementos -> lista para que el usuario la confirme en la interfaz.
El agente no añade género, etnia ni rasgos físicos que la historia no mencione.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional

from .. import config
from ..guardrails.texto import filtrar_texto, normalizar
from .llm import Mensajes, extraer_json

SISTEMA = """Eres un asistente que lee cuentos infantiles y extrae SOLO los elementos visuales que el texto menciona, para ilustrar la portada.
Responde únicamente con un objeto JSON, sin texto adicional, con esta forma:
{"personajes": [{"es": "...", "en": "..."}],
 "objetos": [{"es": "...", "en": "..."}],
 "lugar": {"es": "...", "en": "..."} o null,
 "momento": {"es": "...", "en": "..."} o null,
 "tono": uno de [%(tonos)s],
 "edad": uno de [%(edades)s]}
Reglas:
- Cada elemento es un sustantivo en singular, en minúsculas, en español ("es") y en inglés ("en").
- Escribe en el campo del idioma de la historia la MISMA palabra que aparece en el texto.
- Personajes: animales, personas o seres que actúan. Usa el tipo ("conejo", "niña"), no el nombre propio.
- Objetos: cosas que se ven. Máximo 4 personajes y 4 objetos, los más importantes.
- No inventes nada que el texto no diga. No añadas género, color de piel ni rasgos físicos.
- Si un campo no aparece en la historia, usa [] o null."""

EJEMPLO_USUARIO = "Historia:\nUn conejo que ama las flores las cuida en su jardín durante el invierno."
EJEMPLO_RESPUESTA = ('{"personajes": [{"es": "conejo", "en": "rabbit"}], '
                     '"objetos": [{"es": "flor", "en": "flower"}], '
                     '"lugar": {"es": "jardín", "en": "garden"}, '
                     '"momento": {"es": "invierno", "en": "winter"}, "tono": "calma", "edad": "4-6"}')

_STOP_ES = {"el", "la", "los", "las", "de", "que", "y", "en", "un", "una", "su", "se", "con", "por", "para",
            "del", "al", "lo", "como", "pero", "era", "muy", "habia", "estaba", "dijo"}
_STOP_EN = {"the", "a", "an", "and", "of", "to", "in", "was", "he", "she", "it", "his", "her", "with",
            "they", "on", "for", "said", "one", "day", "there", "had", "very", "is"}


class HistoriaBloqueada(ValueError):
    pass


def detectar_idioma(texto: str) -> str:
    palabras = re.findall(r"[a-z]+", normalizar(texto))
    es = sum(w in _STOP_ES for w in palabras)
    en = sum(w in _STOP_EN for w in palabras)
    return "es" if es >= en else "en"


def mensajes_extraccion(historia: str) -> Mensajes:
    sistema = SISTEMA % {"tonos": ", ".join(f'"{t}"' for t in config.AMBIENTES),
                         "edades": ", ".join(f'"{e}"' for e in config.EDADES)}
    return [
        {"role": "system", "content": sistema},
        {"role": "user", "content": EJEMPLO_USUARIO},
        {"role": "assistant", "content": EJEMPLO_RESPUESTA},
        {"role": "user", "content": f"Historia:\n{historia.strip()}"},
    ]


# ------------------------------------------------------------ normalización y verificación
def _tokens(texto: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", normalizar(texto))


def _formas(palabra: str) -> set:
    """Singular y plurales simples (es/en): flor/flores, rabbit/rabbits, pez/peces, box/boxes."""
    w = palabra
    formas = {w, w + "s", w + "es"}
    if w.endswith("z"):
        formas.add(w[:-1] + "ces")
    if w.endswith("ces"):
        formas.add(w[:-3] + "z")
    if w.endswith("es") and len(w) > 4:
        formas.add(w[:-2])
    if w.endswith("s") and len(w) > 3:
        formas.add(w[:-1])
    if w.endswith("y") and len(w) > 2:
        formas.add(w[:-1] + "ies")
    if w.endswith("ies"):
        formas.add(w[:-3] + "y")
    return formas


def aparece_en(elemento: str, historia: str) -> bool:
    """True si todas las palabras de contenido del elemento están en la historia
    (sin tildes, sin mayúsculas, aceptando plurales)."""
    texto = set(_tokens(historia))
    palabras = [w for w in _tokens(elemento) if w not in _STOP_ES | _STOP_EN]
    if not palabras:
        return False
    return all(_formas(w) & texto for w in palabras)


def _par(x) -> Optional[Dict[str, str]]:
    """Acepta {"es","en"} o un texto suelto; devuelve {"es","en"} en minúsculas o None."""
    if isinstance(x, dict):
        es, en = str(x.get("es") or "").strip().lower(), str(x.get("en") or "").strip().lower()
    elif isinstance(x, str) and x.strip():
        es = en = x.strip().lower()
    else:
        return None
    if not es and not en:
        return None
    return {"es": es or en, "en": en or es}


def normalizar_extraccion(datos: Optional[Dict]) -> Dict:
    """Limpia la salida del LLM: estructura fija, valores de tono/edad válidos."""
    datos = datos if isinstance(datos, dict) else {}
    salida = {
        "personajes": [p for p in (_par(x) for x in (datos.get("personajes") or [])) if p][:4],
        "objetos": [p for p in (_par(x) for x in (datos.get("objetos") or [])) if p][:4],
        "lugar": _par(datos.get("lugar")),
        "momento": _par(datos.get("momento")),
        "tono": datos.get("tono") if datos.get("tono") in config.AMBIENTES else None,
        "edad": datos.get("edad") if datos.get("edad") in config.EDADES else None,
    }
    return salida


def verificar(extraccion: Dict, historia: str, idioma: Optional[str] = None) -> Dict:
    """Marca cada personaje, objeto, lugar y momento como respaldado o no por el texto,
    y aplica el filtro de texto a cada elemento. No borra nada: la interfaz muestra los no
    respaldados marcados y el usuario decide."""
    idioma = idioma or detectar_idioma(historia)
    no_respaldados, bloqueados = [], []
    for campo in ("personajes", "objetos", "lugar", "momento"):
        valores = extraccion.get(campo)
        valores = valores if isinstance(valores, list) else ([valores] if valores else [])
        for el in valores:
            if not aparece_en(el[idioma], historia):
                no_respaldados.append({"campo": campo, **el})
            if not (filtrar_texto(el["es"]).ok and filtrar_texto(el["en"]).ok):
                bloqueados.append({"campo": campo, **el})
    return {"idioma": idioma, "no_respaldados": no_respaldados, "bloqueados": bloqueados}


def elementos_para_prompt(extraccion: Dict, verificacion: Optional[Dict] = None,
                          incluir_no_respaldados: bool = False) -> Dict:
    """Versión en inglés para `motores.prompts.escena_desde_elementos`.
    Excluye siempre los bloqueados y, salvo que el usuario los confirme, los no respaldados."""
    verificacion = verificacion or {"no_respaldados": [], "bloqueados": []}
    excluir = {(e["campo"], e["en"]) for e in verificacion["bloqueados"]}
    if not incluir_no_respaldados:
        excluir |= {(e["campo"], e["en"]) for e in verificacion["no_respaldados"]}

    def ok(campo, el):
        return el and (campo, el["en"]) not in excluir

    return {
        "personajes": [p["en"] for p in extraccion["personajes"] if ok("personajes", p)],
        "objetos": [o["en"] for o in extraccion["objetos"] if ok("objetos", o)],
        "lugar": extraccion["lugar"]["en"] if ok("lugar", extraccion["lugar"]) else None,
        "momento": extraccion["momento"]["en"] if ok("momento", extraccion["momento"]) else None,
    }


# ------------------------------------------------------------ agente
def extraer_elementos(historia: str, llm: Callable[[Mensajes], str], nombre_llm: str = "") -> Dict:
    """Ejecuta el agente completo. Devuelve el bloque "story" del registro JSON (sin el texto,
    solo su hash) más los elementos para el prompt."""
    import hashlib

    if len(historia.split()) > config.MAX_PALABRAS_HISTORIA:
        raise HistoriaBloqueada(f"La historia supera las {config.MAX_PALABRAS_HISTORIA} palabras.")
    filtro = filtrar_texto(historia)
    if not filtro.ok:
        raise HistoriaBloqueada(",".join(filtro.motivos))

    crudo = llm(mensajes_extraccion(historia))
    datos = extraer_json(crudo)
    extraccion = normalizar_extraccion(datos)
    verif = verificar(extraccion, historia)
    return {
        "text_sha256": hashlib.sha256(historia.encode("utf-8")).hexdigest(),
        "llm": nombre_llm,
        "language": verif["idioma"],
        "json_ok": datos is not None,
        "elements": extraccion,
        "unsupported": verif["no_respaldados"],
        "blocked": verif["bloqueados"],
        "suggested": {"P3": extraccion["edad"], "P4": extraccion["tono"]},
        "prompt_elements": elementos_para_prompt(extraccion, verif),
        "user_confirmed": False,  # lo marca la interfaz
    }


# ------------------------------------------------------------ evaluación contra anotaciones
def _clave(palabra: str) -> str:
    """Forma canónica para comparar con la anotación: sin tildes y en singular aproximado."""
    toks = [w for w in _tokens(palabra) if w not in _STOP_ES | _STOP_EN]
    canon = []
    for w in toks:
        if w.endswith("ces") and len(w) > 4:
            w = w[:-3] + "z"
        elif w.endswith("ies") and len(w) > 4:
            w = w[:-3] + "y"
        elif w.endswith("es") and len(w) > 4 and w[-3] not in "aeiou":
            w = w[:-2]
        elif w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
            w = w[:-1]
        canon.append(w)
    return " ".join(canon)


def comparar_conjuntos(predichos: List[str], anotados: List[str]) -> Dict[str, int]:
    p = {_clave(x) for x in predichos if _clave(x)}
    a = {_clave(x) for x in anotados if _clave(x)}
    return {"vp": len(p & a), "fp": len(p - a), "fn": len(a - p)}


def evaluar_extraccion(extraccion: Dict, anotacion: Dict[str, str], idioma: str) -> Dict[str, int]:
    """Compara personajes y objetos (en el idioma de la anotación) con una fila anotada a mano.
    `anotacion` usa ';' para separar varios valores, como en las plantillas de anotación."""
    total = {"vp": 0, "fp": 0, "fn": 0}
    for campo in ("personajes", "objetos"):
        pred = [e[idioma] for e in extraccion.get(campo, [])]
        anot = [x for x in (anotacion.get(campo) or "").split(";") if x.strip()]
        for k, v in comparar_conjuntos(pred, anot).items():
            total[k] += v
    return total


def precision_exhaustividad(conteo: Dict[str, int]) -> Dict[str, float]:
    vp, fp, fn = conteo["vp"], conteo["fp"], conteo["fn"]
    precision = vp / (vp + fp) if vp + fp else 0.0
    exhaustividad = vp / (vp + fn) if vp + fn else 0.0
    f1 = 2 * precision * exhaustividad / (precision + exhaustividad) if precision + exhaustividad else 0.0
    return {"precision": precision, "exhaustividad": exhaustividad, "f1": f1}
