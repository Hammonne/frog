"""Etapa 2: descarga D1, D2 y D4, corre el análisis exploratorio y deja todo listo.

Uso:
    python -m scripts.preparar_datos                 # todo (D1 con 2 000 portadas)
    python -m scripts.preparar_datos --solo d2 d4    # solo algunos
    python -m scripts.preparar_datos --solo d4es     # historias en español de Wikisource (CPU, ~10 min)
    python -m scripts.preparar_datos --n-d1 200      # prueba rápida
    python -m scripts.preparar_datos --ocr           # posición del título con EasyOCR (GPU)
    python -m scripts.preparar_datos --solo traducir # opcional: traduce historias (no se usa)
    python -m scripts.preparar_datos --solo eda --ocr  # solo análisis, con datos ya subidos

Si la descarga falla en Colab (Amazon a veces bloquea esas IPs), se descarga en una
computadora personal con `--solo d1 d2 d4`, se sube la carpeta `datos/` a Drive o a un
dataset privado de Kaggle, y en Colab se corre `--solo eda --ocr`.
Las historias (D4) se usan en inglés; la traducción quedó como opción y no es necesaria.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from portadas import config
from portadas.datos import eda, historias, historias_es, portadas, quickdraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", nargs="*", default=["d1", "d2", "d4", "eda"])
    ap.add_argument("--n-d1", type=int, default=2000)
    ap.add_argument("--n-d2", type=int, default=20, help="bocetos por categoría")
    ap.add_argument("--n-d4", type=int, default=20, help="historias por categoría")
    ap.add_argument("--n-d4es", type=int, default=60, help="historias en español a conservar")
    ap.add_argument("--ocr", action="store_true")
    ap.add_argument("--traducir", action="store_true")
    args = ap.parse_args()

    config.DATOS.mkdir(parents=True, exist_ok=True)
    salida_eda = config.SALIDAS / "eda"
    salida_eda.mkdir(parents=True, exist_ok=True)

    if "d1" in args.solo:
        resumen = portadas.preparar_d1(n=args.n_d1)
        (salida_eda / "d1_descarga.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    if "d2" in args.solo:
        quickdraw.preparar_d2(n_por_categoria=args.n_d2)
    if "d4" in args.solo:
        historias.preparar_d4(n_por_categoria=args.n_d4, con_traduccion=args.traducir)
    if "d4es" in args.solo:
        historias_es.preparar_d4_es(n=args.n_d4es)
    if "traducir" in args.solo:
        _traducir_existentes(config.DATOS / "d4_historias")

    if "eda" in args.solo:
        carpeta_d1 = config.DATOS / "d1_portadas" / "img"
        if carpeta_d1.exists():
            lector = eda.LectorTitulo() if args.ocr else None
            filas = eda.analizar_d1(carpeta_d1, salida_eda / "d1_metricas.csv", lector=lector)
            if filas:
                resumen = eda.rangos_referencia(filas)
                eda.guardar_resumen(resumen, salida_eda / "resumen_d1.json")
                print(f"[EDA] D1: {resumen['n']} portadas; umbral densidad zona título = "
                      f"{resumen['umbral_densidad_titulo']:.4f}")
        bocetos = sorted((config.DATOS / "d2_quickdraw" / "png").glob("*.png"))
        bocetos += sorted((config.DATOS / "d3_bocetos").glob("*.*"))  # bocetos propios, si ya están
        if bocetos:
            filas = eda.analizar_bocetos(bocetos, salida_eda / "bocetos_metricas.csv")
            print(f"[EDA] {len(filas)} bocetos analizados")
        _graficos(salida_eda)


def _traducir_existentes(carpeta: Path) -> None:
    ruta = carpeta / "historias.jsonl"
    hs = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l]
    pendientes = [h for h in hs if not h.get("texto_es")]
    if pendientes:
        historias.traducir(pendientes)
    with open(ruta, "w", encoding="utf-8") as fh:
        for h in hs:
            fh.write(json.dumps(h, ensure_ascii=False) + "\n")
    plantilla = carpeta / "anotacion_30.csv"
    if _sin_anotar(plantilla):
        historias.plantilla_anotacion(hs, plantilla)  # ahora con el texto en español
    else:
        print(f"[D4] {plantilla.name} ya tiene anotaciones: no se sobrescribe")
    print(f"[D4] traducidas {len(pendientes)} historias")


def _sin_anotar(ruta: Path) -> bool:
    import csv

    if not ruta.exists():
        return True
    with open(ruta, encoding="utf-8") as fh:
        return not any((f.get("personajes") or "").strip() for f in csv.DictReader(fh))


def _graficos(carpeta: Path) -> None:
    """Figuras para el informe (sección 6)."""
    import csv

    import matplotlib.pyplot as plt

    ruta = carpeta / "d1_metricas.csv"
    if not ruta.exists():
        return
    with open(ruta, encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    fig, ax = plt.subplots(1, 3, figsize=(10, 2.8))
    for a, clave, titulo in zip(ax, ["colorido", "brillo", "saturacion"],
                                ["Colorido (Hasler y Süsstrunk)", "Brillo medio", "Saturación media"]):
        a.hist([float(f[clave]) for f in filas], bins=30, color="#4C78A8")
        a.set_title(titulo, fontsize=9)
        a.grid(alpha=0.3)
    fig.suptitle(f"Portadas infantiles de D1 (n = {len(filas)})", fontsize=10)
    fig.tight_layout()
    fig.savefig(carpeta / "d1_distribuciones.png", dpi=200)

    fig, a = plt.subplots(figsize=(4, 2.8))
    medias = [sum(float(f[k]) for f in filas) / len(filas) for k in ("dens_sup", "dens_med", "dens_inf")]
    a.bar(["superior", "medio", "inferior"], medias, color="#4C78A8")
    a.set_ylabel("densidad de bordes")
    a.set_title("Densidad visual por tercio vertical", fontsize=9)
    fig.tight_layout()
    fig.savefig(carpeta / "d1_densidad_tercios.png", dpi=200)


if __name__ == "__main__":
    main()
