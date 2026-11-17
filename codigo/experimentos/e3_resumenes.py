"""E3: evaluación de los resúmenes del agente de explicación.

Para cada LLM (Qwen2.5-7B y Phi-3.5-mini) resume N sesiones y mide:
- aprobación del validador al primer intento;
- tasa de resumen por plantilla (fallaron los reintentos);
- intentos y latencia.
Deja además un CSV para la anotación manual de fidelidad (columna `fiel_segun_revision_manual`,
a mano, sin IA: es la parte interpretativa que el validador no cubre).

Entrada: sesiones simuladas de E2 (salidas/e2/sesiones_simuladas.jsonl; se generan con
`python -m experimentos.e2_simulacion`) y, cuando existan, sesiones reales de E4 (--sesiones ruta.jsonl).

Uso (Colab con GPU; en una T4 se carga un LLM a la vez):
    python -m experimentos.e3_resumenes --llm qwen2.5-7b phi-3.5-mini --n 30
    python -m experimentos.e3_resumenes --sin-gpu      # prueba el flujo sin LLM (todo cae a plantilla)
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np

from portadas import config
from portadas.agentes.llm import MODELOS
from portadas.agentes.resumen import resumir


def cargar(ruta: Path, n: int):
    sesiones = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
    return sesiones[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sesiones", default=str(config.SALIDAS / "e2" / "sesiones_simuladas.jsonl"))
    ap.add_argument("--llm", nargs="+", default=list(MODELOS))
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--salida", default=str(config.SALIDAS / "e3"))
    ap.add_argument("--sin-gpu", action="store_true", help="no carga LLM (prueba del flujo en CPU)")
    args = ap.parse_args()

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    sesiones = cargar(Path(args.sesiones), args.n)
    print(f"[E3] {len(sesiones)} sesiones")

    filas, resumen = [], {}
    for nombre in (["sin-llm"] if args.sin_gpu else args.llm):
        if args.sin_gpu:
            llm, liberar = (lambda sistema, mensaje: ""), (lambda: None)
        else:
            from portadas.agentes.llm import LLMLocal
            modelo = LLMLocal(nombre)
            llm, liberar = modelo, modelo.liberar
        res = []
        for i, s in enumerate(sesiones):
            t0 = time.time()
            r = resumir(s, llm)
            r["latencia_s"] = round(time.time() - t0, 2)
            res.append(r)
            plantilla = r["origen"] == "plantilla"
            filas.append({"llm": nombre, "sesion": s.get("session_id", i), "validado": not plantilla,
                          "primer_intento": not plantilla and r["intentos"] == 1, "plantilla": plantilla,
                          "intentos": r["intentos"], "latencia_s": r["latencia_s"],
                          "errores": json.dumps(r["errores"], ensure_ascii=False), "resumen": r["texto"],
                          "fiel_segun_revision_manual": "", "anotador": "", "notas": ""})
            print(f"[E3] {nombre} {i + 1}/{len(sesiones)} origen={r['origen']} intentos={r['intentos']}")
        resumen[nombre] = {
            "n": len(res),
            "aprobacion_primer_intento": float(np.mean([r["origen"] == "llm" and r["intentos"] == 1 for r in res])),
            "tasa_plantilla": float(np.mean([r["origen"] == "plantilla" for r in res])),
            "intentos_medios": float(np.mean([r["intentos"] for r in res])),
            "latencia_media_s": float(np.mean([r["latencia_s"] for r in res])),
        }
        liberar()

    (salida / "e3_resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(salida / "e3_resumenes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(f"[E3] Pendiente manual: completar fiel_segun_revision_manual (si/no) en {salida / 'e3_resumenes.csv'}")


if __name__ == "__main__":
    main()
