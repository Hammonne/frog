"""Tabla de resultados de E1 para el informe (sección 7).

Lee `salidas/e1/e1_resumen.json` (lo escribe `experimentos.e1_automatica`) y escribe
`salidas/e1/tabla_e1.tex`: una tabla LaTeX que compara el motor A con el motor B.

Uso:
    python -m experimentos.tabla_resultados
    python -m experimentos.tabla_resultados --resumen salidas/e1_prueba/e1_resumen.json
    # motores evaluados en corridas distintas: los resúmenes se unen (el último manda)
    python -m experimentos.tabla_resultados --resumen salidas/e1/e1_resumen.json salidas/e1_b/e1_resumen.json

Formato de `e1_resumen.json` (un diccionario por motor):
    {"A": {"n_imagenes": 2000, "clipscore_medio": 31.2, "acierto_estilo_eje_estilo": 0.74,
           "acierto_paleta_eje_paleta": 0.81, "recall_boceto_medio": 0.42,
           "elemento_principal_detectado": 0.85, "lpips_medio": 0.61,
           "latencia_ronda_media_s": 38.5, "bloqueadas": 3, ...},
     "B": {...}}
Algunos valores pueden venir como null (None) si esa métrica no se pudo calcular.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

from portadas import config

# (clave en e1_resumen.json, nombre en la tabla, tipo de formato)
# tipo "pct" = porcentaje sin decimales (0.74 -> "74 %"); "num" = un decimal; "int" = entero.
FILAS = [
    ("clipscore_medio", "CLIPScore", "num"),
    ("acierto_estilo_eje_estilo", "Acierto de estilo", "pct"),
    ("acierto_paleta_eje_paleta", "Paleta dentro del rango", "pct"),
    ("recall_boceto_medio", "Fidelidad al boceto (recall)", "pct"),
    ("elemento_principal_detectado", "Elemento principal detectado", "pct"),
    ("lpips_medio", "Diversidad (LPIPS)", "num"),
    ("latencia_ronda_media_s", "Latencia por ronda (s)", "num"),
    ("bloqueadas", "Portadas bloqueadas", "int"),
    ("kid", "KID", "num"),
    ("fid", "FID", "num"),
]


def formatear(valor: Optional[float], tipo: str) -> str:
    """Convierte un valor en texto para LaTeX.

    - None -> "--"
    - tipo "pct": 0.743 -> "74\\,\\%"
    - tipo "num": 38.46 -> "38.5" (un decimal; dos si el valor es menor que 10, para no
      perder información en métricas entre 0 y 1: 0.763 -> "0.76")
    - tipo "int": 3 -> "3"
    """
    if valor is None:
        return "--"
    if tipo == "pct":
        return f"{round(valor * 100):d}" + "\\,\\%"
    if tipo == "int":
        return f"{int(valor)}"
    return f"{valor:.2f}" if abs(valor) < 10 else f"{valor:.1f}"


def fila(nombre: str, valores: List[str]) -> str:
    """Una fila de la tabla: fila("CLIPScore", ["31.2", "29.8"]) -> "CLIPScore & 31.2 & 29.8\\\\"."""
    return " & ".join([nombre, *valores]) + "\\\\"


def tabla_latex(resumen: Dict[str, Dict]) -> str:
    """Arma la tabla completa con una columna por motor, en orden (A, luego B).

    Usar este esqueleto y agregar una línea `fila(...)` por cada elemento de FILAS:
        \\begin{tabular}{@{}lrr@{}}
        \\toprule
        \\textbf{Métrica} & \\textbf{Motor A} & \\textbf{Motor B}\\\\
        \\midrule
        ... filas ...
        \\bottomrule
        \\end{tabular}
    Si solo hay un motor en el resumen, la tabla tiene una sola columna de valores.
    """
    motores = sorted(resumen)
    cabecera = " & ".join(["\\textbf{Métrica}"] + [f"\\textbf{{Motor {m}}}" for m in motores]) + "\\\\"
    cuerpo = [fila(nombre, [formatear(resumen[m].get(clave), tipo) for m in motores])
              for clave, nombre, tipo in FILAS]
    return "\n".join([
        "\\begin{tabular}{@{}l" + "r" * len(motores) + "@{}}",
        "\\toprule",
        cabecera,
        "\\midrule",
        *cuerpo,
        "\\bottomrule",
        "\\end{tabular}",
    ]) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resumen", nargs="+", default=[str(config.SALIDAS / "e1" / "e1_resumen.json")])
    args = ap.parse_args()
    resumen: Dict[str, Dict] = {}
    for r in args.resumen:
        ruta = Path(r)
        if not ruta.exists():
            raise SystemExit(f"No existe {ruta}: primero corre la evaluación E1.")
        resumen.update(json.loads(ruta.read_text(encoding="utf-8")))
    tabla = tabla_latex(resumen)
    salida = Path(args.resumen[0]).with_name("tabla_e1.tex")
    salida.write_text(tabla, encoding="utf-8")
    print(tabla)
    print(f"\nGuardada en {salida}: copiarla en la sección 7 de informe/main.tex.")


if __name__ == "__main__":
    main()
