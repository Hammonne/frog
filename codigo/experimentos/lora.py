"""Experimento opcional con LoRA (sección 7, etapa 3, Maria).

Compara el motor A con y sin un adaptador LoRA de ilustración infantil, con los mismos
bocetos, prompts y semillas. Antes de cargar el LoRA se revisa su ficha en Hugging Face:
- licencia en la lista permitida (uso académico);
- modelo base SD 1.5 (los LoRA de SDXL no son compatibles);
- sin nombres de artistas ni pedidos de imitar un estilo ajeno (misma lista que el guardrail de texto);
- se registra si la ficha documenta sus datos de entrenamiento (si no, es una limitación a reportar).

Métricas por imagen: acierto de estilo (CLIP), CLIPScore, F1 de bordes con el boceto,
cuánto cambia la imagen respecto de la base (LPIPS), latencia y filtro NSFW de SD.

Uso (Colab con GPU):
    python -m experimentos.lora --revisar                 # solo revisa la ficha del LoRA
    python -m experimentos.lora --n 20                    # experimento completo (~20 min en T4)
    python -m experimentos.lora --lora usuario/otro-lora --peso archivo.safetensors --disparador "x style"
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from portadas import config

# Candidato por defecto: SD 1.5, OpenRAIL-M, palabra clave inventada (no un artista).
LORA_POR_DEFECTO = {
    "repo": "alvdansen/dimension-w-sd15",
    "peso": "araminta_k_dimension_w_sd15.safetensors",
    "disparador": "daiton illustration style",
}
LICENCIAS_OK = {"creativeml-openrail-m", "openrail", "openrail++", "openrail-m", "mit", "apache-2.0",
                "cc-by-4.0", "cc-by-sa-4.0", "cc-by-nc-4.0", "cc-by-nc-sa-4.0", "cc0-1.0"}
ESCALAS_LORA = [0.0, 0.6, 1.0]   # 0.0 = modelo base


def revisar_ficha(repo: str, ficha: Dict, texto_ficha: str = "") -> Dict:
    """Decide si un LoRA se puede usar. `ficha` es la respuesta de /api/models/{repo}."""
    from portadas.guardrails.texto import NOMBRES_PROTEGIDOS, PATRONES_ESTILO, normalizar

    datos = ficha.get("cardData") or {}
    licencia = str(datos.get("license") or "").lower()
    base = datos.get("base_model") or ""
    base = " ".join(base) if isinstance(base, list) else str(base)
    motivos = []
    if licencia not in LICENCIAS_OK:
        motivos.append(f"licencia no permitida o ausente: {licencia or 'sin licencia'}")
    if not any(x in base.lower() for x in ("stable-diffusion-v1-5", "stable-diffusion-v1-4", "sd15", "sd-1-5")):
        motivos.append(f"modelo base no es SD 1.5: {base or 'no indicado'}")
    # Los nombres de repo usan guiones ("quentin-blake-style"): se pasan a espacios.
    t = normalizar(re.sub(r"[-_/]+", " ", f"{repo} {texto_ficha}"))
    nombres = [n for n in NOMBRES_PROTEGIDOS if n in t]
    patrones = [p for p in PATRONES_ESTILO if re.search(p, t)]
    if nombres or patrones:
        motivos.append(f"imita a un artista o marca: {nombres + patrones}")
    return {
        "repo": repo, "ok": not motivos, "motivos": motivos, "licencia": licencia, "base": base,
        "datos_entrenamiento_documentados": bool(datos.get("datasets")),
        "aviso": None if datos.get("datasets") else
        "La ficha no documenta los datos de entrenamiento: reportarlo como limitación.",
    }


def revisar_lora(repo: str) -> Dict:
    import requests

    r = requests.get(f"https://huggingface.co/api/models/{repo}", timeout=30)
    r.raise_for_status()
    leeme = requests.get(f"https://huggingface.co/{repo}/raw/main/README.md", timeout=30)
    return revisar_ficha(repo, r.json(), leeme.text if leeme.ok else "")


def resumir(filas: List[Dict]) -> Dict[str, Dict[str, float]]:
    salida = {}
    for e in sorted({f["escala_lora"] for f in filas}):
        sel = [f for f in filas if f["escala_lora"] == e]
        salida[str(e)] = {k: float(np.mean([f[k] for f in sel if f[k] is not None]))
                          for k in ("acierto_estilo", "clipscore", "f1_bordes", "lpips_vs_base", "latencia_s")
                          if any(f[k] is not None for f in sel)}
        salida[str(e)]["n"] = len(sel)
        salida[str(e)]["nsfw"] = int(sum(bool(f["nsfw_sd"]) for f in sel))
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lora", default=LORA_POR_DEFECTO["repo"])
    ap.add_argument("--peso", default=None, help="nombre del archivo .safetensors dentro del repo")
    ap.add_argument("--disparador", default=None, help="palabra clave del LoRA, se agrega al prompt")
    ap.add_argument("--n", type=int, default=20, help="bocetos de D2 (2 por categoría)")
    ap.add_argument("--d2", default=str(config.DATOS / "d2_quickdraw"))
    ap.add_argument("--salida", default=str(config.SALIDAS / "lora"))
    ap.add_argument("--revisar", action="store_true", help="solo revisar la ficha del LoRA")
    ap.add_argument("--forzar", action="store_true", help="usar aunque la revisión falle (no recomendado)")
    args = ap.parse_args()
    if args.lora == LORA_POR_DEFECTO["repo"]:
        args.peso = args.peso or LORA_POR_DEFECTO["peso"]
        args.disparador = args.disparador or LORA_POR_DEFECTO["disparador"]

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    revision = revisar_lora(args.lora)
    (salida / "revision_lora.json").write_text(json.dumps(revision, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(revision, indent=2, ensure_ascii=False))
    if args.revisar:
        return
    if not revision["ok"] and not args.forzar:
        raise SystemExit("El LoRA no pasa la revisión; no se usa. Elige otro con --lora.")

    from PIL import Image

    from portadas.metricas.bordes import f1_bordes
    from portadas.metricas.clip_metricas import EvaluadorCLIP
    from portadas.metricas.diversidad import EvaluadorLPIPS
    from portadas.motores.base import Peticion
    from portadas.motores.motor_a import MotorA
    from portadas.motores.prompts import construir_prompt
    from portadas.preprocesamiento import preparar_boceto

    indice = json.loads((Path(args.d2) / "indice.json").read_text())
    por_cat: Dict[str, List[Dict]] = {}
    for b in indice:
        por_cat.setdefault(b["categoria"], []).append(b)
    elegidos = [b for lista in por_cat.values() for b in lista[:max(1, args.n // len(por_cat))]][:args.n]

    motor, clip, lp = MotorA(), EvaluadorCLIP(), EvaluadorLPIPS()
    estilos = list(config.ESTILOS)
    imagenes: Dict[tuple, Image.Image] = {}
    filas: List[Dict] = []
    for escala_lora in ESCALAS_LORA:
        if escala_lora > 0:
            if not motor.lora:
                motor.cargar_lora(args.lora, escala=escala_lora, weight_name=args.peso)
            else:
                motor.pipe.set_adapters(["infantil"], adapter_weights=[escala_lora])
        for i, b in enumerate(elegidos):
            boceto = preparar_boceto(Image.open(Path(args.d2) / b["archivo"]), zona_titulo="superior")
            estilo = estilos[i % len(estilos)]
            cfg = {**config.POR_DEFECTO, "P1": estilo}
            pr = construir_prompt(cfg, escena=f"a {b['categoria']}")
            prompt = pr["prompt"] + (f", {args.disparador}" if escala_lora > 0 and args.disparador else "")
            pet = Peticion(id=f"{i}-{escala_lora}", params=cfg, prompt=prompt, negativo=pr["negativo"],
                           semilla=config.SEMILLA_GLOBAL + i,
                           escala_control=config.FIDELIDAD[cfg["P5"]]["controlnet"], pasos=config.PASOS)
            res = motor.generar(boceto.control, [pet])[0]
            imagenes[(i, escala_lora)] = res.imagen
            base = imagenes.get((i, 0.0))
            filas.append({
                "boceto": b["archivo"], "categoria": b["categoria"], "estilo": estilo,
                "escala_lora": escala_lora,
                "acierto_estilo": float(clip.estilo_predicho(res.imagen) == estilo),
                "clipscore": clip.clipscore(res.imagen, pr["prompt"]),  # mismo texto en ambas condiciones
                "f1_bordes": f1_bordes(boceto.lineas, res.imagen)["f1"],
                "lpips_vs_base": lp.distancia(base, res.imagen) if escala_lora > 0 and base else None,
                "latencia_s": res.latencia_s, "nsfw_sd": res.nsfw_sd,
            })
            res.imagen.save(salida / f"{Path(b['archivo']).stem}_lora{escala_lora}.png")
        print(f"[LoRA] escala {escala_lora}: {len(elegidos)} imágenes")

    with open(salida / "lora.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    resumen = {"lora": args.lora, "revision": revision, "por_escala": resumir(filas)}
    (salida / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumen["por_escala"], indent=2))
    _lamina(imagenes, elegidos[:5], salida / "lamina_lora.png")


def _lamina(imagenes: Dict[tuple, "Image.Image"], bocetos: List[Dict], ruta: Path) -> None:
    """Filas = bocetos; columnas = escala del LoRA (0 = base)."""
    from PIL import Image, ImageDraw

    w, h = config.ANCHO // 3, config.ALTO // 3
    hoja = Image.new("RGB", (len(ESCALAS_LORA) * (w + 10) + 10, len(bocetos) * (h + 10) + 40), "white")
    d = ImageDraw.Draw(hoja)
    for j, e in enumerate(ESCALAS_LORA):
        d.text((10 + j * (w + 10), 12), "base" if e == 0 else f"LoRA {e}", fill="black")
    for i in range(len(bocetos)):
        for j, e in enumerate(ESCALAS_LORA):
            if (i, e) in imagenes:
                hoja.paste(imagenes[(i, e)].resize((w, h)), (10 + j * (w + 10), 40 + i * (h + 10)))
    hoja.save(ruta)


if __name__ == "__main__":
    main()
