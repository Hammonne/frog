"""E2: simulación del planificador (sección 11, etapa 5, Nayeli).

50 usuarios simulados con una preferencia oculta; Thompson frente a elección aleatoria en tres
rondas, con los mismos usuarios en ambas políticas. Se repite 20 veces para dar media y
desviación. Corre en CPU en segundos (no necesita GPU).

Uso:
    python -m experimentos.e2_planificador
    python -m experimentos.e2_planificador --usuarios 50 --repeticiones 20 --ejes P1 P2 P4

Salidas en salidas/e2/: e2_resumen.json, e2_rondas.csv, e2_grafico.png (si hay matplotlib)
y sesiones_simuladas.jsonl (entrada de E3).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from portadas import config
from portadas.agente.simulacion import experimento_e2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--usuarios", type=int, default=config.E2_USUARIOS)
    ap.add_argument("--repeticiones", type=int, default=20)
    ap.add_argument("--ejes", nargs="+", default=list(config.E2_EJES))
    ap.add_argument("--salida", default=str(config.SALIDAS / "e2"))
    args = ap.parse_args()

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    res = experimento_e2(args.usuarios, args.repeticiones, ejes=args.ejes)

    (salida / "e2_resumen.json").write_text(json.dumps(res["resumen"], indent=2, ensure_ascii=False), encoding="utf-8")
    with open(salida / "e2_rondas.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["politica", "repeticion", "ronda", "tasa_aceptacion"])
        for pol, filas in res["filas"].items():
            for rep, tasas in enumerate(filas):
                for r, t in enumerate(tasas, start=1):
                    w.writerow([pol, rep, r, round(t, 4)])
    with open(salida / "sesiones_simuladas.jsonl", "w", encoding="utf-8") as fh:
        for s in res["sesiones"]:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(json.dumps(res["resumen"], indent=2, ensure_ascii=False))
    _grafico(res["resumen"], salida / "e2_grafico.png")


def _grafico(resumen, ruta: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:  # sin matplotlib (o mal instalado) los resultados ya están guardados
        print(f"[E2] sin gráfico: {e}")
        return
    fig, ax = plt.subplots(figsize=(4, 3))
    for pol, nombre in (("thompson", "Thompson"), ("aleatoria", "Aleatoria")):
        m = resumen[pol]["media_por_ronda"]
        de = resumen[pol]["de_por_ronda"] or [0] * len(m)
        x = list(range(1, len(m) + 1))
        ax.errorbar(x, m, yerr=de, marker="o", capsize=3, label=nombre)
    ax.set_xlabel("Ronda")
    ax.set_ylabel("Tasa de aceptación")
    ax.set_xticks(range(1, len(m) + 1))
    ax.set_ylim(0, 1)
    ax.legend()
    fig.tight_layout()
    fig.savefig(ruta, dpi=200)


if __name__ == "__main__":
    main()
