"""Copia a `portadas/config.py` los valores que propone la calibración (tarea de Maria).

Lee `salidas/calibracion/resumen.json` (lo escribe `experimentos.calibracion`) y reemplaza
la escala de ControlNet de cada nivel de FIDELIDAD y el número de PASOS. Los valores de
SD-Turbo (`turbo`) no se tocan. Guarda una copia `config.py.antes_calibracion`.

Uso:
    python -m experimentos.aplicar_calibracion            # muestra los cambios y los aplica
    python -m experimentos.aplicar_calibracion --probar   # solo muestra los cambios
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from portadas import config

RUTA_CONFIG = Path(__file__).resolve().parents[1] / "portadas" / "config.py"


def aplicar(texto: str, propuesta: dict) -> str:
    """Devuelve el texto de config.py con los valores de la propuesta."""
    for nivel, escala in propuesta["fidelidad"].items():
        patron = rf'("{re.escape(nivel)}":\s*\{{"controlnet":\s*)[0-9.]+'
        texto, n = re.subn(patron, rf"\g<1>{float(escala):.2f}", texto)
        if n != 1:
            raise ValueError(f"No se encontró el nivel {nivel!r} en FIDELIDAD")
    texto, n = re.subn(r"^PASOS = \d+", f"PASOS = {int(propuesta['pasos'])}", texto, flags=re.M)
    if n != 1:
        raise ValueError("No se encontró la línea 'PASOS = ...'")
    return texto


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resumen", default=str(config.SALIDAS / "calibracion" / "resumen.json"))
    ap.add_argument("--probar", action="store_true", help="solo mostrar, sin escribir")
    args = ap.parse_args()

    ruta = Path(args.resumen)
    if not ruta.exists():
        raise SystemExit(f"No existe {ruta}: primero corre `python -m experimentos.calibracion`.")
    propuesta = json.loads(ruta.read_text(encoding="utf-8"))["propuesta"]

    print("Nivel        antes  ->  después (escala de ControlNet)")
    for nivel, escala in propuesta["fidelidad"].items():
        print(f"{nivel:<12} {config.FIDELIDAD[nivel]['controlnet']:>5}  ->  {float(escala):.2f}")
    print(f"PASOS        {config.PASOS:>5}  ->  {propuesta['pasos']}")
    escalas = [float(e) for e in propuesta["fidelidad"].values()]
    if escalas != sorted(escalas):
        print("Aviso: las escalas no crecen de 'muy_baja' a 'muy_alta'; revisar antes de aplicar.")
    if args.probar:
        return

    texto = RUTA_CONFIG.read_text(encoding="utf-8")
    shutil.copy(RUTA_CONFIG, RUTA_CONFIG.with_name("config.py.antes_calibracion"))
    RUTA_CONFIG.write_text(aplicar(texto, propuesta), encoding="utf-8")
    print(f"Listo: {RUTA_CONFIG} actualizado. Ahora corre las pruebas: python -m pytest -q tests")


if __name__ == "__main__":
    main()
