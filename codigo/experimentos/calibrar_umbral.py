"""Calibración del umbral de CLIP con imágenes de los dos motores (sin bloquear ninguna).

Por qué: el umbral se fijó con E5 (45 imágenes del motor A con un solo boceto). En E1 el filtro con
umbral 0.5 bloqueó 269 de 1 000 portadas del motor B y 1 de 2 000 del A. No sabemos si esas 269 eran de
verdad no aptas o falsos positivos, porque las bloqueadas no se guardaron. Este script genera
portadas con cada motor SIN filtro, calcula la probabilidad de "no apto" de cada una y guarda para
revisión manual todas las que pasarían a bloquearse con el umbral actual o con el anterior.

Salida (salidas/calibracion_umbral/):
  p_no_apto.csv   una fila por imagen: motor, par, id, p_no_apto, descriptor, imagen
  revision_manual.csv   las imágenes con p >= 0.15, con la columna `apta_segun_revision_manual` (si/no)
                        y `anotador` para completar a mano
  resumen.json    por motor, fracción de imágenes que se bloquearía con cada umbral

Uso (Colab con GPU):
    python -m experimentos.calibrar_umbral --pares 40
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image

from portadas import config
from portadas.guardrails.salida import RevisorSalida
from portadas.motores.generar import generar_ronda
from portadas.motores.prompts import escena_desde_elementos
from portadas.preprocesamiento import preparar_boceto

from .e1_automatica import cargar_pares

UMBRALES = (0.15, 0.2, 0.25, 0.3, 0.4, 0.5)
MINIMO_REVISION = 0.15


def _csv(filas, ruta: Path) -> None:
    with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d2", default=str(config.DATOS / "d2_quickdraw"))
    ap.add_argument("--d4", default=str(config.DATOS / "d4_historias"))
    ap.add_argument("--pares", type=int, default=40, help="pares boceto+historia por motor (5 portadas cada uno)")
    ap.add_argument("--salida", default=str(config.SALIDAS / "calibracion_umbral"))
    args = ap.parse_args()

    from portadas.metricas.clip_metricas import EvaluadorCLIP
    from portadas.motores.motor_a import MotorA
    from portadas.motores.motor_b import MotorB

    salida = Path(args.salida)
    (salida / "img").mkdir(parents=True, exist_ok=True)
    d2 = Path(args.d2)
    pares = cargar_pares(d2, Path(args.d4))
    paso = max(1, len(pares) // args.pares)               # pares repartidos por todas las categorías
    pares = pares[::paso][:args.pares]
    revisor = RevisorSalida(EvaluadorCLIP())              # solo para medir, nunca para bloquear aquí

    filas = []
    for nombre, clase, eje in (("A", MotorA, "P1"), ("B", MotorB, "P1")):
        motor = clase()
        for k, par in enumerate(pares):
            h = par["historia"]
            boceto = preparar_boceto(Image.open(d2 / par["boceto"]["archivo"]), zona_titulo="superior")
            ronda = generar_ronda(boceto, dict(config.POR_DEFECTO), eje, {nombre: motor}, motor_preferido=nombre,
                                  escena=escena_desde_elementos(par["elementos"]))
            for v in ronda["variations"]:
                img = v.pop("image")
                if img is None:
                    continue
                r = revisor.revisar(img)
                ruta = salida / "img" / f"{nombre}_{h['id']}_{v['id']}.png"
                img.save(ruta)
                filas.append({"motor": nombre, "par": h["id"], "id": v["id"], "estilo": v["params"]["P1"],
                              "p_no_apto": round(r.prob_no_apto, 4), "descriptor": r.descriptor,
                              "imagen": ruta.name})
            print(f"[calibracion] {nombre} {k + 1}/{len(pares)}")
        del motor

    _csv(filas, salida / "p_no_apto.csv")
    revisar = sorted((f for f in filas if f["p_no_apto"] >= MINIMO_REVISION), key=lambda f: -f["p_no_apto"])
    if revisar:
        _csv([{**f, "apta_segun_revision_manual": "", "anotador": ""} for f in revisar],
             salida / "revision_manual.csv")
    resumen = {"pares": len(pares), "imagenes_a_revisar": len(revisar)}
    for m in ("A", "B"):
        p = np.array([f["p_no_apto"] for f in filas if f["motor"] == m])
        resumen[m] = {"n": int(len(p)), "mediana_p": float(np.median(p)) if len(p) else None,
                      "pct_bloqueada_con_umbral": {str(u): round(float((p >= u).mean()), 3) for u in UMBRALES}}
    (salida / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(f"[calibracion] Pendiente manual: completar apta_segun_revision_manual en {salida / 'revision_manual.csv'}")


if __name__ == "__main__":
    main()
