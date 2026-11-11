"""Pruebas que corren en CPU sin modelos (python -m pytest -q)."""
from __future__ import annotations

import json

import numpy as np
import pytest
from PIL import Image, ImageDraw

from portadas import config
from portadas.datos import historias, quickdraw
from portadas.datos.eda import metricas_portada, rangos_referencia
from portadas.datos.portadas import leer_listado, muestrear_infantiles
from portadas.guardrails.salida import RevisorSalida
from portadas.guardrails.texto import filtrar_texto, mensaje_usuario
from portadas.metricas.bordes import f1_bordes, densidad_bordes
from portadas.metricas.color import adherencia_paleta, colorido, estadisticas_hsv
from portadas.motores.base import MotorNoDisponible, Resultado
from portadas.motores.generar import generar_ronda, guardar_imagenes, peticiones_ronda
from portadas.motores.prompts import (configuraciones_por_eje, construir_prompt,
                                      escena_desde_elementos)
from portadas.preprocesamiento import BocetoInvalido, preparar_boceto, region_libre


def dibujo_conejo(tam=(600, 600), fondo=255, trazo=0) -> Image.Image:
    img = Image.new("L", tam, fondo)
    d = ImageDraw.Draw(img)
    d.ellipse((200, 260, 400, 460), outline=trazo, width=6)   # cuerpo
    d.ellipse((240, 120, 290, 270), outline=trazo, width=6)   # oreja
    d.ellipse((310, 120, 360, 270), outline=trazo, width=6)   # oreja
    d.line((100, 500, 500, 500), fill=trazo, width=6)          # suelo
    return img


# ------------------------------------------------------------ preprocesamiento
def test_boceto_valido_respeta_zona_titulo():
    b = preparar_boceto(dibujo_conejo(), zona_titulo="superior")
    assert b.lineas.size == (config.ANCHO, config.ALTO)
    assert b.tipo == "boceto"
    tinta = np.asarray(b.lineas) < 128
    y0 = region_libre("superior")[1]
    assert tinta[:y0].sum() == 0, "el dibujo invade la zona del título"
    assert tinta.sum() > 0
    control = np.asarray(b.control.convert("L"))
    assert control.max() == 255 and control[tinta].min() == 255  # blanco sobre negro


def test_boceto_inferior_deja_libre_abajo():
    b = preparar_boceto(dibujo_conejo(), zona_titulo="inferior")
    tinta = np.asarray(b.lineas) < 128
    y1 = region_libre("inferior")[3]
    assert tinta[y1:].sum() == 0


def test_boceto_vacio_y_saturado():
    with pytest.raises(BocetoInvalido):
        preparar_boceto(Image.new("L", (400, 400), 255))
    lleno = Image.new("L", (400, 400), 255)
    ImageDraw.Draw(lleno).rectangle((20, 20, 380, 380), fill=0)
    with pytest.raises(BocetoInvalido):
        preparar_boceto(lleno)


def test_quita_exif_y_acepta_rgba():
    img = dibujo_conejo().convert("RGBA")
    b = preparar_boceto(img)
    assert not b.lineas.info


# --------------------------------------------------------------------- prompts
def test_prompt_contiene_parametros_y_escena():
    cfg = dict(config.POR_DEFECTO)
    escena = escena_desde_elementos({"personajes": ["rabbit"], "objetos": ["flowers"], "lugar": "garden"})
    assert escena == "a rabbit with flowers in a garden"
    pr = construir_prompt(cfg, escena=escena)
    assert pr["prompt"].startswith(config.ESTILOS["acuarela"])
    assert "a rabbit with flowers" in pr["prompt"]
    assert "text" in pr["negativo"]


def test_configuraciones_por_eje():
    configs = configuraciones_por_eje(config.POR_DEFECTO, "P2")
    assert [c["P2"] for c in configs] == list(config.PALETAS)
    assert all(c["P1"] == config.POR_DEFECTO["P1"] for c in configs)
    with pytest.raises(ValueError):
        construir_prompt({**config.POR_DEFECTO, "P1": "anime"})


def test_peticiones_usan_escala_del_motor():
    configs = configuraciones_por_eje(config.POR_DEFECTO, "P5")
    pa = peticiones_ronda(configs, "A")
    pb = peticiones_ronda(configs, "B")
    assert [p.escala_control for p in pa] == [v["controlnet"] for v in config.FIDELIDAD.values()]
    assert [p.escala_control for p in pb] == [v["turbo"] for v in config.FIDELIDAD.values()]
    assert [p.id for p in pa] == [f"R1-V{i}" for i in range(1, 6)]
    assert peticiones_ronda(configs, "A", ronda=2)[0].semilla == config.SEMILLAS_RONDA_1[0] + 1000


# ------------------------------------------------------------------ guardrails
@pytest.mark.parametrize("texto,motivo", [
    ("Un conejo con un cuchillo ensangrentado", "violencia"),
    ("una portada al estilo de Studio Ghibli", "nombre_protegido"),
    ("Mickey Mouse en el bosque", "nombre_protegido"),
    ("dibújalo in the style of a famous painter", "imitacion_estilo"),
    ("una casa de terror", "miedo_extremo"),
])
def test_filtro_bloquea(texto, motivo):
    r = filtrar_texto(texto)
    assert not r.ok and motivo in r.motivos
    assert "no acepta" in mensaje_usuario(r)


@pytest.mark.parametrize("texto", [
    "Un conejo que ama las flores y las cuida durante el invierno",
    "El tomate armado de valor salvó a su amiga",   # 'tomate' y 'armado' no deben bloquear
    "A little bunny reads a book under a tree",
])
def test_filtro_deja_pasar(texto):
    assert filtrar_texto(texto).ok


class ClipFalso:
    def __init__(self, no_apto: float):
        self.no_apto = no_apto

    def zero_shot(self, img, etiquetas):
        from portadas.guardrails.salida import DESCRIPTORES_NO_APTOS
        n_no = len(DESCRIPTORES_NO_APTOS)
        n_si = len(etiquetas) - n_no
        return {e: (self.no_apto / n_no if e in DESCRIPTORES_NO_APTOS else (1 - self.no_apto) / n_si)
                for e in etiquetas}


def test_revisor_salida():
    img = Image.new("RGB", (64, 96), "white")
    assert RevisorSalida(ClipFalso(0.1)).revisar(img).ok
    assert not RevisorSalida(ClipFalso(0.9)).revisar(img).ok
    assert "filtro_sd" in RevisorSalida(None).revisar(img, nsfw_sd=True).motivos


# --------------------------------------------------------------------- métricas
def test_metricas_color():
    gris = Image.new("RGB", (100, 100), (128, 128, 128))
    assert colorido(gris) == pytest.approx(0.0, abs=1e-6)
    pastel = Image.new("RGB", (100, 100), (250, 210, 225))
    naranja = Image.new("RGB", (100, 100), (240, 120, 20))
    azul = Image.new("RGB", (100, 100), (30, 90, 200))
    assert adherencia_paleta(pastel, "pastel")
    assert not adherencia_paleta(naranja, "pastel")
    assert adherencia_paleta(naranja, "calida") and not adherencia_paleta(naranja, "fria")
    assert adherencia_paleta(azul, "fria")
    assert colorido(naranja) > colorido(pastel)
    assert set(estadisticas_hsv(azul)) >= {"brillo", "saturacion"}


def test_f1_bordes_identico_y_distinto():
    b = preparar_boceto(dibujo_conejo())
    salida = b.lineas.convert("RGB")
    assert f1_bordes(b.lineas, salida)["recall"] > 0.9
    vacia = Image.new("RGB", salida.size, "white")
    assert f1_bordes(b.lineas, vacia)["f1"] == 0.0
    assert densidad_bordes(vacia) == 0.0


def test_eda_y_rangos():
    filas = [{"archivo": f"{i}.jpg", **metricas_portada(Image.new("RGB", (300, 450), (i * 20, 100, 150)),
                                                         con_paleta=False)} for i in range(5)]
    r = rangos_referencia(filas)
    assert r["n"] == 5 and "colorido" in r["metricas"]
    assert "umbral_densidad_titulo" in r


# ------------------------------------------------------------------------ datos
def test_quickdraw_render_y_lectura():
    trazos = [[[0, 100, 200], [0, 150, 0]], [[50, 50], [0, 255]]]
    img = quickdraw.renderizar(trazos)
    assert img.size == (512, 512) and np.asarray(img).min() == 0
    lineas = [json.dumps({"recognized": i % 2 == 0, "drawing": trazos, "key_id": str(i)}) for i in range(20)]
    elegidos = quickdraw.leer_lineas(lineas, n=3, pool=5)
    assert len(elegidos) == 3 and all(d["recognized"] for d in elegidos)
    preparar_boceto(img)  # un boceto de D2 pasa el preprocesamiento


def test_listado_book32():
    csv_txt = ('"1","1.jpg","http://x/1.jpg","A","B","4","Children\'s Books"\n'
               '"2","2.jpg","http://x/2.jpg","C","D","1","Biographies & Memoirs"\n')
    filas = leer_listado(csv_txt)
    assert len(filas) == 2
    assert [f["asin"] for f in muestrear_infantiles(filas, n=10)] == ["1"]


def test_historias():
    texto = ("Once upon a time there was a little bunny. The bunny loved flowers. "
             "Every day the bunny watered the flowers.<|endoftext|>"
             "Tom had a red ball. He played with the ball in the park all day long and was happy."
             "<|endoftext|>")
    hs = historias.separar_historias(texto)
    assert len(hs) == 2
    assert historias.categoria_principal(hs[0]) == "rabbit"
    assert historias.categoria_principal(hs[1]) is None
    sel = historias.seleccionar(hs, n_por_categoria=5)
    pares = historias.emparejar(sel, [{"archivo": "png/rabbit_00.png", "categoria": "rabbit"}])
    assert len(pares) == 1 and pares[0]["boceto"]["categoria"] == "rabbit"


# ---------------------------------------------------------------- motores/ronda
class MotorFalso:
    def __init__(self, nombre="A", falla=False, nsfw_primero=False):
        self.nombre, self.falla, self.nsfw_primero, self.llamadas = nombre, falla, nsfw_primero, 0

    def generar(self, control, peticiones, **kw):
        if self.falla:
            raise MotorNoDisponible("sin GPU")
        self.llamadas += 1
        out = []
        for p in peticiones:
            nsfw = self.nsfw_primero and self.llamadas == 1 and p.id.endswith("V1")
            out.append(Resultado(p, Image.new("RGB", (config.ANCHO, config.ALTO), "white"),
                                 self.nombre, 0.01, nsfw_sd=nsfw))
        return out


def test_ronda_con_respaldo_y_regeneracion(tmp_path):
    b = preparar_boceto(dibujo_conejo())
    motores = {"A": MotorFalso("A", falla=True), "B": MotorFalso("B", nsfw_primero=True)}
    ronda = generar_ronda(b, dict(config.POR_DEFECTO), "P1", motores, escena="a rabbit")
    assert ronda["engine"] == "B" and ronda["fallback_errors"]
    assert len(ronda["variations"]) == 5
    v1 = ronda["variations"][0]
    assert v1["guardrails"]["regenerations"] == 1 and v1["guardrails"]["output"] == "ok"
    assert v1["id"] == "R1-V1"
    ronda = guardar_imagenes(ronda, tmp_path)
    json.dumps(ronda)  # serializable
    assert all((tmp_path / f"R1-V{i}.png").exists() for i in range(1, 6))


def test_ronda_bloquea_instruccion():
    b = preparar_boceto(dibujo_conejo())
    with pytest.raises(ValueError):
        generar_ronda(b, dict(config.POR_DEFECTO), "P1", {"A": MotorFalso()}, instruccion="con una pistola")


def test_motor_b_turbo_fidelidad_inversa():
    from portadas.motores.motor_b import pasos_efectivos
    configs = configuraciones_por_eje(config.POR_DEFECTO, "P5")
    fuerzas = [p.escala_control for p in peticiones_ronda(configs, "B")]
    assert fuerzas == sorted(fuerzas, reverse=True)       # más fidelidad = menos ruido
    assert all(pasos_efectivos(config.PASOS_TURBO, f) >= 1 for f in fuerzas)


# ------------------------------------------------------------------ calibración
def test_calibracion_propone_niveles_en_zona_aceptable():
    from experimentos.calibracion import elegir_pasos, proponer_niveles
    resumen = {0.4: {"recall": 0.2, "acierto_estilo": 0.9}, 0.6: {"recall": 0.4, "acierto_estilo": 0.85},
               0.8: {"recall": 0.5, "acierto_estilo": 0.8}, 1.0: {"recall": 0.6, "acierto_estilo": 0.75},
               1.2: {"recall": 0.7, "acierto_estilo": 0.6}, 1.4: {"recall": 0.75, "acierto_estilo": 0.4}}
    niveles = proponer_niveles(resumen)
    assert niveles == sorted(niveles) and len(niveles) == 5
    assert niveles[0] == 0.6 and niveles[-1] == 1.0
    por_pasos = {20: {1.0: {"recall": 0.5, "acierto_estilo": 0.8}},
                 25: {1.0: {"recall": 0.51, "acierto_estilo": 0.8}},
                 30: {1.0: {"recall": 0.7, "acierto_estilo": 0.9}}}
    assert elegir_pasos(por_pasos) == 30
    por_pasos[30][1.0] = {"recall": 0.52, "acierto_estilo": 0.8}
    assert elegir_pasos(por_pasos) == 20


def test_dividir_oraciones_respeta_comillas():
    from portadas.datos.historias import dividir_oraciones

    texto = 'Tim stops. He hears a noise! "Run, Mia, run!" Tim yells. Is it a bear?'
    assert dividir_oraciones(texto) == ["Tim stops.", "He hears a noise!", '"Run, Mia, run!"',
                                        "Tim yells.", "Is it a bear?"]


def test_historias_es_limpieza_y_categoria():
    from portadas.datos.historias_es import categoria_es, es_verso, html_a_texto

    html = ('<style>.x{}</style><div class="noprint ws-noexport">Descargar ePub</div>'
            '<p>LA TORTUGA</p><p><span><img alt="H" src="x.jpg"/></span>abía una vez un gato.'
            '<sup class="reference">[1]</sup></p><p>El gato y el gatito vivían en una casa.</p>')
    texto = html_a_texto(html, "La tortuga")
    assert texto.startswith("Había una vez un gato.")
    assert "Descargar" not in texto and "[1]" not in texto and ".x{}" not in texto
    assert categoria_es(texto) == "cat"
    assert categoria_es("Un día de lluvia.") == "otro"
    assert es_verso("\n".join(["Un verso corto"] * 8))
    assert not es_verso(texto)


def test_aplicar_calibracion_reemplaza_valores():
    from experimentos.aplicar_calibracion import RUTA_CONFIG, aplicar

    texto = RUTA_CONFIG.read_text(encoding="utf-8")
    propuesta = {"pasos": 20, "fidelidad": {"muy_baja": 0.4, "baja": 0.55, "media": 0.7,
                                            "alta": 0.85, "muy_alta": 1.0}}
    nuevo = aplicar(texto, propuesta)
    assert '"media": {"controlnet": 0.70, "turbo": 0.70}' in nuevo
    assert "\nPASOS = 20" in nuevo
    assert "PASOS_TURBO = 4" in nuevo  # no se toca


def test_revision_lora():
    from experimentos.lora import revisar_ficha, resumir

    ok = revisar_ficha("alguien/cuentos-sd15", {"cardData": {"license": "creativeml-openrail-m",
                                                              "base_model": "runwayml/stable-diffusion-v1-5"}})
    assert ok["ok"] and not ok["datos_entrenamiento_documentados"]
    sdxl = revisar_ficha("x/y", {"cardData": {"license": "creativeml-openrail-m",
                                              "base_model": "stabilityai/stable-diffusion-xl-base-1.0"}})
    assert not sdxl["ok"]
    artista = revisar_ficha("x/quentin-blake-style", {"cardData": {"license": "mit",
                                                                   "base_model": "stable-diffusion-v1-5"}})
    assert not artista["ok"]
    sin_licencia = revisar_ficha("x/y", {"cardData": {"base_model": "stable-diffusion-v1-5"}})
    assert not sin_licencia["ok"]
    filas = [{"escala_lora": 0.0, "acierto_estilo": 1.0, "clipscore": 30.0, "f1_bordes": 0.4,
              "lpips_vs_base": None, "latencia_s": 2.0, "nsfw_sd": False},
             {"escala_lora": 1.0, "acierto_estilo": 0.0, "clipscore": 28.0, "f1_bordes": 0.3,
              "lpips_vs_base": 0.5, "latencia_s": 2.2, "nsfw_sd": False}]
    r = resumir(filas)
    assert "lpips_vs_base" not in r["0.0"] and r["1.0"]["lpips_vs_base"] == 0.5
