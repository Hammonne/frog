"""Agente explicador y validador determinista (sección 9 del informe).

El agente recibe el registro JSON de la sesión, nunca las imágenes, así que solo puede
describir lo registrado. Para que el validador pueda comprobarlo, el resumen sigue un formato:

    Ronda 1 (eje: estilo)
    Aceptadas: R1-V1 (acuarela), R1-V4 (vectorial plano)
    Rechazadas: R1-V2 (lápices de colores; motivo: colores; comentario: "muy apagado"), ...
    Para la ronda 2: ...
    Preferencias: ...
    {"accepted": [...], "rejected": [...]}

El validador comprueba que (1) el bloque JSON coincida con el registro, (2) cada ID esté en la
línea correcta (Aceptadas/Rechazadas), (3) no se mencionen IDs inexistentes y (4) todo valor
nombrado en "Preferencias" haya sido aceptado al menos una vez. No evalúa la redacción
interpretativa: eso se anota a mano en E3. Si falla, se reintenta con el error (máx. 2) y
después se usa el resumen por plantilla.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .. import config
from ..guardrails.texto import normalizar
from .llm import Mensajes, extraer_json
from .planificador import cambios_entre_rondas

PATRON_ID = re.compile(r"\bR(\d+)\s*-\s*V(\d+)\b", re.IGNORECASE)


def etiqueta(p: str, v: str) -> str:
    return config.ETIQUETAS_VALORES[p][v]


# ------------------------------------------------------------ hechos del registro
def hechos(sesion: Dict) -> Dict:
    """Resume el registro en hechos verificables, en el orden en que los cuenta el resumen."""
    rondas = []
    for i, r in enumerate(sesion["rounds"]):
        eje = r["axis"]
        aceptadas, rechazadas, otras = [], [], []
        for v in r["variations"]:
            item = {"id": v["id"], "valor_eje": etiqueta(eje, v["params"][eje])}
            if v.get("reasons"):
                item["motivos"] = [m.replace("_", " ") for m in v["reasons"]]
            if v.get("comment"):
                item["comentario"] = v["comment"]
            edicion = (v.get("typography") or {}).get("user_edit")
            if edicion:
                item["cambio_tipografia"] = edicion
            {"accepted": aceptadas, "rejected": rechazadas}.get(v.get("decision"), otras).append(item)
        ronda = {"ronda": r["round"], "eje": config.NOMBRES_PARAMETROS[eje],
                 "aceptadas": aceptadas, "rechazadas": rechazadas}
        if otras:
            ronda["sin_decision_o_bloqueadas"] = [o["id"] for o in otras]
        if i + 1 < len(sesion["rounds"]):
            sig = sesion["rounds"][i + 1]
            ronda["siguiente"] = {
                "eje": config.NOMBRES_PARAMETROS[sig["axis"]],
                "planificador": [
                    {"parametro": config.NOMBRES_PARAMETROS[c["parametro"]],
                     "valores_usados": [etiqueta(c["parametro"], v) for v in c["valores_usados"]],
                     "historial": [{"valor": etiqueta(c["parametro"], h["valor"]),
                                    "aceptadas": h["aceptadas"], "rechazadas": h["rechazadas"]}
                                   for h in c["historial"]]}
                    for c in cambios_entre_rondas(r, sig)],
            }
        rondas.append(ronda)
    salida = {"titulo": sesion.get("title", ""), "rondas": rondas}
    story = sesion.get("story") or {}
    elems = story.get("prompt_elements") or {}
    usados = [x for x in (elems.get("personajes", []) + elems.get("objetos", [])) if x]
    if elems.get("lugar"):
        usados.append(elems["lugar"])
    if usados:
        salida["elementos_de_la_historia"] = usados
    return salida


def decisiones(sesion: Dict) -> Dict[str, set]:
    acc, rej = set(), set()
    for r in sesion["rounds"]:
        for v in r["variations"]:
            if v.get("decision") == "accepted":
                acc.add(v["id"])
            elif v.get("decision") == "rejected":
                rej.add(v["id"])
    return {"accepted": acc, "rejected": rej}


def valores_aceptados(sesion: Dict) -> set:
    return {(p, val) for r in sesion["rounds"] for v in r["variations"] if v.get("decision") == "accepted"
            for p, val in v["params"].items()}


# ------------------------------------------------------------ prompt
SISTEMA = """Eres el agente explicador de FROG, un sistema que propone portadas de cuentos infantiles.
Recibes los HECHOS de una sesión en JSON y escribes, en español y en segunda persona, un resumen breve para la persona usuaria.
Formato obligatorio, una sección por ronda:
Ronda N (eje: <eje>)
Aceptadas: <ID> (<valor>), ... o "ninguna"
Rechazadas: <ID> (<valor>; motivo: ...; comentario: "..."), ... o "ninguna"
Para la ronda N+1: <qué cambió el planificador, usando solo el campo "siguiente"> (omitir en la última ronda)
Al final:
Preferencias: <valores que aceptaste, solo si aparecen en propuestas aceptadas> o "sin preferencias claras"
Y en la última línea, solo este JSON: {"accepted": [IDs aceptados], "rejected": [IDs rechazados]}
Reglas: usa los IDs exactos (p. ej. R1-V3); no inventes propuestas, motivos ni valores que no estén en los hechos; menciona los cambios de tipografía y los elementos de la historia si aparecen; no describas las imágenes."""


def mensajes_resumen(sesion: Dict, error_previo: Optional[str] = None) -> Mensajes:
    m = [{"role": "system", "content": SISTEMA},
         {"role": "user", "content": "HECHOS:\n" + json.dumps(hechos(sesion), ensure_ascii=False, indent=1)}]
    if error_previo:
        m.append({"role": "user", "content": f"Tu resumen anterior no coincide con el registro: {error_previo}. "
                                             "Vuelve a escribirlo completo corrigiendo eso."})
    return m


# ------------------------------------------------------------ validador
@dataclass
class Validacion:
    ok: bool
    errores: List[str] = field(default_factory=list)


def _lineas(texto: str, prefijo: str) -> List[str]:
    patron = re.compile(r"^\W*" + prefijo + r"\W*:", re.IGNORECASE)
    return [l for l in texto.splitlines() if patron.match(normalizar(l))]


def _ids(texto: str) -> set:
    return {f"R{a}-V{b}" for a, b in PATRON_ID.findall(texto)}


def _sin_json(texto: str) -> str:
    """Texto sin el bloque JSON final (lo que ve la persona usuaria)."""
    i = texto.rfind('{"accepted"')
    if i < 0:
        i = texto.rfind("{")
        if i < 0 or "accepted" not in texto[i:]:
            return texto.strip()
    return texto[:i].rstrip("` \n")


def validar(texto: str, sesion: Dict) -> Validacion:
    reg = decisiones(sesion)
    existentes = {v["id"] for r in sesion["rounds"] for v in r["variations"]}
    errores = []

    bloque = extraer_json(texto)
    if not isinstance(bloque, dict) or "accepted" not in bloque or "rejected" not in bloque:
        errores.append('falta el bloque JSON final {"accepted": [...], "rejected": [...]}')
    else:
        for k in ("accepted", "rejected"):
            declarados = set(map(str, bloque.get(k) or []))
            if declarados != reg[k]:
                faltan, sobran = sorted(reg[k] - declarados), sorted(declarados - reg[k])
                errores.append(f"en el JSON, '{k}' debe ser {sorted(reg[k])}"
                               + (f" (faltan {faltan})" if faltan else "") + (f" (sobran {sobran})" if sobran else ""))

    cuerpo = _sin_json(texto)
    inventados = _ids(cuerpo) - existentes
    if inventados:
        errores.append(f"menciona propuestas que no existen: {sorted(inventados)}")
    en_aceptadas = set().union(*[_ids(l) for l in _lineas(cuerpo, "aceptadas")] or [set()])
    en_rechazadas = set().union(*[_ids(l) for l in _lineas(cuerpo, "rechazadas")] or [set()])
    mal_acc = en_aceptadas - reg["accepted"]
    mal_rej = en_rechazadas - reg["rejected"]
    if mal_acc:
        errores.append(f"pone como aceptadas propuestas que fueron rechazadas o no tienen decisión: {sorted(mal_acc)}")
    if mal_rej:
        errores.append(f"pone como rechazadas propuestas que fueron aceptadas o no tienen decisión: {sorted(mal_rej)}")
    omitidas = (reg["accepted"] - en_aceptadas) | (reg["rejected"] - en_rechazadas)
    if omitidas:
        errores.append(f"no nombra en su línea Aceptadas/Rechazadas a: {sorted(omitidas)}")

    aceptados = valores_aceptados(sesion)
    for linea in _lineas(cuerpo, "preferencias"):
        t = normalizar(linea)
        for p, valores in config.ETIQUETAS_VALORES.items():
            for v, nombre in valores.items():
                if re.search(r"(?<![a-z0-9])" + re.escape(normalizar(nombre)) + r"(?![a-z0-9])", t) \
                        and (p, v) not in aceptados:
                    errores.append(f"dice que prefieres '{nombre}', pero ninguna propuesta aceptada lo tenía")
    return Validacion(ok=not errores, errores=errores)


# ------------------------------------------------------------ plantilla (respaldo)
def _item(it: Dict, con_detalle: bool) -> str:
    detalle = [it["valor_eje"]]
    if con_detalle and it.get("motivos"):
        detalle.append("motivo: " + ", ".join(it["motivos"]))
    if con_detalle and it.get("comentario"):
        detalle.append(f'comentario: "{it["comentario"]}"')
    if it.get("cambio_tipografia"):
        detalle.append("cambiaste la tipografía a " + ", ".join(f"{k} {v}" for k, v in it["cambio_tipografia"].items()))
    return f"{it['id']} ({'; '.join(detalle)})"


def resumen_plantilla(sesion: Dict) -> str:
    h = hechos(sesion)
    lineas = []
    if h.get("elementos_de_la_historia"):
        lineas.append("Elementos de tu historia usados en las portadas: " + ", ".join(h["elementos_de_la_historia"]) + ".")
    for r in h["rondas"]:
        lineas.append(f"Ronda {r['ronda']} (eje: {r['eje']})")
        lineas.append("Aceptadas: " + (", ".join(_item(i, False) for i in r["aceptadas"]) or "ninguna"))
        lineas.append("Rechazadas: " + (", ".join(_item(i, True) for i in r["rechazadas"]) or "ninguna"))
        if r.get("sin_decision_o_bloqueadas"):
            lineas.append("Sin decisión o bloqueadas por seguridad: " + ", ".join(r["sin_decision_o_bloqueadas"]))
        if r.get("siguiente"):
            s = r["siguiente"]
            favorecidos, evitados = [], []
            for c in s["planificador"]:
                for h_ in c["historial"]:
                    if h_["aceptadas"] > 0 and h_["valor"] in c["valores_usados"]:
                        favorecidos.append(h_["valor"])
                    elif h_["aceptadas"] == 0 and h_["rechazadas"] > 0 and h_["valor"] not in c["valores_usados"]:
                        evitados.append(h_["valor"])
            texto = f"Para la ronda {r['ronda'] + 1}: elegiste comparar {s['eje']}"
            if favorecidos:
                texto += "; el planificador repitió lo que aceptaste (" + ", ".join(favorecidos) + ")"
            if evitados:
                texto += "; dejó de proponer lo que rechazaste (" + ", ".join(evitados) + ")"
            if not favorecidos and not evitados:
                texto += "; como aún no había aceptaciones, el planificador siguió explorando"
            lineas.append(texto + ".")
    preferidos = []
    for p, valores in config.ETIQUETAS_VALORES.items():
        cuenta = {}
        for r in sesion["rounds"]:
            if p == r["axis"]:
                for v in r["variations"]:
                    if v.get("decision") == "accepted":
                        cuenta[v["params"][p]] = cuenta.get(v["params"][p], 0) + 1
        if cuenta:
            mejor = max(cuenta, key=cuenta.get)
            preferidos.append(valores[mejor])
    lineas.append("Preferencias: " + (", ".join(preferidos) if preferidos else "sin preferencias claras"))
    reg = decisiones(sesion)
    lineas.append(json.dumps({"accepted": sorted(reg["accepted"]), "rejected": sorted(reg["rejected"])}))
    return "\n".join(lineas)


# ------------------------------------------------------------ agente con reintentos
def explicar(sesion: Dict, llm: Optional[Callable[[Mensajes], str]], nombre_llm: str = "",
             max_reintentos: int = config.MAX_REINTENTOS_RESUMEN) -> Dict:
    """Devuelve una entrada de `summaries` del registro:
    {"llm", "text", "user_text", "validated", "attempts", "template", "errors", "latency_s"}."""
    inicio = time.perf_counter()
    errores_por_intento: List[List[str]] = []
    texto, intentos = "", 0
    if llm is not None:
        error_previo = None
        for intentos in range(1, max_reintentos + 2):
            texto = llm(mensajes_resumen(sesion, error_previo))
            v = validar(texto, sesion)
            if v.ok:
                return _entrada(nombre_llm, texto, True, intentos, False, errores_por_intento, inicio)
            errores_por_intento.append(v.errores)
            error_previo = "; ".join(v.errores)
    texto = resumen_plantilla(sesion)
    ok = validar(texto, sesion).ok
    return _entrada(nombre_llm, texto, ok, intentos, True, errores_por_intento, inicio)


def _entrada(llm, texto, validado, intentos, plantilla, errores, inicio) -> Dict:
    return {"llm": llm, "text": texto, "user_text": _sin_json(texto), "validated": validado,
            "attempts": intentos, "template": plantilla, "errors": errores,
            "latency_s": round(time.perf_counter() - inicio, 3)}
