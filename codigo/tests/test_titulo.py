"""Pruebas del renderizador del título (sin GPU)."""
import numpy as np
import pytest
from PIL import Image

from portadas import config
from portadas.titulo import CONTRASTE_MIN, contraste, render_titulo


def lienzo(color):
    return Image.new("RGB", (config.ANCHO, config.ALTO), color)


def test_contraste_wcag_conocido():
    assert contraste((0, 0, 0), (255, 255, 255)) == pytest.approx(21.0, rel=1e-3)
    assert contraste((255, 255, 255), (255, 255, 255)) == pytest.approx(1.0)


@pytest.mark.parametrize("fondo", [(250, 250, 250), (20, 20, 40), (200, 120, 40), (128, 128, 128)])
def test_el_contraste_final_cumple_wcag_sobre_cualquier_fondo(fondo):
    _, info = render_titulo(lienzo(fondo), "El conejo y las flores", "superior", "4-6")
    assert info["contraste"] >= CONTRASTE_MIN


def test_dibuja_solo_dentro_de_la_zona():
    img = lienzo((240, 240, 240))
    out, info = render_titulo(img, "Mi cuento", "superior", "4-6")
    diff = np.abs(np.asarray(out, dtype=int) - np.asarray(img, dtype=int)).sum(axis=2)
    filas = np.where(diff.sum(axis=1) > 0)[0]
    assert len(filas) and filas.max() < config.ALTO * 0.40     # nada en la mitad inferior
    assert out.size == img.size and info["fuente"]


def test_sin_titulo_o_zona_sin_no_cambia_la_imagen():
    img = lienzo((10, 200, 10))
    for titulo, zona in [("", "superior"), ("Hola", "sin")]:
        out, info = render_titulo(img, titulo, zona)
        assert np.array_equal(np.asarray(out), np.asarray(img)) and info["contraste"] is None


def test_zona_centrada_siempre_lleva_banda():
    _, info = render_titulo(lienzo((250, 250, 250)), "Titulo", "centrada")
    assert info["banda"] is True


def test_titulo_largo_se_ajusta_y_se_recorta():
    largo = "palabra " * 40
    out, info = render_titulo(lienzo((255, 255, 255)), largo, "superior", "4-6")
    assert out.size == (config.ANCHO, config.ALTO) and info["tamano_px"] >= 14


def test_es_determinista():
    a, _ = render_titulo(lienzo((200, 100, 50)), "Hola mundo", "inferior", "7-9")
    b, _ = render_titulo(lienzo((200, 100, 50)), "Hola mundo", "inferior", "7-9")
    assert np.array_equal(np.asarray(a), np.asarray(b))
