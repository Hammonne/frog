"""Pruebas del agente de historia (sin GPU: el LLM se reemplaza por un generador falso)."""
import json

import pytest

from portadas.agentes.historia import (HistoriaInvalida, aparece_en_texto, escena_ingles,
                                       extraer_elementos, verificar)

HISTORIA = "Un conejo que ama las flores vive en un jardin y juega con sus amigos al atardecer."
BUENA = {"personajes_es": ["conejo"], "personajes": ["rabbit"], "objetos_es": ["flores"],
         "objetos": ["flowers"], "lugar_es": "jardin", "lugar": "garden", "momento": "sunset",
         "tono": "alegre", "edad": "4-6"}


def llm_fijo(*respuestas):
    cola = list(respuestas)
    llamadas = []

    def generar(sistema, mensaje):
        llamadas.append(mensaje)
        return cola.pop(0) if len(cola) > 1 else cola[0]
    generar.llamadas = llamadas
    return generar


def test_extrae_y_verifica():
    e = extraer_elementos(HISTORIA, llm_fijo(json.dumps(BUENA)))
    assert e["personajes"] == ["rabbit"] and e["objetos"] == ["flowers"] and e["lugar"] == "garden"
    assert e["no_verificados"] == [] and e["origen"] == "llm" and e["intentos"] == 1
    assert escena_ingles(e) == "a rabbit with flowers in a garden at sunset"


def test_marca_lo_que_la_historia_no_dice():
    inventado = {**BUENA, "personajes_es": ["conejo", "oso"], "personajes": ["rabbit", "bear"]}
    e = extraer_elementos(HISTORIA, llm_fijo(json.dumps(inventado)))
    assert e["no_verificados"] == ["oso"]
    assert escena_ingles(e, quitar=["bear"]) == "a rabbit with flowers in a garden at sunset"


def test_tolera_texto_alrededor_del_json():
    e = extraer_elementos(HISTORIA, llm_fijo("Claro:\n```json\n" + json.dumps(BUENA) + "\n```"))
    assert e["personajes"] == ["rabbit"]


def test_reintenta_si_el_json_es_invalido():
    llm = llm_fijo("no se", json.dumps(BUENA))
    e = extraer_elementos(HISTORIA, llm)
    assert e["intentos"] == 2 and e["origen"] == "llm"
    assert "invalid" in llm.llamadas[1]       # el segundo pedido menciona el error


def test_respaldo_si_nunca_hay_json_valido():
    e = extraer_elementos(HISTORIA, llm_fijo("sin json"), reintentos=2)
    assert e["origen"] == "respaldo" and e["personajes"] == [] and e["intentos"] == 3


def test_listas_desiguales_se_rechazan():
    mal = {**BUENA, "personajes": ["rabbit", "bear"]}
    assert extraer_elementos(HISTORIA, llm_fijo(json.dumps(mal)), reintentos=0)["origen"] == "respaldo"


def test_valores_fuera_de_catalogo_usan_los_por_defecto():
    raro = {**BUENA, "tono": "terrorifico", "edad": "40"}
    e = extraer_elementos(HISTORIA, llm_fijo(json.dumps(raro)))
    assert e["tono"] == "alegre" and e["edad"] == "4-6"


def test_momento_en_espanol_se_traduce_y_el_desconocido_se_descarta():
    assert extraer_elementos(HISTORIA, llm_fijo(json.dumps({**BUENA, "momento": "amanecer"})))["momento"] == "sunrise"
    assert extraer_elementos(HISTORIA, llm_fijo(json.dumps({**BUENA, "momento": "Atardecer"})))["momento"] == "sunset"
    assert extraer_elementos(HISTORIA, llm_fijo(json.dumps({**BUENA, "momento": "a veces"})))["momento"] == ""


def test_lugar_largo_se_reduce_al_sustantivo():
    def lugar(v):
        return extraer_elementos(HISTORIA, llm_fijo(json.dumps({**BUENA, "lugar": v})))["lugar"]
    assert lugar("bottom of the sea") == "sea"
    assert lugar("edge of forest") == "forest"
    assert lugar("garden") == "garden" and lugar("") == ""


def test_historia_bloqueada_vacia_o_larga():
    with pytest.raises(HistoriaInvalida):
        extraer_elementos("Un hombre con una pistola mata al lobo", llm_fijo(json.dumps(BUENA)))
    with pytest.raises(HistoriaInvalida):
        extraer_elementos("   ", llm_fijo(json.dumps(BUENA)))
    with pytest.raises(HistoriaInvalida):
        extraer_elementos("flor " * 501, llm_fijo(json.dumps(BUENA)))


def test_elementos_bloqueados_en_la_salida_van_a_respaldo():
    malo = {**BUENA, "objetos_es": ["pistola"], "objetos": ["pistol"]}
    assert extraer_elementos(HISTORIA, llm_fijo(json.dumps(malo)))["origen"] == "respaldo"


def test_verificador_plurales_diminutivos_y_sinonimos():
    assert aparece_en_texto("conejo", "Los conejitos saltan")
    assert aparece_en_texto("conejo", "La liebre corre")
    assert aparece_en_texto("flores", "Una flor roja")
    assert aparece_en_texto("pájaro", "Un pajarito canta")
    assert not aparece_en_texto("oso", "Un conejo y una zorra")
    assert verificar({"personajes": ["conejo"], "objetos": ["luna"]}, "El conejo duerme") == ["luna"]
