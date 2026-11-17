"""Agente de explicación: resume en palabras qué aceptó y rechazó el usuario.

El LLM (Qwen2.5-7B o Phi-3.5-mini, temperatura 0) recibe SOLO un resumen de hechos
sacado del registro JSON de la sesión, nunca las imágenes. Un validador determinista
contrasta el texto con el registro; si hay discrepancias se vuelve a pedir el resumen
indicando el error (máximo `reintentos`) y, si persiste, se usa un resumen por plantilla
que solo contiene datos del registro.

Entrada: sesión = {"rounds": [ronda, ...], "story": {...elementos usados...},
                   "typography_changes": [{"id": "R1-V2", "cambio": "fuente: Andika"}]}
Cada ronda es la que devuelve `generar_ronda` con `decision` ("accepted"/"rejected"/
"blocked"), `reasons` (casillas), `reason` (comentario) y el bloque `planner`.
"""
from __future__ import annotations

import json
import re
from typing import Callable, Dict, List, Optional, Set, Tuple

from .. import config
from ..guardrails.texto import normalizar

NOMBRES_EJE = {"P1": "Estilo", "P2": "Paleta", "P3": "Edad", "P4": "Ambiente",
               "P5": "Fidelidad", "P6": "Zona del título"}
ID_RE = re.compile(r"R\d+-V\d+")
CUE_PREFERENCIA = ("prefi", "prefe", "favorit", "gust", "eligi")   # prefiere, prefirió, preferido...
CUE_AZAR = ("azar", "aleator", "muestre", "sortea")
FUENTES_CONOCIDAS = ("andika", "fredoka", "baloo", "lilita", "dejavu")

SISTEMA = """Eres el agente que explica a una persona, en español y con tono amable, qué decidió al elegir portadas de un libro infantil.
Recibirás un JSON con los hechos de la sesión. Reglas estrictas:
1. Usa SOLO lo que está en el JSON. No inventes propuestas, valores, motivos ni cambios.
2. Escribe, para cada ronda, una línea "Ronda N (eje: <eje>) - Aceptadas: <IDs con su valor>. Rechazadas: <IDs con su valor>." Usa los IDs exactamente como aparecen (por ejemplo R1-V2).
3. Si hay motivos o comentarios de rechazo, menciónalos junto al ID. Menciona los elementos de la historia usados solo si aparecen en el JSON. Menciona un cambio de tipografía SOLO si el JSON tiene la clave "tipografia"; si no la tiene, no hables de fuentes ni de tipografía.
4. Para explicar qué hizo el planificador usa solo el bloque "planificador" de cada ronda. Si ese bloque trae "frase_para_copiar", cópiala TAL CUAL, palabra por palabra, al final de la línea de ESA misma ronda (cada ronda trae la suya: no las mezcles ni las muevas a otra ronda). Las rondas que no traen "frase_para_copiar" no llevan nada sobre el planificador. Di que un valor es preferido solo si fue aceptado al menos una vez.
5. Máximo de palabras de texto: el número "limite_palabras" del JSON (no lo menciones en el texto). Aun así, nombra TODAS las propuestas con su ID.
6. Termina con UNA línea con un objeto JSON, sin nada después, con todos los IDs de toda la sesión: {"accepted": [...], "rejected": [...]}
7. Un rechazo con "motivos" o "comentario" debe llevarlos junto a su ID. Si hay "tipografia", di qué ID cambió y a qué fuente. En la ronda 1 no hubo azar (se mostraron los 5 valores del eje); no digas que algo se eligió al azar en esa ronda. Los parámetros elegidos al azar en cada ronda son SOLO los de "parametros_al_azar" de esa ronda; el eje de la ronda nunca es al azar.

EJEMPLO de formato (con datos inventados, no los copies):
Ronda 1 (eje: Estilo) - Aceptadas: R1-V1 (acuarela), R1-V2 (collage). Rechazadas: R1-V3 (vectorial; motivo: colores, comentario: muy fuerte).
Ronda 2 (eje: Ambiente) - Aceptadas: R2-V1 (calma). Rechazadas: R2-V2 (humor). El planificador eligió al azar, según lo aceptado antes: Paleta, Edad.
{"accepted": ["R1-V1", "R1-V2", "R2-V1"], "rejected": ["R1-V3", "R2-V2"]}"""


# ------------------------------------------------------------------------------ hechos
def clasificar(sesion: Dict) -> Tuple[Set[str], Set[str], Set[str]]:
    """IDs aceptados, rechazados y bloqueados de toda la sesión, según el registro."""
    acept, rech, bloq = set(), set(), set()
    for r in sesion["rounds"]:
        for v in r["variations"]:
            {"accepted": acept, "rejected": rech, "blocked": bloq}.get(v.get("decision"), set()).add(v["id"])
    return acept, rech, bloq


def frase_planificador(nombres: List[str]) -> str:
    """La frase que explica qué parámetros eligió el planificador al azar en una ronda."""
    return "El planificador eligió al azar, según lo aceptado antes: " + ", ".join(nombres) + "."


def limite_palabras(sesion: Dict) -> int:
    """Largo máximo del resumen. Nombrar todas las propuestas con su valor y motivo ocupa más cuanto
    más largas son la sesión (hasta 3 rondas y 15 propuestas): se da 1,5 veces lo que ocupa el resumen
    por plantilla, con un mínimo de 120 palabras (las sesiones cortas quedan como antes)."""
    return max(120, int(1.5 * len(resumen_plantilla(sesion).split())))


def hechos(sesion: Dict) -> Dict:
    """Resumen compacto y sin imágenes que recibe el LLM (incluye el largo máximo permitido)."""
    return {**_hechos(sesion), "limite_palabras": limite_palabras(sesion)}


def _hechos(sesion: Dict) -> Dict:
    """Los hechos de la sesión, sin el límite de palabras (la plantilla se arma con esto)."""
    rondas = []
    for r in sesion["rounds"]:
        eje = r["axis"]
        info = {"ronda": r["round"], "eje": f"{eje} ({NOMBRES_EJE[eje]})",
                "aceptadas": [], "rechazadas": [], "bloqueadas": []}
        for v in r["variations"]:
            d = v.get("decision")
            valor = v["params"][eje]
            if d == "accepted":
                info["aceptadas"].append({"id": v["id"], "valor": valor})
            elif d == "rejected":
                item = {"id": v["id"], "valor": valor}
                if v.get("reasons"):
                    item["motivos"] = v["reasons"]
                if (v.get("reason") or "").strip():
                    item["comentario"] = v["reason"].strip()
                info["rechazadas"].append(item)
            elif d == "blocked":
                info["bloqueadas"].append(v["id"])
        p = r.get("planner") or {}
        info["planificador"] = {"metodo": p.get("method", ""), "parametros_al_azar": [NOMBRES_EJE[x] for x in p.get("free_params", [])],
                                "valores_preferidos": p.get("favorites", {})}
        if info["planificador"]["parametros_al_azar"]:
            info["planificador"]["frase_para_copiar"] = frase_planificador(info["planificador"]["parametros_al_azar"])
        rondas.append(info)
    salida = {"rondas": rondas}
    if sesion.get("story"):
        s = sesion["story"]
        salida["historia"] = {k: s[k] for k in ("personajes", "objetos", "lugar", "momento") if s.get(k)}
    if sesion.get("typography_changes"):
        salida["tipografia"] = sesion["typography_changes"]
    return salida


def valores_aceptados(sesion: Dict) -> Set[str]:
    """Valores (de cualquier parámetro) que aparecen en alguna propuesta aceptada."""
    return {valor for r in sesion["rounds"] for v in r["variations"]
            if v.get("decision") == "accepted" for valor in v["params"].values()}


def _todos_los_valores() -> Set[str]:
    return {valor for p in ("P1", "P2", "P3", "P4") for valor in config.PARAMETROS[p]}


# ---------------------------------------------------------------------------- validador
def separar_bloque(respuesta: str) -> Tuple[str, Optional[Dict]]:
    """Separa el texto del bloque JSON final {"accepted":..., "rejected":...}."""
    fin = respuesta.rfind("}")
    inicio = respuesta.rfind("{", 0, fin + 1) if fin >= 0 else -1
    if inicio < 0:
        return respuesta.strip(), None
    try:
        bloque = json.loads(respuesta[inicio: fin + 1])
    except json.JSONDecodeError:
        return respuesta.strip(), None
    return (respuesta[:inicio] + respuesta[fin + 1:]).strip().rstrip("`").strip(), bloque


def _segmentos(texto: str) -> List[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n", texto) if s.strip()]


def validar(texto: str, bloque: Optional[Dict], sesion: Dict) -> List[str]:
    """Lista de discrepancias entre el resumen y el registro (vacía = válido)."""
    errores: List[str] = []
    acept, rech, bloq = clasificar(sesion)
    conocidos = acept | rech | bloq

    # 1. El bloque JSON declarado coincide con el registro.
    if not isinstance(bloque, dict) or "accepted" not in bloque or "rejected" not in bloque:
        errores.append('falta el bloque final {"accepted": [...], "rejected": [...]}')
    else:
        if set(bloque["accepted"]) != acept:
            errores.append(f"accepted debe ser exactamente {sorted(acept)}")
        if set(bloque["rejected"]) != rech:
            errores.append(f"rejected debe ser exactamente {sorted(rech)}")

    # 2. Cada ID del texto existe, y aparece donde corresponde.
    mencionados = set(ID_RE.findall(texto))
    inventados = mencionados - conocidos
    if inventados:
        errores.append(f"IDs que no existen en el registro: {sorted(inventados)}")
    for seg in _segmentos(texto):
        n = normalizar(seg)
        if "bloquead" in n:
            continue
        dice_acept, dice_rech = "aceptad" in n, "rechazad" in n
        if dice_acept == dice_rech:        # ninguna o ambas categorías: no se puede decidir
            continue
        esperado, nombre = (acept, "aceptadas") if dice_acept else (rech, "rechazadas")
        mal = [i for i in ID_RE.findall(seg) if i in conocidos and i not in esperado]
        if mal:
            errores.append(f"{sorted(set(mal))} no están {nombre} en el registro")
    faltan = (acept | rech) - mencionados
    if faltan:
        errores.append(f"faltan estos IDs en el texto: {sorted(faltan)}")

    # 3. Todo valor presentado como preferido fue aceptado al menos una vez
    #    (se ignora si el valor va precedido de una negación: "no le gustó la tierra").
    ok = valores_aceptados(sesion)
    for seg in _segmentos(texto):
        n = normalizar(seg)
        if not any(c in n for c in CUE_PREFERENCIA):
            continue
        for valor in _todos_los_valores():
            m = re.search(rf"(?<![\w-]){re.escape(normalizar(valor))}(?![\w-])", n)
            if m and valor not in ok and not _negado(n, m.start()):
                errores.append(f"se dice que prefiere '{valor}' pero nunca lo aceptó")

    # 4. Lo que se dice "al azar" debe ser un parámetro que el planificador sí muestreó.
    #    Se usa la ronda de la que se está hablando (la última "Ronda N" mencionada).
    libres_por_ronda = {r["round"]: {p for p in (r.get("planner") or {}).get("free_params", [])}
                        for r in sesion["rounds"]}
    todas = set().union(*libres_por_ronda.values()) if libres_por_ronda else set()
    actual = None
    for seg in _segmentos(texto):
        n = normalizar(seg)
        rondas = re.findall(r"ronda (\d+)", n)
        if rondas:
            actual = int(rondas[-1])
        if not any(c in n for c in CUE_AZAR):
            continue
        libres = libres_por_ronda.get(actual, todas)
        donde = f" en la ronda {actual}" if actual in libres_por_ronda else ""
        for p, nombre in NOMBRES_EJE.items():           # "la paleta se eligió al azar"
            m = re.search(rf"(?<!\w){normalizar(nombre.split()[0])}(?!\w)", n)
            if m and p not in libres and p != "P6" and not _negado(n, m.start()):
                errores.append(f"'{nombre}' no se eligió al azar{donde}: no fue un parámetro muestreado")
        valores_libres = {valor for p in libres for valor in config.PARAMETROS[p]}
        for valor in _todos_los_valores() - valores_libres:
            m = re.search(rf"(?<![\w-]){re.escape(normalizar(valor))}(?![\w-])", n)
            if m and not _negado(n, m.start()):
                errores.append(f"'{valor}' no se eligió al azar{donde}: no es un parámetro que el planificador muestreara")

    # 5. Debe incluir los cambios de tipografía y los motivos de rechazo del registro.
    for c in sesion.get("typography_changes") or []:
        nuevo = normalizar(str(c["cambio"]).split(":")[-1]).strip()
        if nuevo and nuevo not in normalizar(texto):
            errores.append(f"falta mencionar el cambio de tipografía de {c['id']} ({c['cambio']})")
    # 6. No afirmar cambios de tipografía que no existen (el LLM tiende a copiar el ejemplo del prompt).
    cambios = sesion.get("typography_changes") or []
    reales = [normalizar(str(c["cambio"]).split(":")[-1]).strip() for c in cambios]
    for seg in _segmentos(texto):
        n = normalizar(seg)
        m = re.search(r"fuente|tipograf", n)
        if not m or _negado(n, m.start()):
            continue
        if not cambios:
            errores.append("se menciona un cambio de tipografía pero el registro no tiene ninguno")
            continue
        for fuente in FUENTES_CONOCIDAS:
            if fuente in n and not any(fuente in r for r in reales):
                errores.append(f"se dice que se usó la fuente {fuente.capitalize()} pero no está en el registro")

    # 7. Si el planificador eligió parámetros al azar en alguna ronda, el resumen debe explicarlo.
    libres = [r["round"] for r in sesion["rounds"] if (r.get("planner") or {}).get("free_params")]
    if libres and not any(c in normalizar(texto) for c in ("planific", "azar", "muestre")):
        errores.append(f"falta explicar qué eligió el planificador en la ronda {libres[0]} "
                       "(parámetros elegidos al azar según lo aceptado)")

    segs = _segmentos(texto)
    for r in sesion["rounds"]:
        for v in r["variations"]:
            if v.get("decision") != "rejected":
                continue
            palabras = _palabras_clave((v.get("reasons") or []) + [v.get("reason") or ""])
            if palabras and not any(v["id"] in s and any(p in normalizar(s) for p in palabras) for s in segs):
                errores.append(f"falta el motivo del rechazo de {v['id']} ({', '.join(v.get('reasons') or [])} "
                               f"{v.get('reason') or ''})".replace("  ", " ").replace(" )", ")"))
    return list(dict.fromkeys(errores))


def _negado(n: str, pos: int) -> bool:
    """¿Hay una negación o rechazo justo antes de la posición `pos` del texto normalizado?"""
    antes = n[max(0, pos - 45): pos]
    return any(w in antes for w in ("no ", "rechaz", "descart", "evit", "menos", "nunca"))


def _palabras_clave(textos: List[str]) -> List[str]:
    """Palabras significativas (>=5 letras) de los motivos y comentarios, normalizadas y en raíz."""
    palabras = []
    for t in textos:
        palabras += [w[:5] for w in re.findall(r"[a-z0-9]+", normalizar(t)) if len(w) >= 5]
    return palabras


# ------------------------------------------------------------------------------ plantilla
def resumen_plantilla(sesion: Dict) -> str:
    """Resumen sin LLM: solo datos del registro (respaldo cuando el LLM falla)."""
    lineas = []
    for h in _hechos(sesion)["rondas"]:
        acept = ", ".join(f"{a['id']} ({a['valor']})" for a in h["aceptadas"]) or "ninguna"
        rech = ", ".join(f"{a['id']} ({a['valor']})" for a in h["rechazadas"]) or "ninguna"
        linea = f"Ronda {h['ronda']} (eje: {h['eje']}) - Aceptadas: {acept}. Rechazadas: {rech}."
        motivos = [f"{a['id']}: " + "; ".join(a.get("motivos", []) + ([a["comentario"]] if a.get("comentario") else []))
                   for a in h["rechazadas"] if a.get("motivos") or a.get("comentario")]
        if motivos:
            linea += " Motivos: " + " | ".join(motivos) + "."
        if h["bloqueadas"]:
            linea += " Bloqueadas por los guardrails: " + ", ".join(h["bloqueadas"]) + "."
        if h["planificador"]["parametros_al_azar"]:
            linea += " " + frase_planificador(h["planificador"]["parametros_al_azar"])
        lineas.append(linea)
    if sesion.get("typography_changes"):
        lineas.append("Cambios de tipografía: " + "; ".join(
            f"{c['id']} ({c['cambio']})" for c in sesion["typography_changes"]) + ".")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------------- agente
def resumir(sesion: Dict, llm: Callable[[str, str], str], reintentos: int = 2) -> Dict:
    """Pide el resumen al LLM y lo valida. Devuelve
    {"texto", "origen": "llm"|"plantilla", "intentos", "errores": [...]}."""
    if not sesion.get("rounds"):
        raise ValueError("No hay rondas decididas que resumir.")
    mensaje = "Hechos de la sesión (JSON):\n" + json.dumps(hechos(sesion), ensure_ascii=False)
    errores_previos: List[str] = []
    historial: List[List[str]] = []
    borradores: List[str] = []
    for intento in range(1, reintentos + 2):
        pedido = mensaje if not errores_previos else (
            mensaje + "\n\nTu respuesta anterior tenía errores: " + " | ".join(errores_previos) +
            ". Corrígelos y responde de nuevo siguiendo todas las reglas.")
        bruto = llm(SISTEMA, pedido)
        borradores.append(bruto)
        texto, bloque = separar_bloque(bruto)
        errores = validar(texto, bloque, sesion)
        historial.append(errores)
        if not errores:
            return {"texto": texto, "origen": "llm", "intentos": intento, "errores": historial,
                    "borradores": borradores}
        errores_previos = errores
    return {"texto": resumen_plantilla(sesion), "origen": "plantilla", "intentos": reintentos + 1,
            "errores": historial, "borradores": borradores}
