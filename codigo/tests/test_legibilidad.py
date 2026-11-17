"""Pruebas de la medición de legibilidad del título (sin Tesseract ni GPU: OCR y LLM falsos)."""
import csv

import pytest
from PIL import Image

from experimentos import legibilidad_titulo as L
from portadas import config


def test_cer_cuenta_errores_por_caracter_e_ignora_tildes_y_formato():
    assert L.cer("Tomás y las galletas", "tomas  y las\ngalletas") == 0
    assert L.cer("hola", "hela") == pytest.approx(0.25)          # una sustitución en 4 letras
    assert L.cer("hola", "") == 1.0
    assert L.cer("hola", "holaaa") == pytest.approx(0.5)         # dos inserciones
    assert L.distancia("kitten", "sitting") == 3


def filas_falsas(tmp_path, n=3):
    filas = []
    for i in range(n):
        ruta = tmp_path / f"p{i}.png"
        Image.new("RGB", (config.ANCHO, config.ALTO), (200 - 30 * i, 220, 240)).save(ruta)
        filas.append({"par": f"cat_{i:02d}", "id": f"R1-V{i + 1}", "ruta": ruta,
                      "params": {"P1": "acuarela", "P2": "pastel", "P3": "4-6", "P4": "calma", "P5": "media",
                                 "P6": "superior"}})
    return filas


class LLMFalso:
    def __call__(self, sistema, mensaje):
        return '{"fuente": "Fredoka", "curva": 0.2, "color": "#1B3A57"}'


def test_ejecutar_mide_los_tres_modos_y_resume(tmp_path):
    filas = filas_falsas(tmp_path)
    ciego = lambda img, zona: ""                                  # un OCR que no lee nada: CER 1
    r = L.ejecutar(filas, ["Hola"], LLMFalso(), ciego)
    assert len(r) == 9 and {x["modo"] for x in r} == {"defecto", "agente", "extremo"}
    assert all(x["cer"] == 1.0 and x["contraste"] >= 4.5 for x in r)
    assert {x["origen_agente"] for x in r if x["modo"] == "agente"} == {"agente"}
    res = L.resumir(r)
    assert res["agente"]["cer_medio"] == 1.0 and res["agente"]["cumple_cer_medio"] is False
    assert res["defecto"]["n"] == 3 and res["agente"]["pct_respaldo"] == 0.0
    assert set(res["agente"]["cer_por_fuente"]) == {"Fredoka"}


def test_un_ocr_perfecto_cumple_el_criterio(tmp_path):
    perfecto = lambda img, zona: "Hola"
    r = L.ejecutar(filas_falsas(tmp_path, 2), ["Hola"], None, perfecto, modos=("defecto", "extremo"))
    res = L.resumir(r)
    assert all(v["cer_medio"] == 0 and v["cumple_cer_medio"] and v["pct_exactos"] == 1.0 for k, v in res.items())


def test_el_modo_extremo_usa_los_limites_maximos(tmp_path):
    r = L.ejecutar(filas_falsas(tmp_path, 1), ["Hola mundo"], None, lambda i, z: "", modos=("extremo",))
    assert r[0]["contraste"] >= 4.5


def test_muestrear_toma_solo_el_motor_a_con_imagen_y_es_reproducible(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RAIZ", tmp_path)
    (tmp_path / "salidas").mkdir()
    campos = ["par", "motor", "id", "imagen", "param_P1", "param_P3", "param_P6"]
    with open(tmp_path / "e1.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for i in range(6):
            Image.new("RGB", (64, 64)).save(tmp_path / "salidas" / f"{i}.png")
            w.writerow({"par": f"c{i}", "motor": "B" if i == 0 else "A", "id": f"R1-V{i}",
                        "imagen": f"salidas/{i}.png", "param_P1": "acuarela", "param_P3": "4-6",
                        "param_P6": "sin" if i == 1 else "superior"})
        w.writerow({"par": "x", "motor": "A", "id": "R1-V9", "imagen": "salidas/no_existe.png",
                    "param_P1": "acuarela", "param_P3": "4-6", "param_P6": "superior"})
    a = L.muestrear(tmp_path / "e1.csv", 10)
    assert sorted(f["par"] for f in a) == ["c2", "c3", "c4", "c5"]      # sin motor B, sin zona 'sin', sin imagen ausente
    assert [f["par"] for f in a] == [f["par"] for f in L.muestrear(tmp_path / "e1.csv", 10)]
    assert a[0]["params"]["P6"] == "superior"


def test_la_hoja_de_muestras_se_genera(tmp_path):
    L.hoja_de_muestras(filas_falsas(tmp_path, 2), ["Hola", "Luna"], LLMFalso(), tmp_path / "m.png", cuantas=2)
    assert Image.open(tmp_path / "m.png").width > 0
