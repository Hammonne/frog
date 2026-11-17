"""Legibilidad del título: tasa de error por carácter (CER) al leerlo con OCR.

Métrica de la Tabla 4 del informe ("legibilidad del título"): el título renderizado debe poder leerse
con Tesseract con un CER de 5 % o menos. Se toman portadas ya generadas en E1 (salidas/e1/img/), se
les pone un título de prueba de distinta longitud de tres maneras y se lee la zona del título:

  defecto : disposición por defecto según la edad (sin agente)
  agente  : estilo propuesto por el agente tipográfico (necesita el LLM, GPU)
  extremo : los límites máximos de curva, onda, inclinación y contorno (peor caso permitido)

Deja salidas/legibilidad/legibilidad.csv (una fila por portada y modo), resumen.json y muestras.png.

Antes, en Colab:
    !apt-get -qq install tesseract-ocr tesseract-ocr-spa
    !pip install -q pytesseract
Uso:
    python -m experimentos.legibilidad_titulo --n 100
    python -m experimentos.legibilidad_titulo --n 100 --sin-agente      # sin GPU: solo defecto y extremo
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from pathlib import Path
from typing import Callable, Dict, List, Optional

from PIL import Image

from portadas import config
from portadas.agentes.tipografia import titular_basico, titular_con_agente
from portadas.guardrails.texto import normalizar
from portadas.titulo import CATALOGO, caja_titulo, render_titulo

CER_MAX = 0.05                       # criterio del informe
TITULOS = [
    "El conejo", "Luna y el bosque", "Tomás y las galletas", "La tortuga que quería volar",
    "El dragón que tenía miedo del fuego", "Pablo y la estrella del mar", "Un día en el jardín",
    "Los tres amigos del río", "Mía y el barco de papel", "La noche en que el oso no pudo dormir",
    "Dino", "El gato que aprendió a nadar en la laguna",
]


# ----------------------------------------------------------------------------- métrica
def distancia(a: str, b: str) -> int:
    """Distancia de Levenshtein (inserciones, borrados y sustituciones)."""
    previa = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        actual = [i]
        for j, cb in enumerate(b, start=1):
            actual.append(min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + (ca != cb)))
        previa = actual
    return previa[-1]


def limpiar(texto: str) -> str:
    """Minúsculas, sin tildes y con los espacios normalizados: se compara el contenido, no el formato."""
    return " ".join(normalizar(texto or "").split())


def cer(real: str, leido: str) -> float:
    real, leido = limpiar(real), limpiar(leido)
    return distancia(real, leido) / max(len(real), 1)


# ----------------------------------------------------------------------------- OCR
def crear_ocr() -> Callable[[Image.Image, str], str]:
    """Lector de la zona del título con Tesseract (español si está instalado)."""
    import pytesseract
    idiomas = pytesseract.get_languages()
    lang = "spa" if "spa" in idiomas else "eng"

    def leer(img: Image.Image, zona: str) -> str:
        x0, y0, x1, y1 = caja_titulo(zona, *img.size)
        margen = 12
        area = img.convert("L").crop((max(0, x0 - margen), max(0, y0 - margen),
                                      min(img.width, x1 + margen), min(img.height, y1 + margen)))
        area = area.resize((area.width * 2, area.height * 2), Image.LANCZOS)
        return pytesseract.image_to_string(area, lang=lang, config="--psm 6")
    leer.idioma = lang
    return leer


def comprobar_ocr(ocr) -> None:
    """Un título grande, negro sobre blanco, debe leerse casi perfecto; si no, Tesseract no está bien."""
    lienzo = Image.new("RGB", (config.ANCHO, config.ALTO), (255, 255, 255))
    img, _ = render_titulo(lienzo, "Luna y el dragon", "superior", "7-9", fuente="Andika", color=(0, 0, 0))
    error = cer("Luna y el dragon", ocr(img, "superior"))
    if error > 0.2:
        raise RuntimeError(f"Tesseract no lee ni un título simple (CER {error:.2f}). Revisa la instalación: "
                           "apt-get install tesseract-ocr tesseract-ocr-spa y pip install pytesseract.")


# ----------------------------------------------------------------------------- muestra de portadas
def muestrear(ruta_csv: Path, n: int, semilla: int = config.SEMILLA_GLOBAL) -> List[Dict]:
    """n portadas del motor A de E1 con su imagen presente (misma muestra en cada corrida)."""
    with open(ruta_csv, encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    candidatas = []
    for f in filas:
        if f.get("motor") != "A" or not f.get("imagen") or f.get("param_P6") == "sin":
            continue
        ruta = config.RAIZ / f["imagen"]
        if ruta.exists():
            candidatas.append({"par": f["par"], "id": f["id"], "ruta": ruta,
                               "params": {k.replace("param_", ""): v for k, v in f.items() if k.startswith("param_")}})
    random.Random(semilla).shuffle(candidatas)
    return candidatas[:n]


# ----------------------------------------------------------------------------- medición
def _extremo(i: int):
    fuente = list(CATALOGO)[i % len(CATALOGO)]
    return dict(fuente=fuente, curva=0.4 if i % 2 == 0 else -0.4, onda=0.15, inclinacion=8, contorno=0.10,
                restringir_edad=False)


def ejecutar(filas: List[Dict], titulos: List[str], llm, ocr, modos=("defecto", "agente", "extremo")) -> List[Dict]:
    """Pone un título a cada portada con cada modo, lo lee y calcula el CER."""
    resultados = []
    for i, f in enumerate(filas):
        titulo = titulos[i % len(titulos)]
        img = Image.open(f["ruta"]).convert("RGB")
        zona, edad = f["params"]["P6"], f["params"]["P3"]
        for modo in modos:
            if modo == "defecto":
                titulada, info = titular_basico(img, titulo, zona, edad)
            elif modo == "agente":
                titulada, info = titular_con_agente(img, titulo, zona, edad, f["params"], llm)
            else:
                titulada, info = render_titulo(img, titulo, zona, edad, **_extremo(i))
            leido = ocr(titulada, zona)
            resultados.append({
                "modo": modo, "par": f["par"], "id": f["id"], "edad": edad, "titulo": titulo,
                "n_letras": len(titulo.replace(" ", "")), "fuente": info["estilo"]["fuente"],
                "contraste": info["contraste"], "banda": info["banda"],
                "origen_agente": (info.get("agente") or {}).get("origen", ""),
                "leido": " ".join(leido.split()), "cer": round(cer(titulo, leido), 4)})
    return resultados


def resumir(resultados: List[Dict]) -> Dict:
    resumen = {}
    for modo in dict.fromkeys(r["modo"] for r in resultados):
        rs = [r for r in resultados if r["modo"] == modo]
        errores = [r["cer"] for r in rs]
        resumen[modo] = {
            "n": len(rs), "cer_medio": round(statistics.mean(errores), 4),
            "cer_mediana": round(statistics.median(errores), 4),
            "pct_cer_hasta_5": round(sum(e <= CER_MAX for e in errores) / len(errores), 4),
            "pct_exactos": round(sum(e == 0 for e in errores) / len(errores), 4),
            "contraste_minimo": min(r["contraste"] for r in rs),
            "pct_con_banda": round(sum(r["banda"] for r in rs) / len(rs), 4),
            "cumple_cer_medio": statistics.mean(errores) <= CER_MAX,
            "cer_por_fuente": {fu: round(statistics.mean(r["cer"] for r in rs if r["fuente"] == fu), 4)
                               for fu in sorted({r["fuente"] for r in rs})},
        }
        if modo == "agente":
            resumen[modo]["pct_respaldo"] = round(sum(r["origen_agente"] == "respaldo" for r in rs) / len(rs), 4)
    return resumen


def hoja_de_muestras(filas: List[Dict], titulos: List[str], llm, ruta: Path, cuantas: int = 4) -> None:
    """Imagen con la zona del título de unas pocas portadas en cada modo (para el informe)."""
    columnas = ("defecto", "agente", "extremo")
    recortes = []
    for i, f in enumerate(filas[:cuantas]):
        img = Image.open(f["ruta"]).convert("RGB")
        zona, edad = f["params"]["P6"], f["params"]["P3"]
        fila = []
        for modo in columnas:
            if modo == "defecto":
                t, _ = titular_basico(img, titulos[i % len(titulos)], zona, edad)
            elif modo == "agente":
                t, _ = titular_con_agente(img, titulos[i % len(titulos)], zona, edad, f["params"], llm)
            else:
                t, _ = render_titulo(img, titulos[i % len(titulos)], zona, edad, **_extremo(i))
            x0, y0, x1, y1 = caja_titulo(zona, *t.size)
            fila.append(t.crop((x0 - 12, max(0, y0 - 12), x1 + 12, y1 + 12)))
        recortes.append(fila)
    ancho, alto = recortes[0][0].size
    hoja = Image.new("RGB", (ancho * len(columnas), alto * len(recortes)), "white")
    for r, fila in enumerate(recortes):
        for c, im in enumerate(fila):
            hoja.paste(im.resize((ancho, alto)), (c * ancho, r * alto))
    hoja.save(ruta)


# ----------------------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="portadas de E1 a usar")
    ap.add_argument("--e1", default=str(config.SALIDAS / "e1" / "e1_imagenes.csv"))
    ap.add_argument("--llm", default="qwen2.5-7b")
    ap.add_argument("--sin-agente", action="store_true", help="no carga el LLM: solo defecto y extremo")
    ap.add_argument("--salida", default=str(config.SALIDAS / "legibilidad"))
    args = ap.parse_args()

    ocr = crear_ocr()
    comprobar_ocr(ocr)
    filas = muestrear(Path(args.e1), args.n)
    if not filas:
        raise SystemExit(f"No hay portadas del motor A con imagen en {args.e1}: ¿está salidas/e1/img/ en Drive?")
    llm, modos = None, ("defecto", "extremo")
    if not args.sin_agente:
        from portadas.agentes.llm import LLMLocal
        llm, modos = LLMLocal(args.llm), ("defecto", "agente", "extremo")
    print(f"[legibilidad] {len(filas)} portadas, modos {modos}, OCR en '{ocr.idioma}'")

    resultados = ejecutar(filas, TITULOS, llm, ocr, modos)
    resumen = resumir(resultados)
    resumen["criterio"] = f"CER <= {CER_MAX:.0%} (media por modo)"
    resumen["ocr"] = {"idioma": ocr.idioma, "portadas": len(filas), "titulos_distintos": len(TITULOS)}
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    with open(salida / "legibilidad.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(resultados[0]))
        w.writeheader()
        w.writerows(resultados)
    (salida / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    hoja_de_muestras(filas, TITULOS, llm, salida / "muestras.png")
    if llm is not None:
        llm.liberar()
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
