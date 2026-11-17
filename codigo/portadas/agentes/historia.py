"""Agente de historia: convierte el cuento del usuario en elementos visuales.

Un LLM local (temperatura 0) devuelve un JSON con personajes, objetos, lugar, momento,
tono y edad sugerida. Un verificador determinista comprueba que cada personaje y objeto
aparezca en el texto, para que el agente no invente lo que la historia no dice; la interfaz
muestra los que no se pudieron verificar y el usuario confirma o edita antes de generar.

Salida de `extraer_elementos` (el prompt de imagen usa los campos en inglés):
    {"personajes": ["rabbit"], "objetos": ["flowers"], "lugar": "garden", "momento": "",
     "tono": "alegre", "edad": "4-6",
     "es": {"personajes": ["conejo"], "objetos": ["flores"], "lugar": "jardin"},
     "no_verificados": [], "intentos": 1, "origen": "llm"}
"""
from __future__ import annotations

import json
import re
from typing import Callable, Dict, List, Optional

from .. import config
from ..guardrails.texto import filtrar_texto, normalizar

MAX_PALABRAS = 500
MAX_PERSONAJES, MAX_OBJETOS = 3, 4
TONOS = list(config.AMBIENTES)          # alegre, aventura, calma, misterio, humor
EDADES = [e for e in config.EDADES if e != "sin"]
MOMENTOS = ["sunrise", "morning", "noon", "afternoon", "sunset", "evening", "night"]
# Si el modelo contesta en español, se traduce; lo que no se reconoce se descarta.
MOMENTOS_ES = {"amanecer": "sunrise", "alba": "sunrise", "manana": "morning", "mediodia": "noon",
               "tarde": "afternoon", "atardecer": "sunset", "anochecer": "evening",
               "noche": "night", "madrugada": "night"}

SISTEMA = f"""You extract visual elements from a children's story (written in Spanish or English) to illustrate a picture-book cover.
Answer with ONE JSON object and nothing else. Keys:
- "personajes_es": list of main characters, in Spanish, exactly as the story names them (max {MAX_PERSONAJES}).
- "personajes": the same characters in English, same order.
- "objetos_es": list of important physical objects, in Spanish, only if the story mentions them (max {MAX_OBJETOS}).
- "objetos": the same objects in English, same order.
- "lugar_es": the place, one or two Spanish words, or "".
- "lugar": the place in English as ONE short noun like "garden", "forest", "sea", "beach", or "".
- "momento": time of day, in English, one of {MOMENTOS}, or "".
- "tono": one of {TONOS}.
- "edad": suggested reader age, one of {EDADES}.
Rules: use ONLY what the story says. Do not add gender, ethnicity, age or physical features the story does not mention. Do not invent characters, objects or places. If something is not in the story use [] or "".
Characters: use the kind of character (rabbit, dragon, girl), never proper names ("Tomas the dragon" -> "dragon"). Keep a size or color adjective only if the story says it ("little fox").
Objects: only things that can be drawn (flowers, boat, cookies). Never actions, speech, jokes, feelings or ideas.
Example story: "Un conejo que ama las flores vive en un jardin."
Example answer: {{"personajes_es": ["conejo"], "personajes": ["rabbit"], "objetos_es": ["flores"], "objetos": ["flowers"], "lugar_es": "jardin", "lugar": "garden", "momento": "", "tono": "alegre", "edad": "4-6"}}"""

# Sinónimos cortos para el verificador (forma normalizada, sin tildes).
SINONIMOS: Dict[str, List[str]] = {
    "conejo": ["liebre", "conejito", "gazapo"], "perro": ["perrito", "cachorro", "can"],
    "gato": ["gatito", "minino"], "oso": ["osito"], "pajaro": ["ave", "pajarito"],
    "pez": ["pececito", "peces"], "dragon": ["dragoncito"], "casa": ["hogar", "cabana"],
    "bosque": ["selva", "arboleda"], "flores": ["flor"], "arbol": ["arboles"], "mar": ["oceano"],
}


PALABRAS_ES = {"el", "la", "los", "las", "un", "una", "que", "de", "en", "y", "con", "su", "se", "por", "del", "al", "era", "vez"}
PALABRAS_EN = {"the", "a", "an", "and", "of", "in", "to", "was", "his", "her", "with", "that", "on", "is", "he", "she", "they"}


def detectar_idioma(texto: str) -> str:
    """'es' o 'en' según qué lista de palabras funcionales domina (por defecto, 'es')."""
    palabras = _tokens(texto)
    es, en = sum(w in PALABRAS_ES for w in palabras), sum(w in PALABRAS_EN for w in palabras)
    return "en" if en > es else "es"


class HistoriaInvalida(ValueError):
    """La historia está vacía, es demasiado larga o contiene texto bloqueado."""


# ------------------------------------------------------------------------ verificación
def _tokens(texto: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", normalizar(texto))


def _raiz(palabra: str) -> str:
    """Raíz tosca: quita plural y diminutivo habituales (conejitos -> conej)."""
    p = palabra
    for suf in ("citos", "citas", "cito", "cita", "itos", "itas", "ito", "ita", "es", "s"):
        if p.endswith(suf) and len(p) - len(suf) >= 3:
            p = p[: -len(suf)]
            break
    return p[:-1] if len(p) > 4 and p[-1] in "aeiou" else p


def aparece_en_texto(termino: str, texto: str) -> bool:
    """¿El término (en español) aparece en el texto? Coincide por raíz y por sinónimos."""
    palabras = {_raiz(w) for w in _tokens(texto)}
    for parte in _tokens(termino):
        if len(parte) < 3:        # artículos y preposiciones ("el", "de")
            continue
        candidatos = {parte, *SINONIMOS.get(parte, [])}
        if not any(_raiz(c) in palabras for c in candidatos):
            return False
    return True


def verificar(elementos_es: Dict, texto: str) -> List[str]:
    """Devuelve los personajes y objetos que NO se encuentran en el texto. Los elementos deben
    estar en el idioma del texto (español por defecto; para un texto en inglés, los de `personajes`
    y `objetos`)."""
    dudosos = []
    for clave in ("personajes", "objetos"):
        for t in elementos_es.get(clave, []):
            if not aparece_en_texto(t, texto):
                dudosos.append(t)
    return dudosos


# --------------------------------------------------------------------------- análisis
def _json_de(respuesta: str) -> Dict:
    """Extrae el primer objeto JSON de la respuesta (los modelos a veces añaden texto)."""
    inicio, fin = respuesta.find("{"), respuesta.rfind("}")
    if inicio < 0 or fin <= inicio:
        raise ValueError("la respuesta no contiene JSON")
    return json.loads(respuesta[inicio: fin + 1])


def _lista(valor, tope: int) -> List[str]:
    if isinstance(valor, str):
        valor = [valor]
    if not isinstance(valor, list):
        return []
    limpio = [str(v).strip().lower() for v in valor if str(v).strip()]
    return list(dict.fromkeys(limpio))[:tope]


def _momento(valor) -> str:
    m = normalizar(str(valor or "")).strip()
    m = MOMENTOS_ES.get(m, m)
    return m if m in MOMENTOS else ""


def _lugar(valor) -> str:
    """Deja el lugar como sustantivo corto: 'bottom of the sea' -> 'sea'."""
    texto = str(valor or "").strip().lower()
    return re.split(r"\bof (?:the )?", texto)[-1].strip() if " of " in f" {texto} " else texto


def normalizar_salida(d: Dict) -> Dict:
    """Valida la forma del JSON del modelo y lo deja con tipos y valores permitidos."""
    pers_es, pers_en = _lista(d.get("personajes_es"), MAX_PERSONAJES), _lista(d.get("personajes"), MAX_PERSONAJES)
    obj_es, obj_en = _lista(d.get("objetos_es"), MAX_OBJETOS), _lista(d.get("objetos"), MAX_OBJETOS)
    if len(pers_es) != len(pers_en) or len(obj_es) != len(obj_en):
        raise ValueError("las listas en español e inglés no coinciden")
    tono = str(d.get("tono", "")).strip().lower()
    edad = str(d.get("edad", "")).strip()
    return {
        "personajes": pers_en, "objetos": obj_en,
        "lugar": _lugar(d.get("lugar")),
        "momento": _momento(d.get("momento")),
        "tono": tono if tono in TONOS else config.POR_DEFECTO["P4"],
        "edad": edad if edad in EDADES else config.POR_DEFECTO["P3"],
        "es": {"personajes": pers_es, "objetos": obj_es,
               "lugar": str(d.get("lugar_es", "") or "").strip().lower()},
    }


def validar_historia(texto: str) -> str:
    texto = (texto or "").strip()
    if not texto:
        raise HistoriaInvalida("Escribe una historia.")
    if len(texto.split()) > MAX_PALABRAS:
        raise HistoriaInvalida(f"La historia supera las {MAX_PALABRAS} palabras.")
    filtro = filtrar_texto(texto)
    if not filtro.ok:
        raise HistoriaInvalida("La historia contiene contenido no apto para una portada infantil "
                               f"({', '.join(filtro.motivos)}). Cámbiala e inténtalo de nuevo.")
    return texto


def _elementos_vacios(origen: str, intentos: int) -> Dict:
    return {"personajes": [], "objetos": [], "lugar": "", "momento": "",
            "tono": config.POR_DEFECTO["P4"], "edad": config.POR_DEFECTO["P3"],
            "es": {"personajes": [], "objetos": [], "lugar": ""},
            "no_verificados": [], "intentos": intentos, "origen": origen}


def extraer_elementos(texto: str, llm: Callable[[str, str], str], reintentos: int = 2) -> Dict:
    """Pipeline completo. Lanza HistoriaInvalida si el texto no se puede procesar.

    Si el modelo no devuelve un JSON válido tras `reintentos` intentos adicionales, o si
    sus elementos son bloqueados por los guardrails, devuelve elementos vacíos con
    `origen="respaldo"`: el usuario escribe la escena a mano en la interfaz."""
    texto = validar_historia(texto)
    mensaje = f"Story:\n{texto}"
    ultimo_error = ""
    for intento in range(1, reintentos + 2):
        pedido = mensaje if not ultimo_error else (
            f"{mensaje}\n\nYour previous answer was invalid ({ultimo_error}). Answer again with one valid JSON object.")
        try:
            elementos = normalizar_salida(_json_de(llm(SISTEMA, pedido)))
        except (ValueError, json.JSONDecodeError) as e:
            ultimo_error = str(e)[:120]
            continue
        # Los elementos que extrae el agente también pasan por la lista de bloqueo.
        salida = " ".join(elementos["personajes"] + elementos["objetos"] +
                          [elementos["lugar"], elementos["momento"]] + elementos["es"]["personajes"] +
                          elementos["es"]["objetos"] + [elementos["es"]["lugar"]])
        if not filtrar_texto(salida).ok:
            return _elementos_vacios("respaldo", intento)
        idioma = detectar_idioma(texto)
        en_su_idioma = elementos["es"] if idioma == "es" else elementos
        elementos["no_verificados"] = verificar(en_su_idioma, texto)
        elementos["idioma"] = idioma
        elementos["intentos"], elementos["origen"] = intento, "llm"
        return elementos
    return _elementos_vacios("respaldo", reintentos + 1)


def escena_ingles(elementos: Dict, quitar: Optional[List[str]] = None) -> str:
    """Escena para el prompt a partir de los elementos (opcionalmente sin los que el
    usuario descartó en la interfaz)."""
    from ..motores.prompts import escena_desde_elementos
    quitar = {q.lower() for q in (quitar or [])}
    filtrados = dict(elementos)
    filtrados["personajes"] = [p for p in elementos["personajes"] if p not in quitar]
    filtrados["objetos"] = [o for o in elementos["objetos"] if o not in quitar]
    return escena_desde_elementos(filtrados)


# ----------------------------------------------------------- evaluación contra anotaciones
def _clave(texto: str) -> str:
    """Forma canónica para comparar con una anotación: sin tildes, sin artículos y en singular."""
    return " ".join(_raiz(t) for t in _tokens(texto) if len(t) >= 3 and t not in PALABRAS_ES | PALABRAS_EN)


def comparar_conjuntos(predichos: List[str], anotados: List[str]) -> Dict[str, int]:
    """Verdaderos positivos, falsos positivos y falsos negativos entre dos listas de elementos."""
    p = {_clave(x) for x in predichos if _clave(x)}
    a = {_clave(x) for x in anotados if _clave(x)}
    return {"vp": len(p & a), "fp": len(p - a), "fn": len(a - p)}


def evaluar_extraccion(elementos: Dict, anotacion: Dict[str, str], idioma: str) -> Dict[str, int]:
    """Compara personajes y objetos con una fila anotada a mano (valores separados por ';').
    `idioma` es el de la historia anotada: 'es' usa las listas en español; 'en', las del prompt."""
    total = {"vp": 0, "fp": 0, "fn": 0}
    for campo in ("personajes", "objetos"):
        pred = elementos["es"][campo] if idioma == "es" else elementos[campo]
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
