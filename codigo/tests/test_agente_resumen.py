"""Pruebas del agente de explicación y su validador (sin GPU: LLM falso)."""
import json

import pytest

from portadas import config
from portadas.agentes.resumen import (hechos, resumen_plantilla, resumir, separar_bloque, validar)


def _var(i, ronda, params, decision, reasons=None, comentario=""):
    return {"id": f"R{ronda}-V{i}", "params": params, "decision": decision,
            "reasons": reasons or [], "reason": comentario, "image": "NO_DEBE_VERSE", "prompt": "secreto"}


def sesion():
    base = dict(config.POR_DEFECTO)
    estilos = list(config.ESTILOS)
    r1 = {"round": 1, "axis": "P1", "planner": {"method": "eje completo (ronda 1)", "free_params": [],
                                                  "favorites": {}},
          "variations": [_var(i + 1, 1, {**base, "P1": e}, d, rs, c) for i, (e, d, rs, c) in enumerate([
              (estilos[0], "accepted", None, ""), (estilos[1], "rejected", ["colores"], "muy oscuro"),
              (estilos[2], "accepted", None, ""), (estilos[3], "rejected", None, ""),
              (estilos[4], "blocked", None, "")])]}
    return {"rounds": [r1], "story": {"personajes": ["rabbit"], "lugar": "garden"},
            "typography_changes": [{"id": "R1-V1", "cambio": "fuente: Andika"}]}


BUENO = ("Ronda 1 (eje: Estilo) - Aceptadas: R1-V1 (acuarela), R1-V3 (collage). "
         "Rechazadas: R1-V2 (lapices) por colores, R1-V4 (vectorial). R1-V5 fue bloqueada por los guardrails. En R1-V1 cambió la fuente a Andika.\n"
         '{"accepted": ["R1-V1", "R1-V3"], "rejected": ["R1-V2", "R1-V4"]}')


def llm_fijo(*respuestas):
    cola, llamadas = list(respuestas), []

    def f(sistema, mensaje):
        llamadas.append(mensaje)
        return cola.pop(0) if len(cola) > 1 else cola[0]
    f.llamadas = llamadas
    return f


def test_resumen_correcto_pasa_a_la_primera():
    r = resumir(sesion(), llm_fijo(BUENO))
    assert r["origen"] == "llm" and r["intentos"] == 1 and "R1-V1" in r["texto"]
    assert "{" not in r["texto"]                      # el bloque JSON no se muestra


def test_el_llm_no_recibe_imagenes_ni_prompts():
    llm = llm_fijo(BUENO)
    resumir(sesion(), llm)
    assert "NO_DEBE_VERSE" not in llm.llamadas[0] and "secreto" not in llm.llamadas[0]
    assert "muy oscuro" in llm.llamadas[0] and "Andika" in llm.llamadas[0]


def test_detecta_bloque_que_no_coincide():
    texto, bloque = separar_bloque(BUENO.replace('"R1-V4"', '"R1-V3"'))
    assert any("rejected" in e for e in validar(texto, bloque, sesion()))
    assert validar(*separar_bloque("sin bloque"), sesion())[0].startswith("falta el bloque")


def test_detecta_id_inventado_y_faltante():
    malo = BUENO.replace("R1-V4 (vectorial)", "R1-V9 (vectorial)")
    errores = validar(*separar_bloque(malo), sesion())
    assert any("R1-V9" in e and "no existen" in e for e in errores)
    assert any("faltan" in e and "R1-V4" in e for e in errores)


def test_detecta_id_en_la_categoria_equivocada():
    malo = BUENO.replace("Aceptadas: R1-V1 (acuarela), R1-V3 (collage).", "Aceptadas: R1-V1 (acuarela), R1-V2 (lapices).") \
                .replace("Rechazadas: R1-V2 (lapices) por colores,", "Rechazadas: R1-V3 (collage),")
    errores = validar(*separar_bloque(malo), sesion())
    assert any("no están aceptadas" in e for e in errores) and any("no están rechazadas" in e for e in errores)


def test_detecta_preferencia_por_valor_nunca_aceptado():
    s = sesion()
    texto = BUENO.split("\n")[0] + " Parece que prefiere el estilo vectorial.\n" + BUENO.split("\n")[1]
    assert any("vectorial" in e for e in validar(*separar_bloque(texto), s))
    ok = BUENO.split("\n")[0] + " Parece que prefiere el estilo acuarela.\n" + BUENO.split("\n")[1]
    assert validar(*separar_bloque(ok), s) == []


def _con(extra: str) -> str:
    """BUENO con una frase adicional en el texto (antes del bloque JSON)."""
    linea, bloque = BUENO.split("\n")
    return linea + " " + extra + "\n" + bloque


def test_la_preferencia_negada_no_es_falso_positivo():
    texto = _con("Prefiere acuarela y no le gustó el estilo vectorial.")
    assert validar(*separar_bloque(texto), sesion()) == []


def test_detecta_al_azar_en_un_parametro_que_no_se_muestreo():
    s = sesion()
    s["rounds"][0]["planner"]["free_params"] = ["P2", "P3"]
    malo = _con("El estilo vectorial se eligió al azar.")
    assert any("vectorial" in e and "azar" in e for e in validar(*separar_bloque(malo), s))
    bien = _con("La paleta pastel se eligió al azar.")
    assert validar(*separar_bloque(bien), s) == []


def test_el_azar_se_revisa_en_la_ronda_de_la_que_se_habla():
    s = sesion()
    r2 = {"round": 2, "axis": "P2", "planner": {"method": "thompson", "free_params": ["P1", "P3"], "favorites": {}},
          "variations": [_var(i, 2, dict(config.POR_DEFECTO, P2=p), "accepted") for i, p in enumerate(config.PALETAS, 1)]}
    s["rounds"].append(r2)
    base = ("Ronda 1 (eje: Estilo) - Aceptadas: R1-V1 (acuarela), R1-V3 (collage). Rechazadas: R1-V2 (lapices) por "
            "colores, R1-V4 (vectorial). R1-V5 fue bloqueada por los guardrails. En R1-V1 cambió la fuente a Andika.\n")
    cierre = ("Ronda 2 (eje: Paleta) - Aceptadas: R2-V1, R2-V2, R2-V3, R2-V4, R2-V5.\n"
              '{"accepted": ["R1-V1","R1-V3","R2-V1","R2-V2","R2-V3","R2-V4","R2-V5"], "rejected": ["R1-V2","R1-V4"]}')
    # Falso: en la ronda 1 no hubo azar, aunque P1 sí fue libre en la ronda 2.
    malo = base + "En la ronda 1 el estilo acuarela se eligió al azar.\n" + cierre
    assert any("acuarela" in e and "ronda 1" in e for e in validar(*separar_bloque(malo), s))
    # Verdadero: en la ronda 2 el estilo (P1) fue un parámetro libre.
    bien = base + cierre.replace("\n{", " En la ronda 2 el estilo acuarela se eligió al azar.\n{", 1)
    assert validar(*separar_bloque(bien), s) == []


def test_exige_tipografia_y_motivos():
    sin_tipo = BUENO.replace(" En R1-V1 cambió la fuente a Andika.", "")
    assert any("tipografía" in e for e in validar(*separar_bloque(sin_tipo), sesion()))
    sin_motivo = BUENO.replace(" por colores", "")
    assert any("motivo" in e and "R1-V2" in e for e in validar(*separar_bloque(sin_motivo), sesion()))
    parafraseado = BUENO.replace(" por colores", " porque era muy oscuro")
    assert validar(*separar_bloque(parafraseado), sesion()) == []


def test_reintenta_con_el_error_y_se_recupera():
    llm = llm_fijo("Aceptó todo.", BUENO)
    r = resumir(sesion(), llm)
    assert r["origen"] == "llm" and r["intentos"] == 2
    assert "errores" in llm.llamadas[1] and "falta el bloque" in llm.llamadas[1]


def test_plantilla_si_el_llm_nunca_acierta():
    r = resumir(sesion(), llm_fijo("Todo bien."), reintentos=2)
    assert r["origen"] == "plantilla" and r["intentos"] == 3 and len(r["errores"]) == 3
    assert "R1-V2 (lapices)" in r["texto"] and "muy oscuro" in r["texto"] and "R1-V5" in r["texto"]
    assert "Andika" in r["texto"]


def test_la_plantilla_pasa_el_propio_validador():
    s = sesion()
    assert validar(resumen_plantilla(s), {"accepted": ["R1-V1", "R1-V3"], "rejected": ["R1-V2", "R1-V4"]}, s) == []


def test_sesion_sin_rondas():
    with pytest.raises(ValueError):
        resumir({"rounds": []}, llm_fijo(BUENO))


def test_hechos_incluye_el_planificador():
    assert hechos(sesion())["rondas"][0]["planificador"]["metodo"].startswith("eje completo")


# ---- caso real: sesión de Colab con Qwen (16-nov), el resumen inventó una fuente y omitió al planificador
def sesion_colab():
    base = dict(config.POR_DEFECTO)
    r1 = {"round": 1, "axis": "P1", "planner": {"method": "eje completo (ronda 1)", "free_params": [], "favorites": {}},
          "variations": [
              _var(1, 1, {**base, "P1": "acuarela"}, "accepted"), _var(2, 1, {**base, "P1": "lapices"}, "accepted"),
              _var(3, 1, {**base, "P1": "collage"}, "accepted"),
              _var(4, 1, {**base, "P1": "vectorial"}, "rejected", ["ambiente"]),
              _var(5, 1, {**base, "P1": "plastilina"}, "rejected", ["estilo"])]}
    r2 = {"round": 2, "axis": "P4", "planner": {"method": "thompson", "free_params": ["P1", "P2", "P5"], "favorites": {}},
          "variations": [
              _var(1, 2, {**base, "P4": "alegre", "P2": "fria"}, "rejected", ["colores"]),
              _var(2, 2, {**base, "P4": "aventura"}, "rejected", ["estilo"]),
              _var(3, 2, {**base, "P4": "calma"}, "rejected", [], "feo"),
              _var(4, 2, {**base, "P4": "misterio"}, "accepted"),
              _var(5, 2, {**base, "P4": "humor"}, "rejected", ["se aleja del boceto"])]}
    return {"rounds": [r1, r2], "story": {}, "typography_changes": []}


QWEN_COLAB = (
    "Ronda 1 (eje: Estilo) - Aceptadas: R1-V1 (acuarela), R1-V2 (lapices), R1-V3 (collage). Rechazadas: R1-V4 "
    "(vectorial; motivo: ambiente), R1-V5 (plastilina; motivo: estilo). En R1-V1 el usuario cambió la fuente a Fredoka.\n"
    "Ronda 2 (eje: Ambiente) - Aceptadas: R2-V4 (misterio). Rechazadas: R2-V1 (alegre; motivo: colores), R2-V2 "
    "(aventura; motivo: estilo), R2-V3 (calma; comentario: feo), R2-V5 (humor; motivo: se aleja del boceto).\n"
    '{"accepted": ["R1-V1","R1-V2","R1-V3","R2-V4"], "rejected": ["R1-V4","R1-V5","R2-V1","R2-V2","R2-V3","R2-V5"]}')


def test_caso_real_fuente_inventada_y_planificador_omitido():
    errores = validar(*separar_bloque(QWEN_COLAB), sesion_colab())
    assert any("tipografía" in e and "ninguno" in e for e in errores)
    assert any("planificador" in e and "ronda 2" in e for e in errores)


def test_caso_real_corregido_pasa():
    ok = (QWEN_COLAB.replace(" En R1-V1 el usuario cambió la fuente a Fredoka.", "")
          .replace("\n{", " Por el planificador, el estilo, la paleta y la fidelidad se eligieron al azar según "
                           "lo aceptado antes.\n{"))
    assert validar(*separar_bloque(ok), sesion_colab()) == []


def test_no_hubo_cambios_de_tipografia_es_valido():
    ok = QWEN_COLAB.replace(" En R1-V1 el usuario cambió la fuente a Fredoka.", " No hubo cambios de tipografía.") \
                   .replace("\n{", " El planificador eligió estilo, paleta y fidelidad al azar.\n{")
    assert validar(*separar_bloque(ok), sesion_colab()) == []


def test_fuente_distinta_a_la_registrada():
    malo = BUENO.replace("Andika", "Fredoka")
    assert any("Fredoka" in e for e in validar(*separar_bloque(malo), sesion()))


def test_la_plantilla_explica_al_planificador_y_pasa_el_validador():
    s = sesion_colab()
    t = resumen_plantilla(s)
    assert "El planificador eligió al azar" in t and "Estilo" in t
    assert validar(t, {"accepted": ["R1-V1", "R1-V2", "R1-V3", "R2-V4"],
                       "rejected": ["R1-V4", "R1-V5", "R2-V1", "R2-V2", "R2-V3", "R2-V5"]}, s) == []
