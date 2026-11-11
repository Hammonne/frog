"""Calibración de la fidelidad y de los pasos (sección 7, etapa 3).

Barrido: escala de ControlNet en {0.4, 0.6, ..., 1.4} x pasos en {20, 25, 30} sobre
20 bocetos de D2. El estilo rota entre los 5 para no sesgar el resultado hacia uno.
Métricas: recall de bordes (fidelidad al boceto), acierto de estilo con CLIP y latencia.
Salida: CSV por imagen, resumen por escala y los 5 valores propuestos para la fidelidad.

Uso (Colab con GPU):
    python -m experimentos.calibracion --d2 datos/d2_quickdraw --n 20
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
from PIL import Image

from portadas import config
from portadas.motores.base import Peticion
from portadas.motores.prompts import construir_prompt
from portadas.preprocesamiento import preparar_boceto

ESCALAS = [0.4, 0.6, 0.8, 1.0, 1.2, 1.4]
PASOS = [20, 25, 30]


def proponer_niveles(resumen: Dict[float, Dict[str, float]], recall_min: float = 0.35,
                     estilo_min: float = 0.70) -> List[float]:
    """Elige 5 escalas para muy baja..muy alta dentro de la zona aceptable:
    respeta el boceto (recall >= recall_min) y conserva el estilo (acierto >= estilo_min).
    Si la zona tiene menos de 5 puntos, se interpola dentro de ella."""
    aceptables = sorted(e for e, m in resumen.items()
                        if m["recall"] >= recall_min and m["acierto_estilo"] >= estilo_min)
    if not aceptables:
        # Sin zona aceptable: se prioriza el estilo y se reporta como hallazgo.
        aceptables = sorted(resumen, key=lambda e: -resumen[e]["acierto_estilo"])[:2]
        aceptables.sort()
    lo, hi = aceptables[0], aceptables[-1]
    if hi - lo < 0.2:
        lo, hi = max(0.3, lo - 0.2), hi + 0.2
    return [round(float(x), 2) for x in np.linspace(lo, hi, 5)]


def elegir_pasos(resumen_por_pasos: Dict[int, Dict[float, Dict[str, float]]],
                 tolerancia: float = 0.03) -> int:
    """Menor número de pasos cuya calidad media (recall + estilo) está a menos de
    `tolerancia` de la mejor: más pasos solo se justifican si mejoran el resultado."""
    calidad = {p: float(np.mean([v["recall"] + v["acierto_estilo"] for v in r.values()]))
               for p, r in resumen_por_pasos.items() if r}
    mejor = max(calidad.values())
    return min(p for p, c in calidad.items() if c >= mejor - tolerancia)


def resumir(filas: List[Dict], pasos: int) -> Dict[float, Dict[str, float]]:
    resumen = {}
    for e in sorted({f["escala"] for f in filas}):
        sel = [f for f in filas if f["escala"] == e and f["pasos"] == pasos]
        if sel:
            resumen[e] = {
                "recall": float(np.mean([f["recall"] for f in sel])),
                "f1": float(np.mean([f["f1"] for f in sel])),
                "acierto_estilo": float(np.mean([f["acierto_estilo"] for f in sel])),
                "latencia_s": float(np.mean([f["latencia_s"] for f in sel])),
            }
    return resumen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d2", default=str(config.DATOS / "d2_quickdraw"))
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--salida", default=str(config.SALIDAS / "calibracion"))
    ap.add_argument("--guardar-imagenes", action="store_true")
    args = ap.parse_args()

    from portadas.metricas.bordes import f1_bordes
    from portadas.metricas.clip_metricas import EvaluadorCLIP
    from portadas.motores.motor_a import MotorA

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    indice = json.loads((Path(args.d2) / "indice.json").read_text())
    # 2 bocetos por categoría para cubrir las 10
    por_cat: Dict[str, List[Dict]] = {}
    for b in indice:
        por_cat.setdefault(b["categoria"], []).append(b)
    elegidos = [b for lista in por_cat.values() for b in lista[:max(1, args.n // len(por_cat))]][:args.n]

    try:
        from controlnet_aux import HEDdetector
        hed = HEDdetector.from_pretrained("lllyasviel/Annotators")
    except Exception:
        hed = None
        print("[calibración] sin HED: se usa Canny para la métrica de bordes")

    motor = MotorA()
    clip = EvaluadorCLIP()
    estilos = list(config.ESTILOS)
    filas = []
    for i, b in enumerate(elegidos):
        boceto = preparar_boceto(Image.open(Path(args.d2) / b["archivo"]), zona_titulo="superior")
        estilo = estilos[i % len(estilos)]
        cfg = {**config.POR_DEFECTO, "P1": estilo}
        pr = construir_prompt(cfg, escena=f"a {b['categoria']}")
        for pasos in PASOS:
            peticiones = [Peticion(id=f"{i}-{pasos}-{e}", params=cfg, prompt=pr["prompt"],
                                   negativo=pr["negativo"], semilla=config.SEMILLA_GLOBAL + i,
                                   escala_control=e, pasos=pasos) for e in ESCALAS]
            for res in motor.generar(boceto.control, peticiones):
                m = f1_bordes(boceto.lineas, res.imagen, detector=hed)
                fila = {"boceto": b["archivo"], "categoria": b["categoria"], "estilo": estilo,
                        "escala": res.peticion.escala_control, "pasos": pasos,
                        "recall": m["recall"], "precision": m["precision"], "f1": m["f1"],
                        "acierto_estilo": float(clip.estilo_predicho(res.imagen) == estilo),
                        "clipscore": clip.clipscore(res.imagen, pr["prompt"]),
                        "latencia_s": res.latencia_s, "nsfw_sd": res.nsfw_sd}
                filas.append(fila)
                if args.guardar_imagenes:
                    res.imagen.save(salida / f"{Path(b['archivo']).stem}_{pasos}_{res.peticion.escala_control}.png")
        print(f"[calibración] {i + 1}/{len(elegidos)}")

    with open(salida / "calibracion.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    resumen = {p: resumir(filas, p) for p in PASOS}
    pasos_elegidos = elegir_pasos(resumen)
    propuesta = {"pasos": pasos_elegidos, "fidelidad": dict(zip(config.FIDELIDAD, proponer_niveles(resumen[pasos_elegidos])))}
    (salida / "resumen.json").write_text(json.dumps({"resumen": {str(p): {str(e): v for e, v in r.items()}
                                                                 for p, r in resumen.items()},
                                                     "propuesta": propuesta}, indent=2), encoding="utf-8")
    print(json.dumps(propuesta, indent=2))
    _grafico(resumen, salida / "calibracion.png")


def _grafico(resumen, ruta):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
    for p, r in resumen.items():
        e = sorted(r)
        ax[0].plot(e, [r[x]["recall"] for x in e], marker="o", label=f"{p} pasos")
        ax[1].plot(e, [r[x]["acierto_estilo"] for x in e], marker="o", label=f"{p} pasos")
    ax[0].set(xlabel="escala de ControlNet", ylabel="recall de bordes", title="Fidelidad al boceto")
    ax[1].set(xlabel="escala de ControlNet", ylabel="acierto de estilo (CLIP)", title="Conservación del estilo")
    for a in ax:
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ruta, dpi=200)


if __name__ == "__main__":
    main()
