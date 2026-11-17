"""Pruebas de los recursos gráficos: archivos, limpieza del recorte y uso en la interfaz."""
import re
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app import estilo as E
from app import recursos as R
from scripts.recortar_recursos import ALFA_MIN, RECURSOS, recortar

APP = Path(__file__).resolve().parents[1] / "app"
OPACOS = {"textura_papel"}                  # rectángulo con fondo propio: no tiene transparencia


def archivos():
    return {p.stem: p for c in R.CATEGORIAS for p in (APP / "assets" / c).glob("*.png")}


def test_estan_los_29_recursos_en_su_categoria():
    for categoria, recursos in RECURSOS.items():
        for nombre in recursos:
            assert (APP / "assets" / categoria / f"{nombre}.png").exists(), f"falta {categoria}/{nombre}.png"
    assert len(archivos()) == sum(len(r) for r in RECURSOS.values()) == 29


def test_los_nombres_son_unicos_entre_categorias():
    nombres = [n for r in RECURSOS.values() for n in r]
    assert len(nombres) == len(set(nombres))                # recursos.ruta() busca solo por nombre


@pytest.mark.parametrize("nombre", sorted(archivos()))
def test_cada_recorte_esta_limpio(nombre):
    a = np.asarray(Image.open(archivos()[nombre]).convert("RGBA"))
    alfa = a[..., 3]
    if nombre in OPACOS:
        assert alfa.min() >= ALFA_MIN
        return
    assert alfa.min() == 0, "debe tener fondo transparente"
    assert not ((alfa > 0) & (alfa < ALFA_MIN)).any(), "quedó ruido casi transparente (halos de color)"
    assert (a[alfa == 0][:, :3] == 0).all(), "color oculto bajo lo transparente"
    esquinas = [alfa[0, 0], alfa[0, -1], alfa[-1, 0], alfa[-1, -1]]
    assert max(esquinas) == 0, "el recorte debe quedar ajustado al contenido, con margen transparente"


def test_el_peso_de_los_recursos_es_razonable():
    assert max(p.stat().st_size for p in archivos().values()) < 250_000
    assert sum(p.stat().st_size for p in archivos().values()) < 2_000_000


def test_el_recorte_descarta_ruido_y_motas_pero_conserva_piezas_sueltas():
    hoja = np.zeros((120, 240, 4), np.uint8)
    hoja[20:60, 30:90] = (40, 160, 60, 255)                  # el recurso
    hoja[30:56, 100:106] = (250, 200, 0, 255)                # una pieza suelta legítima (un rayo del sol)
    hoja[100:103, 30:33] = (0, 0, 0, 255)                    # una mota diminuta
    hoja[0:120, 200:240, 3] = 20                             # ruido de alfa bajo
    hoja[0:120, 200:240, :3] = (255, 255, 0)
    im = recortar(hoja, (0, 0, 240, 120))
    a = np.asarray(im)
    assert im.size == (82, 46)                               # del recurso (30..90) al rayo (..106), con margen
    assert not ((a[..., 3] > 0) & (a[..., 3] < ALFA_MIN)).any()
    assert (a[..., 3] > 0).sum() == 60 * 40 + 6 * 26         # solo el recurso y el rayo


def test_todos_los_recursos_que_usa_el_codigo_existen():
    usados = set()
    for fuente in ("estilo.py", "interfaz.py"):
        usados |= set(re.findall(r'"((?:frog|ico|deco|escena|fondo|textura)_\w+)"', (APP / fuente).read_text(encoding="utf-8")))
    usados -= {"frog_componentes", "escena_img"}             # nombres internos de la interfaz, no recursos
    assert usados, "no se encontró ningún recurso en el código"
    faltan = [n for n in usados if R.ruta(n) is None]
    assert not faltan, f"el código usa recursos que no existen: {faltan}"


def test_cada_momento_del_dia_tiene_su_escena():
    assert all(R.ruta(n) for n in E.ESCENA_DE.values()) and R.ruta("escena_bosque")


def test_las_imagenes_se_incrustan_y_son_decorativas_por_defecto():
    h = R.img("ico_brillo", alto=22)
    assert h.startswith("<img") and "data:image/" in h and 'aria-hidden="true"' in h
    assert 'alt="Ranita"' in R.img("frog_hero", alt="Ranita")
    assert R.img("no_existe") == ""


def test_cada_pantalla_usa_su_ranita():
    assert R.uri("frog_hero") in E.inicio_imagen() and "f-estallido" in E.inicio_imagen()
    assert R.uri("frog_generando") in E.carga("t", "d")
    assert R.uri("frog_analiza") in E.carga("t", "d", mascota="frog_analiza")
    assert R.uri("frog_resumen") in E.imagen("frog_resumen", 200)
    assert "<img" not in E.tarjeta("error", "t", "x") and "<img" not in E.tarjeta("ok", "t", "x")    # sin iconos
    assert R.uri("ico_bloqueo") in E.bloqueada()
    assert R.uri("escena_noche") in E.escena("night") and R.uri("escena_dia") in E.escena("morning")
    assert R.uri("escena_bosque") in E.escena("") and R.uri("escena_bosque") in E.escena("sunset")


def test_el_css_incluye_el_fondo_de_papel_y_la_fuente():
    assert R.uri("textura_papel") in E.CSS and "url(none)" not in E.CSS


def test_sin_recursos_la_interfaz_sigue_funcionando(monkeypatch):
    """Si faltara alguna imagen, los textos y los iconos de respaldo siguen mostrándose."""
    monkeypatch.setattr(R, "uri", lambda nombre: "")
    monkeypatch.setattr(R, "ruta", lambda nombre: None)
    assert "Convierte tu historia" in E.inicio_texto() and "Leyendo" in E.carga("Leyendo", "d")
    assert "Entrada" in E.barra_pasos(1) and "Falta" in E.tarjeta("error", "Falta", "x")
    assert "bloqueada" in E.bloqueada() and E.etiqueta_campo("Estilo") and "Estilo" in E.ficha("Estilo", "", 1)


def test_cada_png_tiene_su_webp_listo_para_incrustar_y_pesa_menos():
    for nombre, png in archivos().items():
        webp = png.with_suffix(".webp")
        assert webp.exists(), f"falta {webp.name}: ejecuta python -m scripts.recortar_recursos"
        assert webp.stat().st_size < png.stat().st_size
        assert Image.open(webp).size == Image.open(png).size
    assert R.uri("frog_hero").startswith("data:image/webp;base64,")


def test_funciona_subiendo_solo_los_webp(tmp_path, monkeypatch):
    """En Colab basta con los .webp: los .png son el entregable editable y no se usan en ejecución."""
    (tmp_path / "iconos").mkdir()
    Image.new("RGBA", (10, 10), (255, 0, 0, 255)).save(tmp_path / "iconos" / "ico_prueba.webp")
    monkeypatch.setattr(R, "ASSETS", tmp_path)
    R.ruta.cache_clear(); R.uri.cache_clear()
    try:
        assert R.ruta("ico_prueba").suffix == ".webp"
        assert R.uri("ico_prueba").startswith("data:image/webp;base64,")
        assert R.img("ico_prueba", alto=20)
    finally:
        monkeypatch.undo(); R.ruta.cache_clear(); R.uri.cache_clear()
