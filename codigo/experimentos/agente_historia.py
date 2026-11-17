"""Evaluación del agente de historia contra las anotaciones manuales.

Compara los personajes y objetos que extrae cada LLM con las 30 historias anotadas a mano en
inglés (D4) y las 30 en español (D4-es). Reporta precisión, exhaustividad y F1 por idioma y por
LLM (criterio: precisión >= 90 %), y cuántos elementos marcó el verificador como no respaldados.

Requiere que las columnas `personajes` y `objetos` de las plantillas estén llenas
(varios valores separados por ';'). Las filas sin anotar se saltan.

Uso (Colab con GPU):
    python -m experimentos.agente_historia --llm qwen2.5-7b phi-3.5-mini
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from portadas import config
from portadas.agentes.historia import (HistoriaInvalida, evaluar_extraccion, extraer_elementos,
                                       precision_exhaustividad)
from portadas.agentes.llm import MODELOS

PRECISION_MIN = 0.90          # criterio de la tabla de métricas del informe
ANOTACIONES = {
    "en": (config.DATOS / "d4_historias" / "anotacion_30.csv", "texto_en"),
    "es": (config.DATOS / "d4es_historias" / "anotacion_30_es.csv", "texto_es"),
}


def leer_anotadas(ruta: Path):
    with open(ruta, encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    return [f for f in filas if (f.get("personajes") or "").strip() or (f.get("objetos") or "").strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", nargs="+", default=list(MODELOS))
    ap.add_argument("--salida", default=str(config.SALIDAS / "agente_historia"))
    args = ap.parse_args()
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    from portadas.agentes.llm import LLMLocal

    detalle, resumen = [], {}
    for nombre in args.llm:
        llm = LLMLocal(nombre)
        resumen[nombre] = {}
        for idioma, (ruta, col) in ANOTACIONES.items():
            filas = leer_anotadas(ruta)
            total = {"vp": 0, "fp": 0, "fn": 0}
            no_verificados, respaldo = 0, 0
            for f in filas:
                try:
                    e = extraer_elementos(f[col], llm)
                except HistoriaInvalida as err:
                    detalle.append({"llm": nombre, "idioma": idioma, "id": f["id"], "error": f"no válida: {err}"})
                    continue
                c = evaluar_extraccion(e, f, idioma)
                for k in total:
                    total[k] += c[k]
                no_verificados += len(e["no_verificados"])
                respaldo += e["origen"] == "respaldo"
                detalle.append({"llm": nombre, "idioma": idioma, "id": f["id"], **c,
                                "predicho": json.dumps({k: e[k] for k in ("personajes", "objetos", "lugar")},
                                                       ensure_ascii=False),
                                "anotado": f"{f.get('personajes', '')} | {f.get('objetos', '')}",
                                "no_verificados": len(e["no_verificados"])})
            m = precision_exhaustividad(total)
            resumen[nombre][idioma] = {"n_historias": len(filas), **total, **{k: round(v, 4) for k, v in m.items()},
                                       "no_verificados": no_verificados, "respaldo": respaldo,
                                       "cumple_precision": m["precision"] >= PRECISION_MIN}
            print(nombre, idioma, resumen[nombre][idioma])
        llm.liberar()

    (salida / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    if detalle:
        campos = list(dict.fromkeys(k for d in detalle for k in d))
        with open(salida / "detalle.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=campos)
            w.writeheader()
            w.writerows(detalle)


if __name__ == "__main__":
    main()
