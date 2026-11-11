"""Primer hito de la etapa 3: una ronda de 5 portadas a partir de un boceto.

Uso (Colab con GPU):
    python -m scripts.demo_ronda --boceto mi_dibujo.jpg --escena "a rabbit among flowers in a garden"
    python -m scripts.demo_ronda --quickdraw rabbit --eje P2 --motor B
Guarda las 5 imágenes, el registro JSON de la ronda y una lámina comparativa.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from portadas import config
from portadas.guardrails.entrada import revisar_imagen_entrada
from portadas.motores.base import MotorNoDisponible
from portadas.motores.generar import generar_ronda, guardar_imagenes
from portadas.preprocesamiento import preparar_boceto

NOMBRES_EJE = {"P1": "Estilo", "P2": "Paleta", "P3": "Edad", "P4": "Ambiente", "P5": "Fidelidad",
               "P6": "Zona del título"}


def lamina(boceto: Image.Image, ronda: dict, ruta: Path) -> None:
    w, h = config.ANCHO // 2, config.ALTO // 2
    hoja = Image.new("RGB", (w * 6 + 70, h + 60), "white")
    d = ImageDraw.Draw(hoja)
    hoja.paste(boceto.convert("RGB").resize((w, h)), (10, 40))
    d.text((10, 12), "Boceto", fill="black")
    for i, v in enumerate(ronda["variations"], start=1):
        x = 10 + i * (w + 10)
        etiqueta = f"{v['id']}  {NOMBRES_EJE[ronda['axis']]}: {v['params'][ronda['axis']]}"
        d.text((x, 12), etiqueta, fill="black")
        if v.get("image_path"):
            hoja.paste(Image.open(v["image_path"]).resize((w, h)), (x, 40))
        else:
            d.rectangle((x, 40, x + w, 40 + h), outline="red")
            d.text((x + 8, 50), "bloqueada: " + ",".join(v["guardrails"]["reasons"]), fill="red")
    hoja.save(ruta)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--boceto")
    g.add_argument("--quickdraw", help="categoría de Quick, Draw! para una prueba rápida")
    ap.add_argument("--eje", default="P1", choices=list(NOMBRES_EJE))
    ap.add_argument("--motor", default="A", choices=["A", "B"])
    ap.add_argument("--escena", default="")
    ap.add_argument("--instruccion", default="")
    ap.add_argument("--zona", default="superior", choices=list(config.ZONAS_TITULO))
    ap.add_argument("--sin-clip", action="store_true", help="omitir la revisión de salida con CLIP")
    ap.add_argument("--salida", default=str(config.SALIDAS / "demo"))
    args = ap.parse_args()

    if args.boceto:
        img = Image.open(args.boceto)
        entrada = revisar_imagen_entrada(img)
        if not entrada.ok:
            raise SystemExit(entrada.motivo)
    else:
        from portadas.datos.quickdraw import descargar_categoria, renderizar
        img = renderizar(descargar_categoria(args.quickdraw, n=1)[0]["drawing"])
        args.escena = args.escena or f"a {args.quickdraw}"
    boceto = preparar_boceto(img, zona_titulo=args.zona)

    motores = {}
    try:
        from portadas.motores.motor_a import MotorA
        motores["A"] = MotorA()
    except MotorNoDisponible as e:
        print(f"[demo] motor A no disponible: {e}")
    try:
        from portadas.motores.motor_b import MotorB
        motores["B"] = MotorB()
    except MotorNoDisponible as e:
        print(f"[demo] motor B no disponible: {e}")

    revisor = None
    if not args.sin_clip:
        from portadas.guardrails.salida import RevisorSalida
        from portadas.metricas.clip_metricas import EvaluadorCLIP
        revisor = RevisorSalida(EvaluadorCLIP())

    base = {**config.POR_DEFECTO, "P6": args.zona}
    ronda = generar_ronda(boceto, base, args.eje, motores, motor_preferido=args.motor,
                          escena=args.escena, instruccion=args.instruccion, revisor=revisor)
    salida = Path(args.salida)
    ronda = guardar_imagenes(ronda, salida)
    boceto.lineas.save(salida / "boceto_preprocesado.png")
    (salida / "ronda.json").write_text(json.dumps(ronda, indent=2, ensure_ascii=False), encoding="utf-8")
    lamina(boceto.lineas, ronda, salida / "lamina.png")
    print(f"[demo] motor {ronda['engine']}, {ronda['latency_round_s']:.1f} s por ronda -> {salida / 'lamina.png'}")


if __name__ == "__main__":
    main()
