"""Pruebas del flujo de la aplicación (sin GPU ni Gradio: generador y LLM falsos)."""
import json

import pytest
from PIL import Image

from app import flujo
from portadas import config


@pytest.fixture(autouse=True)
def carpeta_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(flujo, "CARPETA", tmp_path / "interfaz")


def preparar_falso(img, zona):
    return {"boceto": True, "zona": zona}


def generador_falso(bloquear=()):
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


def nueva(motor="A", **kw):
    return flujo.iniciar(Image.new("L", (64, 64)), "El conejo", motor, dict(config.POR_DEFECTO),
                         "a rabbit in a garden", preparar=preparar_falso, **kw)


def decidir(e, ronda, ops, comentarios=None, motivos=None):
    return flujo.cerrar_ronda(e, ronda, ops, comentarios or [""] * 5, motivos or [[] for _ in range(5)])


A, R, S = "Aceptar", "Rechazar", "Sin decidir"


def test_escena_editable():
    assert flujo.partir(" Rabbit, Flowers ;fox ") == ["rabbit", "flowers", "fox"]
    assert flujo.construir_escena("rabbit", "flowers", "garden", "sunset") == "a rabbit with flowers in a garden at sunset"
    assert flujo.construir_escena("", "", "", "") == ""


def test_analizar_historia_bloqueada_da_mensaje_claro():
    with pytest.raises(ValueError, match="no apto"):
        flujo.analizar_historia("Un hombre con una pistola mata al lobo", lambda s, m: "{}")


def test_iniciar_rechaza_boceto_vacio_y_textos_bloqueados():
    with pytest.raises(ValueError, match="boceto"):
        flujo.iniciar(None, "t", "A", dict(config.POR_DEFECTO), "x", preparar=preparar_falso)
    with pytest.raises(ValueError, match="título"):
        flujo.iniciar(Image.new("L", (8, 8)), "pistola sangre", "A", dict(config.POR_DEFECTO), "x",
                      preparar=preparar_falso)


def test_decisiones_validan_y_distinguen_bloqueadas():
    e = nueva()
    r = flujo.proponer_ronda(e, "P1", generador_falso(bloquear=(5,)))
    with pytest.raises(ValueError, match="Falta decidir"):
        flujo.aplicar_decisiones(r, [A, S, A, A, S], [""] * 5)
    flujo.aplicar_decisiones(r, [A, R, A, R, S], ["", "muy oscura", "", "", ""],
                             [[], ["colores", "inventado"], [], [], []])
    assert [v["decision"] for v in r["variations"]] == ["accepted", "rejected", "accepted", "rejected", "blocked"]
    v2 = r["variations"][1]
    assert v2["reasons"] == ["colores"] and v2["reason"] == "muy oscura"     # motivo desconocido se ignora
    assert r["variations"][0]["reasons"] == [] and r["variations"][0]["reason"] == ""


def test_ronda_pone_titulo_a_cada_portada_visible():
    e = nueva()
    r = flujo.proponer_ronda(e, "P1", generador_falso(bloquear=(5,)))
    assert [bool(v["titled_path"]) for v in r["variations"]] == [True] * 4 + [False]
    assert r["variations"][0]["title_layout"]["contraste"] >= 4.5
    assert r["axis"] == "P1"


def test_sesion_completa_tres_rondas_y_resumen(tmp_path):
    e = nueva()
    gen = generador_falso()
    r1 = flujo.proponer_ronda(e, "P1", gen)
    decidir(e, r1, [A, R, A, R, A], ["", "muy oscuro", "", "", ""], [[], ["colores"], [], [], []])
    assert flujo.ejes_disponibles(e) == ["P2", "P3", "P4", "P5"]
    r2 = flujo.proponer_ronda(e, "P2", gen)
    assert r2["planner_plan"]["free"] == ["P1", "P3", "P4", "P5"]             # Thompson en la ronda 2
    decidir(e, r2, [A, A, A, R, R])
    r3 = flujo.proponer_ronda(e, "P4", gen)
    decidir(e, r3, [A] * 5)
    assert flujo.ejes_disponibles(e) == [] and e.sesion.terminada()
    with pytest.raises(ValueError):
        flujo.proponer_ronda(e, "P3", gen)

    # Un LLM que no cumple el formato termina en la plantilla verificada.
    resumen = flujo.resumir_sesion(e, lambda sistema, mensaje: "Todo bien.")
    assert resumen["origen"] == "plantilla" and "R1-V2 (lapices)" in resumen["texto"]

    datos = json.loads((e.carpeta / "sesion.json").read_text(encoding="utf-8"))
    assert len(datos["rounds"]) == 3 and datos["summary"]["origen"] == "plantilla"
    assert datos["rounds"][0]["variations"][1]["reason_axes"] == ["P2"]
    assert datos["rounds"][1]["planner"]["method"] == "thompson"
    assert "borradores" not in datos["summary"]
    assert "a rabbit in a garden" in datos["scene"] and "boceto" not in json.dumps(datos).lower()


def test_motor_b_no_ofrece_fidelidad_como_eje():
    assert "P5" not in flujo.ejes_disponibles(nueva(motor="B"))


def test_resumir_exige_una_ronda_cerrada():
    with pytest.raises(ValueError):
        flujo.resumir_sesion(nueva(), lambda s, m: "x")


def test_fixed_solo_lista_lo_que_no_cambio_entre_las_cinco():
    e = nueva()
    gen = generador_falso()
    r1 = flujo.proponer_ronda(e, "P1", gen)
    assert r1["fixed"] == {p: v for p, v in config.POR_DEFECTO.items() if p != "P1"}   # ronda 1: todo lo demás
    decidir(e, r1, [A] * 5)
    r2 = flujo.proponer_ronda(e, "P2", gen)
    for p, v in r2["fixed"].items():
        assert all(x["params"][p] == v for x in r2["variations"])
    assert "P2" not in r2["fixed"] and r2["fixed"]["P6"] == "superior"
    varia = [p for p in r2["planner_plan"]["free"] if p not in r2["fixed"]]
    assert set(r2["planner_plan"]["free"]) - set(r2["fixed"]) == set(varia)
