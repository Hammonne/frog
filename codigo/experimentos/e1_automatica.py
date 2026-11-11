"""E1. Evaluación automática (sección 11, etapa 3).

- Motor A: para cada par boceto (D2) + historia (D4), una ronda con eje estilo y otra
  con eje paleta (200 x 5 x 2 = 2 000 portadas).
- Motor B (SD-Turbo, gratuito): una ronda con eje estilo en los mismos pares (1 000 portadas).
Guarda el avance par por par en `progreso.jsonl`: si Colab se desconecta, al volver a
correr el mismo comando continúa donde quedó.
Calcula las métricas de la Tabla 4 que dependen solo de la imagen y escribe un CSV por
imagen, un CSV por ronda y un resumen con el cumplimiento de cada criterio.

Uso (Colab con GPU):
    python -m experimentos.e1_automatica --pares 200 --pares-b 200
    python -m experimentos.e1_automatica --pares 5 --pares-b 5 --salida salidas/e1_prueba   # prueba rápida
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from portadas import config
from portadas.datos.historias import emparejar
from portadas.guardrails.salida import RevisorSalida
from portadas.metricas.bordes import densidad_bordes, f1_bordes
from portadas.metricas.color import adherencia_paleta
from portadas.motores.generar import generar_ronda
from portadas.motores.prompts import escena_desde_elementos
from portadas.preprocesamiento import preparar_boceto


def cargar_pares(d2: Path, d4: Path, elementos: Optional[Path] = None) -> List[Dict]:
    indice = json.loads((d2 / "indice.json").read_text(encoding="utf-8"))
    historias = [json.loads(l) for l in (d4 / "historias.jsonl").read_text(encoding="utf-8").splitlines() if l]
    pares = emparejar(historias, indice)
    # Elementos extraídos por el agente de historia (etapa 5), si ya existen.
    extra = {}
    if elementos and elementos.exists():
        for l in elementos.read_text(encoding="utf-8").splitlines():
            if l:
                d = json.loads(l)
                extra[d["id"]] = d["elementos"]
    for p in pares:
        p["elementos"] = extra.get(p["historia"]["id"],
                                   {"personajes": [p["historia"]["categoria"]], "objetos": []})
    return pares


def metricas_imagen(v: Dict, img: Image.Image, boceto, clip, elementos: Dict, hed=None) -> Dict:
    zona = v["params"]["P6"]
    arriba, abajo = config.ZONAS_TITULO[zona]["reserva"]
    y0, y1 = (0, int(img.height * arriba)) if arriba else (int(img.height * (1 - abajo)), img.height)
    m = f1_bordes(boceto.lineas, img, detector=hed)
    estilo = clip.estilo_predicho(img)
    fila = {
        "clipscore": clip.clipscore(img, v["prompt"]),
        "estilo_predicho": estilo,
        "acierto_estilo": float(estilo == v["params"]["P1"]),
        "acierto_paleta": float(adherencia_paleta(img, v["params"]["P2"])),
        "recall_boceto": m["recall"],
        "f1_boceto": m["f1"],
        "densidad_zona_titulo": densidad_bordes(img, y0, y1) if y1 > y0 else None,
    }
    objetivos = list(elementos.get("personajes", [])) + list(elementos.get("objetos", []))
    if objetivos:
        det = clip.elementos_detectados(img, objetivos)
        principal = elementos.get("personajes", objetivos)[0] if elementos.get("personajes") else objetivos[0]
        fila["elemento_principal_detectado"] = float(det.get(principal, False))
        fila["frac_elementos_detectados"] = float(np.mean(list(det.values())))
    return fila


def leer_progreso(ruta: Path) -> Dict[str, Dict]:
    hechos = {}
    if ruta.exists():
        for l in ruta.read_text(encoding="utf-8").splitlines():
            if l:
                d = json.loads(l)
                hechos[d["clave"]] = d
    return hechos


def correr(pares: List[Dict], motor, eje: str, carpeta: Path, clip, lp, revisor, hed=None,
           progreso: Optional[Path] = None) -> Tuple[List[Dict], List[Dict]]:
    filas_img, filas_ronda = [], []
    hechos = leer_progreso(progreso) if progreso else {}
    for k, par in enumerate(pares):
        h, b = par["historia"], par["boceto"]
        clave = f"{motor.nombre}|{eje}|{h['id']}"
        if clave in hechos:
            filas_img += hechos[clave]["filas_img"]
            filas_ronda.append(hechos[clave]["fila_ronda"])
            continue
        boceto = preparar_boceto(Image.open(par["_ruta_boceto"]), zona_titulo="superior")
        escena = escena_desde_elementos(par["elementos"])
        ronda = generar_ronda(boceto, dict(config.POR_DEFECTO), eje, {motor.nombre: motor},
                              motor_preferido=motor.nombre, escena=escena, revisor=revisor)
        imgs = []
        for v in ronda["variations"]:
            img = v.pop("image")
            fila = {"par": h["id"], "boceto": b["archivo"], "motor": motor.nombre, "eje": eje,
                    "id": v["id"], **{f"param_{p}": x for p, x in v["params"].items()},
                    "latencia_s": v["latency_s"], "guardrail": v["guardrails"]["output"],
                    "regeneraciones": v["guardrails"]["regenerations"]}
            if img is not None:
                ruta = carpeta / f"{motor.nombre}_{eje}_{h['id']}_{v['id']}.png"
                img.save(ruta)
                fila["imagen"] = str(ruta)
                fila.update(metricas_imagen(v, img, boceto, clip, par["elementos"], hed))
                imgs.append(img)
            filas_img.append(fila)
        fila_ronda = {"par": h["id"], "motor": motor.nombre, "eje": eje,
                      "latencia_ronda_s": ronda["latency_round_s"],
                      "lpips_medio": lp.diversidad_ronda(imgs) if len(imgs) >= 2 else None,
                      "bloqueadas": 5 - len(imgs)}
        filas_ronda.append(fila_ronda)
        if progreso:
            nuevas = [f for f in filas_img if f["par"] == h["id"] and f["motor"] == motor.nombre and f["eje"] == eje]
            with open(progreso, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"clave": clave, "filas_img": nuevas, "fila_ronda": fila_ronda}) + "\n")
        print(f"[E1] motor {motor.nombre} eje {eje}: {k + 1}/{len(pares)}")
    return filas_img, filas_ronda


def resumen_criterios(filas: List[Dict], rondas: List[Dict], umbral_densidad: Optional[float]) -> Dict:
    def media(clave, sel=None):
        x = [f[clave] for f in (sel or filas) if f.get(clave) is not None]
        return float(np.mean(x)) if x else None

    out = {}
    for motor in sorted({f["motor"] for f in filas}):
        sel = [f for f in filas if f["motor"] == motor]
        rs = [r for r in rondas if r["motor"] == motor]
        estilo = [f for f in sel if f["eje"] == "P1"]
        paleta = [f for f in sel if f["eje"] == "P2"]
        lat = [r["latencia_ronda_s"] for r in rs]
        r = {
            "n_imagenes": len(sel),
            "clipscore_medio": media("clipscore", sel),
            "acierto_estilo_eje_estilo": media("acierto_estilo", estilo),
            "acierto_paleta_eje_paleta": media("acierto_paleta", paleta),
            "recall_boceto_medio": media("recall_boceto", sel),
            "elemento_principal_detectado": media("elemento_principal_detectado", sel),
            "lpips_medio": float(np.mean([x["lpips_medio"] for x in rs if x["lpips_medio"] is not None])) if rs else None,
            "latencia_ronda_media_s": float(np.mean(lat)) if lat else None,
            "latencia_ronda_p90_s": float(np.percentile(lat, 90)) if lat else None,
            "bloqueadas": int(sum(x["bloqueadas"] for x in rs)),
        }
        dens = [f["densidad_zona_titulo"] for f in sel if f.get("densidad_zona_titulo") is not None]
        if umbral_densidad is not None and dens:
            r["frac_zona_titulo_ok"] = float(np.mean([d <= umbral_densidad for d in dens]))
        r["criterios"] = {
            "estilo >= 70 %": r["acierto_estilo_eje_estilo"] is not None and r["acierto_estilo_eje_estilo"] >= 0.70,
            "paleta >= 80 %": r["acierto_paleta_eje_paleta"] is not None and r["acierto_paleta_eje_paleta"] >= 0.80,
            "elemento principal >= 80 %": (r["elemento_principal_detectado"] or 0) >= 0.80,
            "latencia < 60 s (A)": motor != "A" or (r["latencia_ronda_media_s"] or 1e9) < 60,
        }
        out[motor] = r
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d2", default=str(config.DATOS / "d2_quickdraw"))
    ap.add_argument("--d4", default=str(config.DATOS / "d4_historias"))
    ap.add_argument("--d1", default=str(config.DATOS / "d1_portadas" / "img"))
    ap.add_argument("--eda", default=str(config.SALIDAS / "eda" / "resumen_d1.json"))
    ap.add_argument("--elementos", default=None, help="JSONL del agente de historia (opcional)")
    ap.add_argument("--pares", type=int, default=200)
    ap.add_argument("--pares-b", type=int, default=200)
    ap.add_argument("--salida", default=str(config.SALIDAS / "e1"))
    ap.add_argument("--sin-kid", action="store_true")
    args = ap.parse_args()

    from portadas.metricas.clip_metricas import EvaluadorCLIP
    from portadas.metricas.diversidad import EvaluadorLPIPS, kid_fid

    salida = Path(args.salida)
    (salida / "img").mkdir(parents=True, exist_ok=True)
    d2 = Path(args.d2)
    pares = cargar_pares(d2, Path(args.d4), Path(args.elementos) if args.elementos else None)[:args.pares]
    for p in pares:
        p["_ruta_boceto"] = d2 / p["boceto"]["archivo"]

    clip = EvaluadorCLIP()
    lp = EvaluadorLPIPS()
    revisor = RevisorSalida(clip)
    try:
        from controlnet_aux import HEDdetector
        hed = HEDdetector.from_pretrained("lllyasviel/Annotators")
    except Exception:
        hed = None

    filas, rondas = [], []
    if args.pares:
        from portadas.motores.motor_a import MotorA
        motor_a = MotorA()
        for eje in ("P1", "P2"):
            f, r = correr(pares, motor_a, eje, salida / "img", clip, lp, revisor, hed,
                          progreso=salida / "progreso.jsonl")
            filas += f
            rondas += r
        del motor_a
    if args.pares_b:
        from portadas.motores.motor_b import MotorB
        motor_b = MotorB()
        f, r = correr(pares[:args.pares_b], motor_b, "P1", salida / "img", clip, lp, revisor, hed,
                      progreso=salida / "progreso.jsonl")
        filas += f
        rondas += r

    _csv(filas, salida / "e1_imagenes.csv")
    _csv(rondas, salida / "e1_rondas.csv")
    umbral = None
    if Path(args.eda).exists():
        umbral = json.loads(Path(args.eda).read_text())["umbral_densidad_titulo"]
    resumen = resumen_criterios(filas, rondas, umbral)

    if not args.sin_kid and Path(args.d1).exists():
        reales = [Image.open(p).convert("RGB").resize((299, 299)) for p in sorted(Path(args.d1).glob("*.jpg"))[:1000]]
        for motor in resumen:
            gen = [Image.open(f["imagen"]).convert("RGB").resize((299, 299))
                   for f in filas if f["motor"] == motor and f.get("imagen")][:1000]
            if len(gen) >= 50 and len(reales) >= 50:
                resumen[motor].update(kid_fid(reales, gen))
    (salida / "e1_resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


def _csv(filas: List[Dict], ruta: Path) -> None:
    if not filas:
        return
    campos = list(dict.fromkeys(k for f in filas for k in f))
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)


if __name__ == "__main__":
    main()
