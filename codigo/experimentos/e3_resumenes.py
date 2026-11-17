"""E3: evaluación de los resúmenes del agente explicador (sección 11, etapa 5, Nayeli).

Para cada LLM (Qwen2.5-7B y Phi-3.5-mini) resume N sesiones y mide:
- aprobación del validador al primer intento;
- tasa de resumen por plantilla (fallaron los reintentos);
- intentos y latencia.
Deja además un CSV para la anotación manual de fidelidad (columna `fiel_segun_revision_manual`,
a mano, sin IA: es la parte interpretativa que el validador no cubre).

Entrada: sesiones simuladas de E2 (salidas/e2/sesiones_simuladas.jsonl) y, cuando existan,
sesiones reales de E4 (--sesiones otra_ruta.jsonl).

Uso (Colab con GPU; en una T4 se carga un LLM a la vez):
    python -m experimentos.e3_resumenes --llm qwen phi --n 30
    python -m experimentos.e3_resumenes --solo-plantilla      # sin GPU: prueba el flujo
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from portadas import config
from portadas.agente.explicador import explicar


def cargar(ruta: Path, n: int):
    sesiones = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
    return sesiones[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sesiones", default=str(config.SALIDAS / "e2" / "sesiones_simuladas.jsonl"))
    ap.add_argument("--llm", nargs="+", default=list(config.LLMS))
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--salida", default=str(config.SALIDAS / "e3"))
    ap.add_argument("--solo-plantilla", action="store_true", help="no carga LLM (prueba en CPU)")
    args = ap.parse_args()

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    sesiones = cargar(Path(args.sesiones), args.n)
    print(f"[E3] {len(sesiones)} sesiones")

    filas, resumen = [], {}
    for nombre in (["plantilla"] if args.solo_plantilla else args.llm):
        llm = None
        if not args.solo_plantilla:
            from portadas.agente.llm import LLMLocal
            llm = LLMLocal(nombre)
        res = []
        for i, s in enumerate(sesiones):
            r = explicar(s, llm, nombre_llm=nombre)
            res.append(r)
            filas.append({"llm": nombre, "sesion": s.get("session_id", i), "validado": r["validated"],
                          "primer_intento": r["validated"] and r["attempts"] == 1 and not r["template"],
                          "plantilla": r["template"], "intentos": r["attempts"], "latencia_s": r["latency_s"],
                          "errores": json.dumps(r["errors"], ensure_ascii=False), "resumen": r["user_text"],
                          "fiel_segun_revision_manual": "", "anotador": "", "notas": ""})
            print(f"[E3] {nombre} {i + 1}/{len(sesiones)} validado={r['validated']} plantilla={r['template']}")
        resumen[nombre] = {
            "n": len(res),
            "aprobacion_primer_intento": float(np.mean([r["validated"] and r["attempts"] == 1 and not r["template"]
                                                         for r in res])),
            "tasa_plantilla": float(np.mean([r["template"] for r in res])),
            "intentos_medios": float(np.mean([r["attempts"] for r in res])),
            "latencia_media_s": float(np.mean([r["latency_s"] for r in res])),
            "todos_los_mostrados_validados": bool(all(r["validated"] for r in res)),
        }
        if llm is not None:
            llm.liberar()

    (salida / "e3_resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(salida / "e3_resumenes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(f"[E3] Pendiente manual: completar fiel_segun_revision_manual (si/no) en {salida / 'e3_resumenes.csv'}")


if __name__ == "__main__":
    main()
