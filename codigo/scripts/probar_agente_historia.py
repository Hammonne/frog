"""Prueba del agente de historia con el modelo de lenguaje real (Colab con GPU).

Uso:
    python -m scripts.probar_agente_historia                       # historias de ejemplo
    python -m scripts.probar_agente_historia --modelo phi-3.5-mini
    python -m scripts.probar_agente_historia --historia "Un oso busca miel en el bosque."
Imprime, por historia, los elementos extraídos, los que el verificador no encontró en el
texto y la escena en inglés que se usaría en el prompt.
"""
from __future__ import annotations

import argparse
import json
import time

from portadas.agentes.historia import HistoriaInvalida, escena_ingles, extraer_elementos

EJEMPLOS = [
    "Un conejo que ama las flores vive en un jardin. Cada manana les cuenta chistes a las mariposas.",
    "Una pequena zorra se perdio en el bosque de noche. Una luciernaga la guio hasta su casa.",
    "El dragon Tomas tenia miedo del fuego. Con ayuda de su amiga la tortuga aprendio a cocinar galletas.",
    "Dos peces curiosos nadan hasta el fondo del mar y encuentran un barco antiguo lleno de estrellas de mar.",
    "Una nina y su perro construyen un castillo de arena en la playa al atardecer.",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="qwen2.5-7b", choices=["qwen2.5-7b", "phi-3.5-mini"])
    ap.add_argument("--historia", default=None)
    args = ap.parse_args()

    from portadas.agentes.llm import LLMLocal
    t0 = time.perf_counter()
    llm = LLMLocal(args.modelo)
    print(f"[historia] {args.modelo} cargado en {time.perf_counter() - t0:.0f} s\n")
    for texto in [args.historia] if args.historia else EJEMPLOS:
        print("HISTORIA:", texto)
        inicio = time.perf_counter()
        try:
            e = extraer_elementos(texto, llm)
        except HistoriaInvalida as err:
            print("  rechazada:", err, "\n")
            continue
        print(f"  ({time.perf_counter() - inicio:.1f} s, intentos={e['intentos']}, origen={e['origen']})")
        print("  elementos:", json.dumps({k: e[k] for k in ("personajes", "objetos", "lugar", "momento", "tono", "edad")},
                                         ensure_ascii=False))
        print("  no verificados:", e["no_verificados"] or "ninguno")
        print("  escena:", escena_ingles(e), "\n")


if __name__ == "__main__":
    main()
