"""Pruebas del agente tipográfico y del renderizador con estilo (sin GPU: LLM falso)."""
import json
from functools import partial

import numpy as np
import pytest
from PIL import Image

from app import flujo
from portadas import config
from portadas.agentes.tipografia import medidas_zona, proponer, titular_basico, titular_con_agente
from portadas.titulo import CATALOGO, CONTRASTE_MIN, LIMITES, fuentes_disponibles, limitar, render_titulo

PARAMS = {"P1": "acuarela", "P3": "7-9", "P4": "alegre"}


def lienzo(color=(240, 235, 220)):
    return Image.new("RGB", (config.ANCHO, config.ALTO), color)


def llm_que_responde(texto):
    def f(sistema, mensaje):
        assert "JSON" in sistema and "titulo" in mensaje
        return texto
    return f


def test_las_fuentes_del_catalogo_estan_en_el_repositorio():
    assert set(fuentes_disponibles()) == set(CATALOGO)
    from portadas.titulo import FUENTES_DIR
    for n in ("Andika", "Fredoka", "Baloo2", "LilitaOne"):
        assert (FUENTES_DIR / f"OFL-{n}.txt").exists(), f"falta la licencia de {n}"


def test_limitar_recorta_y_cae_a_valores_validos():
    e = limitar({"fuente": "Comic Sans", "tamano": 9, "curva": -5, "onda": "x", "inclinacion": 99,
                 "contorno": 0, "color": "rojo"}, "7-9")
    assert e["fuente"] == "Fredoka"                               # fuente fuera del catálogo: la de la edad
    assert e["tamano"] == LIMITES["tamano"][1] and e["curva"] == LIMITES["curva"][0]
    assert e["onda"] == 0.0 and e["inclinacion"] == LIMITES["inclinacion"][1]
    assert e["contorno"] == LIMITES["contorno"][0] and e["color"] is None


def test_lectores_principiantes_solo_usan_letras_sencillas_y_poca_deformacion():
    e = limitar({"fuente": "LilitaOne", "onda": 0.15, "inclinacion": 8}, "4-6")
    assert e["fuente"] in ("Andika", "Fredoka") and e["onda"] <= 0.06 and e["inclinacion"] <= 4


@pytest.mark.parametrize("estilo", [dict(fuente="Fredoka", curva=0.4, onda=0.15, inclinacion=8),
                                    dict(fuente="LilitaOne", curva=-0.4, contorno=0.1),
                                    dict(fuente="Baloo2", color="#FFFF00"), dict(color="#777777")])
@pytest.mark.parametrize("fondo", [(250, 250, 250), (20, 20, 40), (128, 128, 128), (255, 255, 0)])
def test_cualquier_estilo_cumple_el_contraste_y_no_se_sale_de_la_zona(estilo, fondo):
    img = lienzo(fondo)
    out, info = render_titulo(img, "Tomás y las galletas del dragón valiente", "superior", "7-9", **estilo)
    assert info["contraste"] >= CONTRASTE_MIN
    diff = np.abs(np.asarray(out, dtype=int) - np.asarray(img, dtype=int)).sum(axis=2)
    filas = np.where(diff.sum(axis=1) > 0)[0]
    assert filas.max() < config.ALTO * 0.31                        # nada fuera de la zona superior


def test_el_estilo_se_dibuja_distinto_y_es_determinista():
    a = render_titulo(lienzo(), "Hola mundo", "superior", "7-9", fuente="Fredoka")[0]
    b = render_titulo(lienzo(), "Hola mundo", "superior", "7-9", fuente="Fredoka", curva=0.3)[0]
    c = render_titulo(lienzo(), "Hola mundo", "superior", "7-9", fuente="Fredoka", curva=0.3)[0]
    assert not np.array_equal(np.asarray(a), np.asarray(b)) and np.array_equal(np.asarray(b), np.asarray(c))


def test_acepta_el_color_del_selector_de_color():
    _, info = render_titulo(lienzo(), "Hola", "superior", "7-9", color="rgba(198, 40, 40, 1)")
    assert info["estilo"]["color"] == [198, 40, 40]


def test_medidas_de_la_zona_distinguen_fondos():
    claro, oscuro = medidas_zona(lienzo((250, 250, 250)), "superior"), medidas_zona(lienzo((10, 10, 10)), "superior")
    assert claro["brillo"] > 0.9 and oscuro["brillo"] < 0.1 and claro["bordes"] == 0.0
    assert claro["contraste_oscuro"] > claro["contraste_claro"] and oscuro["contraste_claro"] > oscuro["contraste_oscuro"]
    assert medidas_zona(lienzo(), "sin") == {}


def test_el_agente_propone_y_sus_valores_se_recortan():
    respuesta = "Claro:\n```json\n" + json.dumps({"fuente": "LilitaOne", "tamano": 0.5, "curva": 0.2, "onda": 0.1,
                                                  "inclinacion": 3, "contorno": 0.06, "color": "#2E5E3A"}) + "\n```"
    estilo, meta = proponer(lienzo(), "El conejo", "superior", PARAMS, llm_que_responde(respuesta))
    assert meta["origen"] == "agente" and meta["intentos"] == 1
    assert estilo["fuente"] == "LilitaOne" and estilo["tamano"] == LIMITES["tamano"][1]      # recortado
    assert estilo["color"] == (46, 94, 58)


def test_si_el_agente_falla_se_usa_la_disposicion_por_defecto():
    llamadas = []

    def roto(sistema, mensaje):
        llamadas.append(mensaje)
        return "no sé"
    estilo, meta = proponer(lienzo(), "El conejo", "superior", PARAMS, roto)
    assert meta["origen"] == "respaldo" and meta["intentos"] == 2 and len(llamadas) == 2
    assert "invalid" in llamadas[1]                                  # el reintento dice qué falló
    assert estilo == limitar({}, "7-9")
    assert proponer(lienzo(), "El conejo", "superior", PARAMS, None)[1]["origen"] == "respaldo"
    assert proponer(lienzo(), "El conejo", "sin", PARAMS, roto)[1]["origen"] == "respaldo"


def test_el_agente_no_deja_el_limite_de_tokens_cambiado():
    class Falso:
        max_tokens = 512

        def __call__(self, s, m):
            assert self.max_tokens <= 160
            return '{"fuente": "Andika"}'
    llm = Falso()
    proponer(lienzo(), "Hola", "superior", PARAMS, llm)
    assert llm.max_tokens == 512


def test_titular_con_agente_deja_registro_del_origen():
    llm = llm_que_responde('{"fuente": "Baloo2", "curva": 0.2, "color": "#1B3A57"}')
    img, info = titular_con_agente(lienzo(), "El conejo", "superior", "10-12", PARAMS, llm)
    assert info["agente"]["origen"] == "agente" and info["estilo"]["fuente"] == "Baloo2"
    assert info["contraste"] >= CONTRASTE_MIN
    assert titular_basico(lienzo(), "El conejo", "superior", "10-12")[1]["estilo"]["fuente"] == "Baloo2"


# ------------------------------------------------------------------ flujo: el agente y la edición de la persona
@pytest.fixture(autouse=True)
def carpeta_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(flujo, "CARPETA", tmp_path / "interfaz")


def _preparar_falso(img, zona):
    return {"boceto": True, "zona": zona}


def _nueva():
    return flujo.iniciar(Image.new("L", (64, 64)), "El conejo", "A", dict(config.POR_DEFECTO),
                         "a rabbit in a garden", preparar=_preparar_falso)


def _generador_falso(bloquear=()):
    """Reemplaza a generar_real: crea 5 imágenes de color y devuelve la ronda como el motor real."""
    def f(e, configs, numero):
        vs = []
        for i, cfg in enumerate(configs, start=1):
            ruta = None
            if i not in bloquear:
                ruta = e.carpeta / f"r{numero}_R{numero}-V{i}.png"
                Image.new("RGB", (config.ANCHO, config.ALTO), (200, 220, 240)).save(ruta)
            vs.append({"id": f"R{numero}-V{i}", "params": cfg, "image_path": str(ruta) if ruta else None,
                       "decision": None, "prompt": "p", "seed": 1})
        return {"round": numero, "engine": e.motor, "variations": vs}
    return f


def _ronda():
    e = _nueva()
    llm = llm_que_responde('{"fuente": "Fredoka", "tamano": 0.06, "curva": 0.1, "color": "#1B3A57"}')
    return e, flujo.proponer_ronda(e, "P1", _generador_falso(), titulador=partial(titular_con_agente, llm=llm))


def test_la_ronda_guarda_lo_que_propuso_el_agente():
    _, r = _ronda()
    t = r["variations"][0]["typography"]
    assert t["agent"]["origin"] == "agente" and t["agent"]["style"]["fuente"] == "Fredoka" and t["user_edit"] is None


def test_editar_el_titulo_redibuja_solo_el_titulo_y_queda_registrado():
    e, r = _ronda()
    v = r["variations"][1]
    antes = v["titled_path"]
    imagen_original = Image.open(v["image_path"]).tobytes()
    flujo.editar_titulo(e, v, fuente="Andika", curva=-0.2, color="#C62828")
    assert v["typography"]["user_edit"]["fuente"] == "Andika" and v["typography"]["user_edit"]["curva"] == -0.2
    assert v["title_layout"]["estilo"]["fuente"] == "Andika" and v["title_layout"]["contraste"] >= CONTRASTE_MIN
    assert Image.open(v["image_path"]).tobytes() == imagen_original          # la portada no se regenera
    assert v["titled_path"] == antes                                          # mismo archivo, título nuevo
    assert e.cambios_tipografia == [{"id": v["id"], "cambio": "fuente: Andika"}]
    assert flujo.sesion_para_resumen(e)["typography_changes"] == e.cambios_tipografia


def test_editar_solo_el_tamano_no_cuenta_como_cambio_de_fuente():
    e, r = _ronda()
    flujo.editar_titulo(e, r["variations"][0], tamano=0.09)
    assert r["variations"][0]["typography"]["user_edit"] == {"tamano": 0.09} and e.cambios_tipografia == []


def test_cambiar_dos_veces_la_fuente_deja_un_solo_registro():
    e, r = _ronda()
    v = r["variations"][0]
    flujo.editar_titulo(e, v, fuente="LilitaOne")
    flujo.editar_titulo(e, v, fuente="Baloo2")
    assert e.cambios_tipografia == [{"id": v["id"], "cambio": "fuente: Baloo 2"}]


def test_no_se_edita_una_portada_bloqueada():
    e = _nueva()
    r = flujo.proponer_ronda(e, "P1", _generador_falso(bloquear=(5,)))
    with pytest.raises(ValueError, match="no se mostró"):
        flujo.editar_titulo(e, r["variations"][4], fuente="Andika")
