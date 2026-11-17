"""Calibración del motor B (SD-Turbo img2img).

En la E1 el motor B casi copió el boceto: acierto de estilo 20 %, recall de bordes 0.98,
27 % de imágenes bloqueadas. Con 4 pasos y strength 0.5-0.9 solo se ejecutan 2-3 pasos
de difusión sobre un trazo negro nítido, y el modelo apenas repinta.

Barrido: strength x pasos x desenfoque del boceto de partida, sobre bocetos de D2
(uno por categoría; el estilo rota entre los 5). Mide el acierto de estilo (CLIP), el
recall de bordes (¿sigue respetando el boceto?), el CLIPScore, la tasa de bloqueo del
guardrail de salida y la latencia. Guarda además una lámina para revisar a ojo.

Uso (Colab con GPU), unos minutos:
    python -m experimentos.calibracion_b --n 10
    # segundo barrido, más fino (strength y pasos a elección):
    python -m experimentos.calibracion_b --n 10 --pasos 10 16 20 --strengths 0.7 0.75 0.8 0.85 0.9 --suavizados 0
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

from portadas import config
from portadas.motores.base import Peticion
from portadas.motores.prompts import construir_prompt
from portadas.preprocesamiento import preparar_boceto

STRENGTHS = [0.80, 0.85, 0.90, 0.95]
PASOS = [4, 6, 8]
SUAVIZADOS = [0.0, 2.0]


def elegir_mejor(resumen: Dict[Tuple[float, int, float], Dict[str, float]],
                 estilo_min: float = 0.70, recall_min: float = 0.30,
                 bloqueo_max: float = 0.05) -> Optional[Tuple[float, int, float]]:
    """Entre las combinaciones (strength, pasos, suavizado) que conservan el estilo,
    el boceto y casi no se bloquean, elige la de mayor recall (más fiel al dibujo).
    Si ninguna cumple todo, devuelve None: el hallazgo se reporta y se decide a mano."""
    validas = [k for k, m in resumen.items()
               if m["acierto_estilo"] >= estilo_min and m["recall"] >= recall_min
               and m["bloqueo"] <= bloqueo_max]
    if not validas:
        return None
    return max(validas, key=lambda k: (resumen[k]["recall"], -resumen[k]["latencia_s"]))


def resumir(filas: List[Dict]) -> Dict[Tuple[float, int, float], Dict[str, float]]:
    resumen = {}
    claves = sorted({(f["strength"], f["pasos"], f["suavizado"]) for f in filas})
    for k in claves:
        sel = [f for f in filas if (f["strength"], f["pasos"], f["suavizado"]) == k]
        resumen[k] = {
            "recall": float(np.mean([f["recall"] for f in sel])),
            "acierto_estilo": float(np.mean([f["acierto_estilo"] for f in sel])),
            "clipscore": float(np.mean([f["clipscore"] for f in sel])),
            "bloqueo": float(np.mean([f["bloqueada"] for f in sel])),
            "latencia_s": float(np.mean([f["latencia_s"] for f in sel])),
            "n": len(sel),
        }
    return resumen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d2", default=str(config.DATOS / "d2_quickdraw"))
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--salida", default=str(config.SALIDAS / "calibracion_b"))
    ap.add_argument("--strengths", type=float, nargs="+", default=STRENGTHS)
    ap.add_argument("--pasos", type=int, nargs="+", default=PASOS)
    ap.add_argument("--suavizados", type=float, nargs="+", default=SUAVIZADOS)
    args = ap.parse_args()

    from portadas.guardrails.salida import RevisorSalida
    from portadas.metricas.bordes import f1_bordes
    from portadas.metricas.clip_metricas import EvaluadorCLIP
    from portadas.motores.motor_b import MotorB

    salida = Path(args.salida)
    (salida / "img").mkdir(parents=True, exist_ok=True)
    indice = json.loads((Path(args.d2) / "indice.json").read_text())
    por_cat: Dict[str, List[Dict]] = {}
    for b in indice:
        por_cat.setdefault(b["categoria"], []).append(b)
    elegidos = [b for lista in por_cat.values() for b in lista[:max(1, args.n // len(por_cat))]][:args.n]

    try:
        from controlnet_aux import HEDdetector
        hed = HEDdetector.from_pretrained("lllyasviel/Annotators")
    except Exception:
        hed = None
        print("[calibración B] sin HED: se usa Canny para la métrica de bordes")

    motor = MotorB()
    clip = EvaluadorCLIP()
    revisor = RevisorSalida(clip)
    estilos = list(config.ESTILOS)
    filas: List[Dict] = []
    muestras: Dict[Tuple[int, float, int, float], Image.Image] = {}   # para la lámina

    for i, b in enumerate(elegidos):
        boceto = preparar_boceto(Image.open(Path(args.d2) / b["archivo"]), zona_titulo="superior")
        estilo = estilos[i % len(estilos)]
        cfg = {**config.POR_DEFECTO, "P1": estilo}
        pr = construir_prompt(cfg, escena=f"a {b['categoria']}")
        for suav, pasos in itertools.product(args.suavizados, args.pasos):
            motor.suavizado, motor.pasos = suav, pasos
            peticiones = [Peticion(id=f"{i}-{s}", params=cfg, prompt=pr["prompt"], negativo=pr["negativo"],
                                   semilla=config.SEMILLA_GLOBAL + i, escala_control=s, pasos=config.PASOS)
                          for s in args.strengths]
            for res in motor.generar(boceto.lineas, peticiones):
                s = res.peticion.escala_control
                m = f1_bordes(boceto.lineas, res.imagen, detector=hed)
                rev = revisor.revisar(res.imagen, res.nsfw_sd)
                filas.append({
                    "boceto": b["archivo"], "categoria": b["categoria"], "estilo": estilo,
                    "strength": s, "pasos": pasos, "suavizado": suav,
                    "recall": m["recall"], "f1": m["f1"],
                    "acierto_estilo": float(clip.estilo_predicho(res.imagen) == estilo),
                    "clipscore": clip.clipscore(res.imagen, pr["prompt"]),
                    "p_no_apto": rev.prob_no_apto, "bloqueada": float(not rev.ok),
                    "latencia_s": res.latencia_s,
                })
                if i < 3:   # imágenes de los 3 primeros bocetos para revisar a ojo
                    muestras[(i, suav, pasos, s)] = res.imagen
        print(f"[calibración B] {i + 1}/{len(elegidos)}")

    with open(salida / "calibracion_b.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    resumen = resumir(filas)
    mejor = elegir_mejor(resumen)
    propuesta = ({"strength_base": mejor[0], "pasos": mejor[1], "suavizado": mejor[2]}
                 if mejor else None)
    (salida / "resumen.json").write_text(json.dumps({
        "resumen": [{"strength": k[0], "pasos": k[1], "suavizado": k[2], **v} for k, v in resumen.items()],
        "propuesta": propuesta,
        "nota": None if mejor else "Ninguna combinación cumple estilo, recall y bloqueo: revisar la lámina.",
    }, indent=2), encoding="utf-8")
    _tabla_consola(resumen, mejor)
    _lamina(muestras, [elegidos[i]["categoria"] for i in range(min(3, len(elegidos)))],
            args.strengths, salida / "lamina_b.png")


def _tabla_consola(resumen, mejor):
    print(f"{'strength':>8} {'pasos':>5} {'suav':>5} | {'estilo':>6} {'recall':>6} {'clip':>5} {'bloq':>5} {'s':>5}")
    for k, m in resumen.items():
        marca = "  <-- propuesta" if k == mejor else ""
        print(f"{k[0]:8.2f} {k[1]:5d} {k[2]:5.1f} | {m['acierto_estilo']:6.2f} {m['recall']:6.2f} "
              f"{m['clipscore']:5.2f} {m['bloqueo']:5.2f} {m['latencia_s']:5.2f}{marca}")
    if mejor is None:
        print("Ninguna combinación cumple estilo >= 0.70, recall >= 0.30 y bloqueo <= 5 %.")


def _lamina(muestras, categorias, strengths, ruta):
    """Una fila por (boceto, suavizado, pasos); una columna por strength."""
    if not muestras:
        return
    w, h = 128, 192
    filas = sorted({(i, sv, p) for (i, sv, p, _) in muestras})
    hoja = Image.new("RGB", (150 + len(strengths) * (w + 4), 24 + len(filas) * (h + 4)), "white")
    d = ImageDraw.Draw(hoja)
    for j, s in enumerate(strengths):
        d.text((150 + j * (w + 4), 6), f"strength {s}", fill="black")
    for r, (i, sv, p) in enumerate(filas):
        y = 24 + r * (h + 4)
        d.text((4, y + 4), f"{categorias[i]}\nsuav {sv}\npasos {p}", fill="black")
        for j, s in enumerate(strengths):
            img = muestras.get((i, sv, p, s))
            if img is not None:
                hoja.paste(img.resize((w, h)), (150 + j * (w + 4), y))
    hoja.save(ruta)


if __name__ == "__main__":
    main()
