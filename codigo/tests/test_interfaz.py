"""Pruebas del aspecto y de la construcción de la interfaz (sin GPU; la interfaz se recorre
con un navegador aparte, ver README)."""
import pytest

from app import estilo as E
from portadas import config


def test_cada_valor_de_cada_parametro_tiene_etiqueta_para_personas():
    """Si alguien agrega un valor en config.py y no su etiqueta, la interfaz mostraría un código."""
    for eje, valores in config.PARAMETROS.items():
        for v in valores:
            assert v in E.ETIQUETAS[eje], f"falta la etiqueta de {eje}={v!r} en app/estilo.py"
    assert set(E.NOMBRES) == set(config.PARAMETROS) == set(E.CORTO)


def test_opciones_devuelven_texto_y_valor_interno():
    assert ("Lápices de colores", "lapices") in E.opciones("P1", config.ESTILOS)
    assert [v for _, v in E.opciones("P5", config.FIDELIDAD)] == list(config.FIDELIDAD)


def test_barra_de_pasos_marca_hechos_actual_y_futuros():
    h = E.barra_pasos(3)
    assert h.count('class="f-paso hecho"') == 2 and h.count('class="f-paso actual"') == 1
    assert h.count('class="f-paso futuro"') == 2 and "Parámetros" in h and "<b>03</b>" in h
    assert E.barra_pasos(0) == ""                      # la pantalla de inicio no muestra pasos


def test_contador_y_avisos():
    assert "Has decidido 3 de 5" in E.contador(3, 5)
    assert "Listo" in E.contador(5, 5)
    assert "bloqueadas por seguridad" in E.contador(0, 0)      # las 5 portadas bloqueadas: se puede cerrar
    assert 'role="alert"' in E.tarjeta("error", "t", "x") and 'role="status"' in E.tarjeta("ok", "t", "x")


def test_el_html_escapa_texto_del_usuario():
    assert "<script>" not in E.pie_tarjeta("<script>", "P1", "acuarela")
    assert "<b>x</b>" not in E.resumen("<b>x</b>", "llm", "<i>m</i>", 1)


def test_el_resumen_mostrado_no_lleva_codigos_de_parametro():
    t = E._para_personas("Ronda 1 (eje: P1 (Estilo)) - Aceptadas: R1-V1 (acuarela).")
    assert "P1" not in t and "eje: Estilo" in t and "R1-V1" in t     # los IDs de propuesta se conservan


def test_insignia_distingue_resumen_verificado_de_plantilla():
    assert "verificado" in E.insignia("llm", "qwen2.5-7b", 2)
    assert "no pasó la verificación" in E.insignia("plantilla", "", 3)


def test_la_mascota_se_incluye_en_el_html():
    assert E.rana(50).startswith("<img") and "data:image/svg+xml;base64," in E.rana(50)


def test_la_interfaz_se_construye_con_sus_cinco_tarjetas_y_sus_pantallas():
    pytest.importorskip("gradio")
    from app.interfaz import N, PAGINAS, construir_interfaz
    demo = construir_interfaz()
    C = demo.frog_componentes
    assert N == 5 and all(f"op{i}" in C for i in range(5)) and f"op{N}" not in C
    assert all(f"p_{p}" in C for p in PAGINAS)
    assert len(C) == len(set(C))


@pytest.mark.parametrize("pagina", ["inicio", "entrada", "propuestas", "final"])
def test_la_interfaz_puede_arrancar_en_cualquier_pantalla(pagina):
    pytest.importorskip("gradio")
    from app.interfaz import construir_interfaz
    C = construir_interfaz(pagina).frog_componentes
    assert C[f"p_{pagina}"].visible is True
    assert sum(1 for k, c in C.items() if k.startswith("p_") and c.visible) == 1


# ---- dirección de arte: reglas que la persona pidió y que no deben volver a romperse
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\uFE0F\u2705\u2714\u2716]")


@pytest.mark.parametrize("fuente", ["estilo.py", "interfaz.py"])
def test_el_codigo_de_la_interfaz_no_usa_emojis_ni_marcas_tipograficas(fuente):
    texto = (APP / fuente).read_text(encoding="utf-8")
    assert not EMOJI.search(texto), f"{fuente} contiene un emoji o símbolo de marca (✓, ✗, ✦…)"


def test_ninguna_pantalla_genera_emojis_ni_iconos_decorativos():
    html = "".join([E.inicio_texto(), E.inicio_imagen(), E.como_funciona(), E.titulo("t", "s"), E.ficha("Lugar", "", 3),
                    E.etiqueta_campo("Título"), E.carga("t", "d", "a"), E.tarjeta("error", "t", "x"),
                    E.tarjeta("ok", "t", "x"), E.pie_tarjeta("R1-V1", "P1", "acuarela"), E.contador(2, 5),
                    E.escena("night"), E.resumen("texto", "llm", "m", 1), E.barra_pasos(2), E.logo()])
    assert not EMOJI.search(html)


def test_no_hay_vegetacion_decorativa_en_el_inicio():
    """Pedido expreso: sin el pastito al pie de la pantalla inicial (ni 'hierbas' en ningún lado)."""
    from app import recursos as R
    for texto in (E.inicio_texto(), E.inicio_imagen(), E.como_funciona(), E.CSS):
        assert R.uri("fondo_bosque") not in texto and R.uri("deco_hierbas") not in texto
    for fuente in ("estilo.py", "interfaz.py"):
        codigo = (APP / fuente).read_text(encoding="utf-8")
        assert "fondo_bosque" not in codigo and "deco_hierbas" not in codigo and "bosque()" not in codigo


def test_los_parametros_ya_no_llevan_iconos_decorativos():
    for fuente in ("estilo.py", "interfaz.py"):
        codigo = (APP / fuente).read_text(encoding="utf-8")
        assert not re.search(r'"ico_(estilo|colores|ilustracion|composicion|tipografia|ambiente)"', codigo)


def test_los_titulares_usan_la_tipografia_display_y_el_texto_no():
    assert 'class="f-display"' in E.titulo("Tu cuento") and "f-display" not in E.etiqueta_campo("Título", "ayuda")
    assert "Lilita One" in E.CSS and "font/ttf;base64" in E.CSS               # incrustada: no depende de internet
    assert "f-parrafo" in E.inicio_texto() and "f-display f-parrafo" not in E.inicio_texto()


def test_la_paleta_de_marca_es_la_pedida():
    assert (E.VERDE, E.AMARILLO, E.CREMA) == ("#347A37", "#FFC51B", "#F8F1E4") and E.CLARO == "#A5DB91"


def test_la_licencia_de_la_fuente_viaja_con_la_aplicacion():
    assert (APP / "assets" / "fuentes" / "OFL-LilitaOne.txt").exists()
    assert "SIL OPEN FONT LICENSE" in (APP / "assets" / "fuentes" / "OFL-LilitaOne.txt").read_text(encoding="utf-8").upper()


def test_la_barra_de_accion_de_las_propuestas_va_fija_a_la_ventana():
    """Con 'sticky' la barra quedaba fuera de la ventana (medido en el navegador): debe ir fija."""
    regla = E.CSS[E.CSS.index(".f-accion {"):]
    regla = regla[:regla.index("}")]
    assert "position: fixed" in regla and "sticky" not in regla and "bottom: 0" in regla


def test_el_editor_de_titulo_no_usa_menus_desplegables():
    """Las tarjetas van giradas (transform): los menús y selectores flotantes de Gradio quedaban fuera de
    lugar y 'no abrían' (visto en Colab). El editor de cada tarjeta usa botones."""
    gr = pytest.importorskip("gradio")
    from app.interfaz import N, construir_interfaz
    C = construir_interfaz().frog_componentes
    for i in range(N):
        assert isinstance(C[f"edf{i}"], gr.Radio) and isinstance(C[f"edk{i}"], gr.Radio)
