"""Pruebas de la etapa 5 (planificador, agente de historia, explicador). CPU, sin modelos."""
from __future__ import annotations

import json

import numpy as np
import pytest

from portadas import config
from portadas.agente import explicador, historia
from portadas.agente.planificador import Planificador, parametros_penalizados
from portadas.agente.simulacion import UsuarioSimulado, experimento_e2, simular_sesion


def ronda_con_decisiones(plan, r, eje, decisiones, base=None):
    """decisiones: lista de 5 (decision, motivos)."""
    prop = plan.proponer(r, base or dict(config.POR_DEFECTO), eje)
    vars_ = []
    for i, (cfg, (dec, mot)) in enumerate(zip(prop["configs"], decisiones), start=1):
        vars_.append({"id": f"R{r}-V{i}", "params": cfg, "decision": dec, "reasons": mot, "comment": ""})
    return {"round": r, "axis": eje, "planner": prop["planner"], "variations": vars_}


# ------------------------------------------------------------ planificador
def test_ronda1_es_configuracion_por_eje():
    prop = Planificador().proponer(1, dict(config.POR_DEFECTO), "P1")
    assert [c["P1"] for c in prop["configs"]] == list(config.ESTILOS)
    assert all(c["P2"] == config.POR_DEFECTO["P2"] for c in prop["configs"])
    assert prop["planner"]["policy"] == "thompson"


def test_actualizacion_beta_segun_ecuacion():
    plan = Planificador()
    r = ronda_con_decisiones(plan, 1, "P1", [("accepted", []), ("rejected", ["colores"]),
                                             ("rejected", []), ("rejected", ["no_existe"]), (None, [])])
    plan.actualizar(r)
    assert plan.alfa["P1"]["acuarela"] == 2 and plan.alfa["P2"]["pastel"] == 2  # aceptada: todos los p
    assert plan.beta["P2"]["pastel"] == 2           # V2 rechazada por colores -> solo P2
    assert plan.beta["P1"]["lapices"] == 1          # ... y no el estilo
    assert plan.beta["P1"]["collage"] == 2          # V3 sin motivo -> se penaliza el eje
    assert plan.beta["P1"]["vectorial"] == 2        # motivo desconocido -> eje
    assert plan.beta["P1"]["plastilina"] == 1       # sin decisión: no cambia


def test_parametros_penalizados():
    assert parametros_penalizados(["colores", "estilo", "colores"], "P4") == ["P2", "P1"]
    assert parametros_penalizados([], "P4") == ["P4"]


def test_thompson_explota_lo_aceptado():
    plan = Planificador(semilla=1)
    for _ in range(8):  # acuarela aceptada muchas veces, el resto rechazado por estilo
        plan.alfa["P1"]["acuarela"] += 1
        for v in ("lapices", "collage", "vectorial", "plastilina"):
            plan.beta["P1"][v] += 1
    prop = plan.proponer(2, dict(config.POR_DEFECTO), "P2")
    estilos = [c["P1"] for c in prop["configs"]]
    assert estilos.count("acuarela") >= 4
    assert [c["P2"] for c in prop["configs"]] == list(config.PALETAS)  # el eje recorre sus 5 valores
    assert "P1" in prop["planner"]["sampled"] and "P2" not in prop["planner"]["sampled"]
    assert prop["planner"]["posterior_before"]["P1"]["acuarela"] == [9.0, 1.0]


def test_fijos_se_respetan_y_limite_de_rondas():
    plan = Planificador(semilla=3)
    base = {**config.POR_DEFECTO, "P1": "collage"}
    prop = plan.proponer(2, base, "P2", fijos=["P1"])
    assert all(c["P1"] == "collage" for c in prop["configs"])
    with pytest.raises(ValueError):
        plan.proponer(config.MAX_RONDAS + 1, base, "P2")
    with pytest.raises(ValueError):
        Planificador("codicioso")


def test_e2_thompson_supera_aleatorio():
    res = experimento_e2(n_usuarios=50, repeticiones=3)
    t = res["resumen"]["thompson"]["media_por_ronda"]
    a = res["resumen"]["aleatoria"]["media_por_ronda"]
    assert len(t) == 3
    assert t[0] == pytest.approx(a[0])          # ronda 1 idéntica: mismos usuarios, misma propuesta
    assert t[2] > a[2]                          # en la ronda 3 Thompson ya explota lo aprendido
    assert res["resumen"]["criterio"]["aceptacion ronda 2 > ronda 1 (thompson)"]


def test_usuario_simulado_marca_motivos():
    u = UsuarioSimulado(np.random.default_rng(0), p_coincide=1.0, p_no_coincide=0.0)
    cfg = dict(config.POR_DEFECTO)
    for p, v in u.preferencia.items():
        cfg[p] = v
    assert u.decidir(cfg)["decision"] == "accepted"
    p0 = next(iter(u.preferencia))
    otro = next(v for v in config.PARAMETROS[p0] if v != u.preferencia[p0])
    d = u.decidir({**cfg, p0: otro})
    motivo = {p: m for m, p in config.MOTIVOS_RECHAZO.items()}[p0]
    assert d["decision"] == "rejected" and d["reasons"] == [motivo]


# ------------------------------------------------------------ agente de historia
def test_aparece_en_tildes_y_plurales():
    h = "Un conejo que ama las flores vive en el jardín. Había dos peces."
    assert historia.aparece_en("flor", h)
    assert historia.aparece_en("Jardin", h)
    assert historia.aparece_en("pez", h)
    assert not historia.aparece_en("zorro", h)
    assert historia.aparece_en("rabbit", "The rabbits played.")
    assert historia.aparece_en("teddy bear", "She hugged her teddy bear.")


def test_detectar_idioma():
    assert historia.detectar_idioma("Había una vez un gato que vivía en la casa") == "es"
    assert historia.detectar_idioma("Once upon a time there was a cat in the house") == "en"


def llm_historia_falso(respuesta):
    def llm(mensajes):
        assert mensajes[0]["role"] == "system" and "Historia:" in mensajes[-1]["content"]
        return "Aquí está:\n```json\n" + json.dumps(respuesta) + "\n```"
    return llm


def test_extraer_elementos_verifica_y_traduce():
    h = "Un conejo que ama las flores las cuida en su jardín durante el invierno."
    resp = {"personajes": [{"es": "conejo", "en": "rabbit"}, {"es": "zorro", "en": "fox"}],
            "objetos": [{"es": "flor", "en": "flower"}], "lugar": {"es": "jardín", "en": "garden"},
            "momento": {"es": "invierno", "en": "winter"}, "tono": "calma", "edad": "4-6"}
    s = historia.extraer_elementos(h, llm_historia_falso(resp), "falso")
    assert s["language"] == "es" and s["json_ok"]
    assert [u["es"] for u in s["unsupported"]] == ["zorro"]          # inventado: marcado
    assert s["prompt_elements"]["personajes"] == ["rabbit"]          # y fuera del prompt
    assert s["prompt_elements"]["lugar"] == "garden"
    assert s["suggested"] == {"P3": "4-6", "P4": "calma"}
    assert len(s["text_sha256"]) == 64 and "text" not in s           # no guarda la historia


def test_extraccion_robusta_y_guardrails():
    s = historia.extraer_elementos("A cat sat on the mat.", lambda m: "no sé", "falso")
    assert not s["json_ok"] and s["elements"]["personajes"] == []
    malo = {"personajes": [{"es": "gato", "en": "cat"}], "objetos": [{"es": "pistola", "en": "gun"}],
            "tono": "terror", "edad": "99"}
    s = historia.extraer_elementos("A cat found a toy.", llm_historia_falso(malo), "falso")
    assert [b["en"] for b in s["blocked"]] == ["gun"] and s["prompt_elements"]["objetos"] == []
    assert s["suggested"] == {"P3": None, "P4": None}
    with pytest.raises(historia.HistoriaBloqueada):
        historia.extraer_elementos("un conejo con un cuchillo", llm_historia_falso(malo))


def test_evaluacion_contra_anotacion():
    ext = {"personajes": [{"es": "perro", "en": "dog"}, {"es": "gato", "en": "cat"}],
           "objetos": [{"es": "pelota", "en": "ball"}]}
    c = historia.evaluar_extraccion(ext, {"personajes": "dogs; bird", "objetos": "ball"}, "en")
    assert c == {"vp": 2, "fp": 1, "fn": 1}
    m = historia.precision_exhaustividad(c)
    assert m["precision"] == pytest.approx(2 / 3) and m["exhaustividad"] == pytest.approx(2 / 3)
    c = historia.evaluar_extraccion(ext, {"personajes": "Perros;gato", "objetos": ""}, "es")
    assert c == {"vp": 2, "fp": 1, "fn": 0}


# ------------------------------------------------------------ explicador
def sesion_ejemplo():
    plan = Planificador(semilla=5)
    r1 = ronda_con_decisiones(plan, 1, "P1", [("accepted", []), ("rejected", ["colores"]),
                                              ("rejected", []), ("accepted", []), ("rejected", ["estilo"])])
    r1["variations"][1]["comment"] = "muy apagado"
    r1["variations"][0]["typography"] = {"user_edit": {"fuente": "Andika"}}
    plan.actualizar(r1)
    r2 = ronda_con_decisiones(plan, 2, "P2", [("rejected", []), ("accepted", []), ("rejected", []),
                                              ("rejected", ["colores"]), ("accepted", [])])
    return {"session_id": "t", "title": "El conejo jardinero",
            "story": {"prompt_elements": {"personajes": ["rabbit"], "objetos": ["flower"], "lugar": "garden"}},
            "rounds": [r1, r2]}


def test_plantilla_pasa_el_validador():
    s = sesion_ejemplo()
    texto = explicador.resumen_plantilla(s)
    v = explicador.validar(texto, s)
    assert v.ok, v.errores
    assert "R1-V2" in texto and "muy apagado" in texto and "Andika" in texto and "rabbit" in texto
    assert "Para la ronda 2" in texto
    assert '"accepted"' not in explicador.explicar(s, None)["user_text"]


def test_validador_detecta_errores():
    s = sesion_ejemplo()
    bueno = explicador.resumen_plantilla(s)
    invertido = bueno.replace("Aceptadas: R1-V1", "Aceptadas: R1-V2").replace("R1-V2 (lápices", "R1-V1 (lápices")
    assert not explicador.validar(invertido, s).ok
    sin_json = bueno.rsplit("\n", 1)[0]
    assert any("JSON" in e for e in explicador.validar(sin_json, s).errores)
    inventado = bueno.replace("Preferencias:", "También R4-V1 te gustó.\nPreferencias:")
    assert any("no existen" in e for e in explicador.validar(inventado, s).errores)
    pref_falsa = bueno.replace("Preferencias: ", "Preferencias: plastilina 3D, ")
    assert any("plastilina 3D" in e for e in explicador.validar(pref_falsa, s).errores)


def test_explicar_reintenta_y_usa_plantilla():
    s = sesion_ejemplo()
    bueno = explicador.resumen_plantilla(s)
    llamadas = []

    def llm_que_aprende(mensajes):
        llamadas.append(mensajes)
        return "Aceptaste todo." if len(llamadas) == 1 else bueno

    r = explicador.explicar(s, llm_que_aprende, "falso")
    assert r["validated"] and r["attempts"] == 2 and not r["template"]
    assert "no coincide con el registro" in llamadas[1][-1]["content"]   # se le pasa el error

    r = explicador.explicar(s, lambda m: "Todo bien.", "falso")
    assert r["template"] and r["validated"] and r["attempts"] == config.MAX_REINTENTOS_RESUMEN + 1
    assert len(r["errors"]) == config.MAX_REINTENTOS_RESUMEN + 1


def test_hechos_no_incluyen_imagenes_ni_prompts():
    s = sesion_ejemplo()
    s["rounds"][0]["variations"][0]["image_path"] = "/x.png"
    h = json.dumps(explicador.hechos(s), ensure_ascii=False)
    assert "/x.png" not in h and "prompt" not in h
    assert "acuarela" in h and "R2-V5" in h


def test_sesion_simulada_tiene_formato_del_registro():
    s = simular_sesion(UsuarioSimulado(np.random.default_rng(4)), "thompson", semilla=4)
    assert len(s["rounds"]) == 3 and all(len(r["variations"]) == 5 for r in s["rounds"])
    assert explicador.validar(explicador.resumen_plantilla(s), s).ok
