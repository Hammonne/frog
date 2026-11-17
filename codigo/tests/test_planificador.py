"""Pruebas del planificador de Thompson y del control de rondas (sin GPU)."""
import pytest

from experimentos.e2_simulacion import simular_usuario
from portadas import config
from portadas.planificador import MAX_RONDAS, Planificador, Sesion, ejes_de_motivos


def ronda_con(sesion, plan, decisiones, motivos=None):
    motivos = motivos or {}
    vs = [{"id": f"R{plan['round']}-V{i}", "params": cfg, "decision": d, "reasons": motivos.get(i, [])}
          for i, (cfg, d) in enumerate(zip(plan["configs"], decisiones), start=1)]
    return {"round": plan["round"], "axis": plan["axis"], "variations": vs}


def test_motivos_a_ejes():
    assert ejes_de_motivos(["colores", "ambiente", "otro", "colores"]) == ["P2", "P4"]


def test_ronda_1_usa_los_cinco_valores_del_eje():
    s = Sesion(dict(config.POR_DEFECTO))
    plan = s.configs_ronda("P1")
    assert [c["P1"] for c in plan["configs"]] == list(config.ESTILOS)
    assert all(c["P2"] == "pastel" for c in plan["configs"])


def test_aceptar_sube_alfa_y_rechazar_sube_beta_solo_en_los_motivos():
    s = Sesion(dict(config.POR_DEFECTO))
    plan = s.configs_ronda("P1")
    s.cerrar_ronda(ronda_con(s, plan, ["accepted", "rejected", "rejected", "accepted", "accepted"],
                             {2: ["colores"]}))
    post = s.planificador.post
    e = list(config.ESTILOS)
    assert post["P1"][e[0]] == [2.0, 1.0] and post["P1"][e[3]] == [2.0, 1.0]   # aceptadas: alfa +1 en el eje
    assert post["P2"]["pastel"] == [1.0, 1.0]       # la paleta no varió: ni aceptar ni rechazar la toca
    assert post["P1"][e[1]] == [1.0, 2.0]           # rechazo por "colores" (no varió): se redirige al eje
    assert post["P1"][e[2]] == [1.0, 2.0]           # rechazo sin motivo: penaliza el eje


def test_bloqueadas_no_cuentan():
    s = Sesion(dict(config.POR_DEFECTO))
    plan = s.configs_ronda("P1")
    s.cerrar_ronda(ronda_con(s, plan, ["blocked"] * 5))
    assert all(a == b == 1.0 for vals in s.planificador.post.values() for a, b in vals.values())


def test_ejes_no_se_repiten_y_maximo_tres_rondas():
    s = Sesion(dict(config.POR_DEFECTO))
    for eje in ("P1", "P2", "P4"):
        plan = s.configs_ronda(eje)
        s.cerrar_ronda(ronda_con(s, plan, ["accepted"] * 5))
    assert s.terminada() and len(s.rondas) == MAX_RONDAS
    with pytest.raises(ValueError):
        s.configs_ronda("P3")
    s2 = Sesion(dict(config.POR_DEFECTO))
    s2.cerrar_ronda(ronda_con(s2, s2.configs_ronda("P1"), ["accepted"] * 5))
    with pytest.raises(ValueError):
        s2.configs_ronda("P1")


def test_ronda_2_explota_lo_aceptado():
    s = Sesion(dict(config.POR_DEFECTO), semilla=1)
    plan = s.configs_ronda("P1")
    s.cerrar_ronda(ronda_con(s, plan, ["accepted"] * 5))
    s.planificador.post["P2"]["calida"][0] = 200.0     # evidencia fuerte: la elección es casi segura
    plan2 = s.configs_ronda("P4")
    assert sum(c["P2"] == "calida" for c in plan2["configs"]) == 5
    assert [c["P4"] for c in plan2["configs"]] == list(config.AMBIENTES)
    assert "P4" not in plan2["free"] and len(plan2["sampled"]) == 5


def test_fijados_no_se_muestrean():
    s = Sesion(dict(config.POR_DEFECTO, P3="7-9"), fijados=["P3"])
    s.cerrar_ronda(ronda_con(s, s.configs_ronda("P1"), ["rejected"] * 5))
    plan = s.configs_ronda("P2")
    assert all(c["P3"] == "7-9" for c in plan["configs"]) and "P3" not in plan["free"]


def test_zona_del_titulo_es_fija():
    s = Sesion(dict(config.POR_DEFECTO, P6="inferior"))
    assert "P6" not in s.ejes_disponibles()
    s.cerrar_ronda(ronda_con(s, s.configs_ronda("P1"), ["accepted"] * 5))
    plan = s.configs_ronda("P2")
    assert "P6" not in plan["free"] and all(c["P6"] == "inferior" for c in plan["configs"])
    assert ejes_de_motivos(["espacio del título"]) == []


def test_motor_b_no_varia_p5():
    s = Sesion(dict(config.POR_DEFECTO), motor="B")
    assert "P5" not in s.ejes_disponibles()
    s.cerrar_ronda(ronda_con(s, s.configs_ronda("P1"), ["accepted"] * 5))
    assert all(c["P5"] == "media" for c in s.configs_ronda("P2")["configs"])


def test_bloque_del_planificador_queda_en_la_ronda():
    s = Sesion(dict(config.POR_DEFECTO))
    r = ronda_con(s, s.configs_ronda("P1"), ["accepted"] * 5)
    s.cerrar_ronda(r)
    assert r["planner"]["method"].startswith("eje completo")
    assert "posterior_mean" in r["planner"]


def test_reproducible_con_semilla():
    a = Planificador(5).proponer("P1", dict(config.POR_DEFECTO))["configs"]
    b = Planificador(5).proponer("P1", dict(config.POR_DEFECTO))["configs"]
    assert a == b


def test_thompson_supera_al_azar_en_simulacion():
    def media(politica, r):
        t = [simular_usuario(politica, 2026 + u) for u in range(300)]
        return sum(x[r] for x in t) / len(t)
    assert media("thompson", 2) > media("aleatorio", 2)
    assert media("thompson", 2) > media("thompson", 0)


def test_favoritos_ignora_constantes_empates_y_parametros_sin_variar():
    s = Sesion(dict(config.POR_DEFECTO))
    plan = s.configs_ronda("P1")
    s.cerrar_ronda(ronda_con(s, plan, ["accepted", "accepted", "rejected", "rejected", "rejected"]))
    fav = s.planificador.favoritos()
    assert "P3" not in fav and "P4" not in fav and "P6" not in fav     # nunca cambiaron: no son preferencias
    assert "P1" not in fav                                              # acuarela y lapices empatan
    # Con un ganador único y varios valores probados sí hay preferencia.
    s.planificador.post["P1"]["acuarela"][0] += 5
    assert s.planificador.favoritos()["P1"] == "acuarela"


def test_favoritos_no_incluye_a_p6_ni_a_p5_en_motor_b():
    s = Sesion(dict(config.POR_DEFECTO), motor="B")
    s.cerrar_ronda(ronda_con(s, s.configs_ronda("P1"), ["accepted"] * 5))
    assert "P5" not in s.planificador.favoritos() and "P6" not in s.planificador.favoritos()


def test_lo_que_no_vario_no_acumula_evidencia():
    """Aceptar 5 propuestas que comparten paleta no debe inflar esa paleta (fallo visto en una sesión real)."""
    s = Sesion(dict(config.POR_DEFECTO))
    s.cerrar_ronda(ronda_con(s, s.configs_ronda("P1"), ["accepted"] * 5))
    post = s.planificador.post
    assert post["P2"]["pastel"] == [1.0, 1.0] and post["P3"][config.POR_DEFECTO["P3"]] == [1.0, 1.0]
    assert all(post["P1"][v] == [2.0, 1.0] for v in config.ESTILOS)
    assert "P2" not in s.planificador.vistos or not s.planificador.vistos["P2"]


def test_variaron_son_los_parametros_con_mas_de_un_valor():
    s = Sesion(dict(config.POR_DEFECTO), semilla=3)
    plan = s.configs_ronda("P1")
    r = ronda_con(s, plan, ["accepted"] * 5)
    v = Planificador.variaron(r)
    assert "P1" in v and "P6" not in v and "P2" not in v
