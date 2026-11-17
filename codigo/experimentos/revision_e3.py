"""Revisión mecánica de los resúmenes de E3 contra el registro real de cada sesión.

Compara, ronda por ronda, lo que dice el resumen con lo que pasó en la sesión (el .jsonl de E2):
portadas aceptadas y rechazadas, valor del eje, motivos de cada rechazo y parámetros que el
planificador eligió al azar. Un motivo de más, un ID en el grupo equivocado o un parámetro al azar
que no lo fue marcan `no`; si no hay ninguna diferencia, `si`. Las filas de plantilla se dejan en blanco.

OJO: es una comprobación automática de hechos, no la anotación manual de la rúbrica. Sirve para
adelantar el trabajo y para que la persona que anota solo revise los casos marcados `no`.
La parte interpretativa ("prefieres colores cálidos") no se evalúa aquí.

Uso:
    python -m experimentos.revision_e3 --csv salidas/e3_qwen/e3_resumenes.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Set

from portadas import config

NOMBRES_EJE = {"P1": "Estilo", "P2": "Paleta", "P3": "Edad", "P4": "Ambiente", "P5": "Fidelidad", "P6": "Zona del título"}
ALIAS = {"edad": "no apto para la edad", "boceto": "se aleja del boceto"}
CATEGORIAS = {"estilo", "colores", "no apto para la edad", "ambiente", "se aleja del boceto"}
ITEM = re.compile(r"(R\d+-V\d+)\s*\(([^)]*)\)")


def _valor(x: str) -> str:
    return x.strip().lower().replace("_", " ")


def _motivos(texto: str):
    """Devuelve (motivos, avisos) de un texto como 'motivo: a, comentario: b, c' o 'a; b'."""
    motivos, avisos = [], []
    texto = re.sub(r"^\s*motivos?\s*:\s*", "", texto.strip())
    for trozo in re.split(r"[;,]", texto):
        t = trozo.strip()
        if not t:
            continue
        if t.lower().startswith("comentario:"):
            t = t.split(":", 1)[1].strip()
            if _valor(t) in CATEGORIAS | set(ALIAS):
                avisos.append(f"llama 'comentario' a un motivo ({t})")
        motivos.append(ALIAS.get(_valor(t), _valor(t)))
    return motivos, avisos


def leer_resumen(texto: str) -> Dict[int, Dict]:
    """{ronda: {aceptadas, rechazadas, valores, motivos, avisos, azar}} a partir del texto del resumen."""
    rondas = {}
    for bloque in re.split(r"(?=Ronda \d+ \()", texto):
        m = re.match(r"Ronda (\d+) \(", bloque)
        if not m:
            continue
        r = {"aceptadas": set(), "rechazadas": set(), "valores": {}, "motivos": {}, "avisos": [], "azar": None}
        plan = re.search(r"según lo aceptado antes:\s*(.*?)\.", bloque)
        if plan:
            r["azar"] = {x.strip() for x in plan.group(1).split(",") if x.strip()}
            bloque = bloque[:plan.start()]
        a = re.search(r"Rechazadas:(.*)", bloque, re.S)
        if not a:
            rondas[int(m.group(1))] = r
            continue
        resto = a.group(1)
        ac = re.search(r"Aceptadas:(.*?)Rechazadas:", bloque, re.S)
        aceptadas = ac.group(1) if ac else ""
        mot = re.search(r"Motivos:(.*)", resto, re.S)
        if mot:
            resto_rech = resto[:mot.start()]
            for parte in mot.group(1).split("|"):
                if ":" in parte:
                    i, t = parte.strip().split(":", 1)
                    mm, av = _motivos(t)
                    r["motivos"][i.strip()] = mm
                    r["avisos"] += av
        else:
            resto_rech = resto
        for i, v in ITEM.findall(aceptadas):
            r["aceptadas"].add(i)
            r["valores"][i] = _valor(re.split(r"[;,]", v)[0])
        for i, contenido in ITEM.findall(resto_rech):
            r["rechazadas"].add(i)
            partes = re.split(r"[;,]", contenido, maxsplit=1)
            r["valores"][i] = _valor(partes[0])
            if len(partes) > 1:
                mm, av = _motivos(partes[1])
                r["motivos"][i] = mm
                r["avisos"] += av
        rondas[int(m.group(1))] = r
    return rondas


def revisar(resumen: str, sesion: Dict):
    """(errores, avisos): diferencias entre el resumen y el registro de la sesión."""
    errores, avisos = [], []
    dicho = leer_resumen(resumen)
    for ronda in sesion["rounds"]:
        n = ronda["round"]
        d = dicho.get(n)
        if d is None:
            errores.append(f"falta la ronda {n}")
            continue
        eje = ronda["axis"]
        real_acept = {v["id"] for v in ronda["variations"] if v["decision"] == "accepted"}
        real_rech = {v["id"] for v in ronda["variations"] if v["decision"] == "rejected"}
        if d["aceptadas"] != real_acept:
            errores.append(f"R{n}: aceptadas {sorted(d['aceptadas'])} en vez de {sorted(real_acept)}")
        if d["rechazadas"] != real_rech:
            errores.append(f"R{n}: rechazadas {sorted(d['rechazadas'])} en vez de {sorted(real_rech)}")
        for v in ronda["variations"]:
            i = v["id"]
            if i in d["valores"] and d["valores"][i] != _valor(str(v["params"][eje])):
                errores.append(f"{i}: dice '{d['valores'][i]}' y era '{v['params'][eje]}'")
            if v["decision"] == "rejected" and i in d["motivos"]:
                dichos, reales = set(d["motivos"][i]), set(v["reasons"])
                if dichos - reales:
                    errores.append(f"{i}: motivo de más ({', '.join(sorted(dichos - reales))})")
                if reales - dichos:
                    avisos.append(f"{i}: omite {', '.join(sorted(reales - dichos))}")
        avisos += [f"R{n}: {a}" for a in d["avisos"]]
        libres = {NOMBRES_EJE[p] for p in ronda["planner"].get("free_params", [])}
        if libres and d["azar"] is None:
            avisos.append(f"R{n}: no explica el planificador")          # omitir no es afirmar algo falso
        elif libres and d["azar"] != libres:
            errores.append(f"R{n}: planificador al azar {sorted(d['azar'] or [])} en vez de {sorted(libres)}")
        if not libres and d["azar"]:
            errores.append(f"R{n}: dice que el planificador eligió al azar y no fue así")
    return errores, avisos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--sesiones", default=str(config.SALIDAS / "e2" / "sesiones_simuladas.jsonl"))
    ap.add_argument("--salida", default=None, help="por defecto escribe <csv>_revisado.csv")
    ap.add_argument("--anotador", default="revisión automática (Claude)")
    args = ap.parse_args()

    sesiones = {}
    for linea in Path(args.sesiones).read_text(encoding="utf-8").splitlines():
        if linea.strip():
            s = json.loads(linea)
            sesiones[s["session_id"]] = s
    ruta = Path(args.csv)
    crudo = ruta.read_text(encoding="utf-8-sig")
    delim = csv.Sniffer().sniff(crudo.splitlines()[0], delimiters=",;\t").delimiter
    filas = list(csv.DictReader(crudo.splitlines(True), delimiter=delim))
    contar = {"si": 0, "no": 0, "plantilla": 0}
    for f in filas:
        if str(f["plantilla"]).strip().lower() == "true":
            contar["plantilla"] += 1
            continue
        errores, avisos = revisar(f["resumen"], sesiones[f["sesion"]])
        f["fiel_segun_revision_manual"] = "no" if errores else "si"
        f["anotador"] = args.anotador
        f["notas"] = " | ".join(errores) + ((" || avisos: " + " | ".join(avisos)) if avisos else "")
        contar[f["fiel_segun_revision_manual"]] += 1
        print(f["sesion"], f["fiel_segun_revision_manual"], f["notas"][:200])
    salida = Path(args.salida) if args.salida else ruta.with_name(ruta.stem + "_revisado.csv")
    with open(salida, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]), delimiter=delim)
        w.writeheader()
        w.writerows(filas)
    llm = contar["si"] + contar["no"]
    print(f"\n{llm} resúmenes del LLM: {contar['si']} fieles, {contar['no']} con errores "
          f"({contar['si'] / max(llm, 1):.0%} fieles); {contar['plantilla']} de plantilla sin revisar -> {salida}")


if __name__ == "__main__":
    main()
