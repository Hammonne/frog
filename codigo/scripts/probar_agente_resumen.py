"""Prueba del agente de resumen con los LLM reales (Colab con GPU).

Arma una sesión simulada de 2 rondas con decisiones y motivos, y pide el resumen a cada
modelo. Imprime el texto, si lo aprobó el validador (y en cuántos intentos) y los errores
que encontró. Sirve también para comparar Qwen2.5-7B con Phi-3.5-mini.

Uso:
    python -m scripts.probar_agente_resumen                   # los dos modelos
    python -m scripts.probar_agente_resumen --modelo phi-3.5-mini
"""
from __future__ import annotations

import argparse
import time

from portadas import config
from portadas.agentes.resumen import hechos, resumir, validar, separar_bloque
from portadas.planificador import Sesion

DECISIONES_R1 = [("accepted", [], ""), ("rejected", ["colores"], "muy oscuro"), ("accepted", [], ""),
                 ("rejected", [], ""), ("accepted", [], "")]
DECISIONES_R2 = [("accepted", [], ""), ("accepted", [], ""), ("rejected", ["ambiente"], "da miedo"),
                 ("accepted", [], ""), ("rejected", [], "")]


def sesion_ejemplo() -> dict:
    s = Sesion(dict(config.POR_DEFECTO), semilla=7)
    for eje, decisiones in (("P1", DECISIONES_R1), ("P2", DECISIONES_R2)):
        plan = s.configs_ronda(eje)
        variaciones = []
        for i, (cfg, (dec, motivos, comentario)) in enumerate(zip(plan["configs"], decisiones), start=1):
            variaciones.append({"id": f"R{s.numero}-V{i}", "params": cfg, "decision": dec,
                                "reasons": motivos, "reason": comentario})
        s.cerrar_ronda({"round": s.numero, "axis": eje, "variations": variaciones})
    return {"rounds": s.rondas,
            "story": {"personajes": ["rabbit"], "objetos": ["flowers"], "lugar": "garden"},
            "typography_changes": [{"id": "R2-V1", "cambio": "fuente: Andika"}]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default=None, choices=["qwen2.5-7b", "phi-3.5-mini"])
    args = ap.parse_args()
    sesion = sesion_ejemplo()
    modelos = [args.modelo] if args.modelo else ["qwen2.5-7b", "phi-3.5-mini"]

    from portadas.agentes.llm import LLMLocal
    for nombre in modelos:
        t0 = time.perf_counter()
        llm = LLMLocal(nombre)
        print(f"\n===== {nombre} (cargado en {time.perf_counter() - t0:.0f} s) =====")
        inicio = time.perf_counter()
        r = resumir(sesion, llm)
        print(f"({time.perf_counter() - inicio:.1f} s, origen={r['origen']}, intentos={r['intentos']})")
        print(r["texto"])
        for n, (errores, borrador) in enumerate(zip(r["errores"], r["borradores"]), start=1):
            print(f"\n  --- intento {n}: {'OK' if not errores else errores}")
            print("  " + borrador.replace("\n", "\n  "))
        llm.liberar()


if __name__ == "__main__":
    main()
