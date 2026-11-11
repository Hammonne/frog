"""Pruebas de la tabla de resultados de E1 (tarea de la etapa 3).

Cuando `experimentos/tabla_resultados.py` esté completo, borrar la línea `pytestmark` de abajo.
"""
import pytest

from experimentos.tabla_resultados import fila, formatear, tabla_latex

pytestmark = pytest.mark.skip(reason="pendiente: completar experimentos/tabla_resultados.py")


def test_formatear():
    assert formatear(None, "pct") == "--"
    assert formatear(0.743, "pct") == "74\\,\\%"
    assert formatear(38.46, "num") == "38.5"
    assert formatear(3, "int") == "3"


def test_fila():
    assert fila("CLIPScore", ["31.2", "29.8"]) == "CLIPScore & 31.2 & 29.8\\\\"


def test_tabla_latex():
    resumen = {
        "B": {"clipscore_medio": 29.84, "acierto_estilo_eje_estilo": 0.6, "bloqueadas": 1},
        "A": {"clipscore_medio": 31.21, "acierto_estilo_eje_estilo": 0.74, "bloqueadas": 3},
    }
    t = tabla_latex(resumen)
    assert t.startswith("\\begin{tabular}") and t.rstrip().endswith("\\end{tabular}")
    assert "Motor A" in t and "Motor B" in t
    assert "CLIPScore & 31.2 & 29.8\\\\" in t          # A antes que B
    assert "Acierto de estilo & 74\\,\\% & 60\\,\\%\\\\" in t
    assert "Diversidad (LPIPS) & -- & --\\\\" in t     # falta en el resumen
