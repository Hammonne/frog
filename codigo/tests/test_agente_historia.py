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


# ---- historias en inglés y evaluación contra anotaciones manuales
def test_detectar_idioma():
    from portadas.agentes.historia import detectar_idioma
    assert detectar_idioma("Había una vez un gato que vivía en la casa") == "es"
    assert detectar_idioma("Once upon a time there was a cat in the house") == "en"


def test_un_texto_en_ingles_se_verifica_con_los_elementos_en_ingles():
    import json
    respuesta = json.dumps({"personajes_es": ["conejo", "zorro"], "personajes": ["rabbit", "fox"],
                            "objetos_es": ["pelota"], "objetos": ["ball"], "lugar_es": "jardin",
                            "lugar": "garden", "momento": "", "tono": "alegre", "edad": "4-6"})
    e = extraer_elementos("The rabbits played with a ball in the garden.", lambda s, m: respuesta)
    assert e["idioma"] == "en" and e["no_verificados"] == ["fox"]


def test_evaluacion_contra_anotacion():
    from portadas.agentes.historia import evaluar_extraccion, precision_exhaustividad
    e = {"personajes": ["dog", "cat"], "objetos": ["ball"],
         "es": {"personajes": ["perro", "gato"], "objetos": ["pelota"], "lugar": ""}}
    c = evaluar_extraccion(e, {"personajes": "dogs; bird", "objetos": "ball"}, "en")
    assert c == {"vp": 2, "fp": 1, "fn": 1}
    m = precision_exhaustividad(c)
    assert abs(m["precision"] - 2 / 3) < 1e-9 and abs(m["exhaustividad"] - 2 / 3) < 1e-9
    assert evaluar_extraccion(e, {"personajes": "Perros;gato", "objetos": ""}, "es") == {"vp": 2, "fp": 1, "fn": 0}


def test_las_sesiones_simuladas_de_e2_tienen_la_forma_que_espera_el_resumen():
    from experimentos.e2_simulacion import jugar
    from portadas.agentes.resumen import resumir
    tasas, sesion = jugar("thompson", 7)
    assert len(tasas) == 3 and len(sesion["rounds"]) == 3
    r = resumir(sesion, lambda sistema, mensaje: "")        # un LLM que no responde: cae a la plantilla
    assert r["origen"] == "plantilla" and "Ronda 1" in r["texto"]


# ------------------------------------------------------------------ limpieza y comparación flexible
def test_la_salida_quita_nombres_lugares_y_repetidos():
    from portadas.agentes.historia import normalizar_salida
    s = normalizar_salida({"personajes_es": ["niña llamada kat", "perro"], "personajes": ["girl named kat", "dog"],
                           "objetos_es": ["cielo", "perro", "pelota", "pelota"],
                           "objetos": ["sky", "dog", "ball", "ball"], "lugar": "park", "tono": "alegre", "edad": "4-6"})
    assert s["personajes"] == ["girl", "dog"] and s["es"]["personajes"] == ["niña", "perro"]
    assert s["objetos"] == ["ball"] and s["es"]["objetos"] == ["pelota"]       # sin lugar, sin personaje, sin repetido


def test_comparacion_flexible_acepta_que_una_expresion_contenga_a_la_otra():
    from portadas.agentes.historia import comparar_conjuntos, comparar_flexible
    pred, anot = ["dog max", "big red ball", "sky"], ["dog", "ball", "kite"]
    assert comparar_conjuntos(pred, anot) == {"vp": 0, "fp": 3, "fn": 3}
    assert comparar_flexible(pred, anot) == {"vp": 2, "fp": 1, "fn": 1}
    assert comparar_flexible(["ball", "ball bat"], ["ball"]) == {"vp": 1, "fp": 1, "fn": 0}   # un anotado, un predicho
