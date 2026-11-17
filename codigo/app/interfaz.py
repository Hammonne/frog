"""Interfaz web (Gradio) de FROG, en pasos. Toda la lógica está en `app/flujo.py`; el aspecto en
`app/estilo.py`; aquí solo se conectan pantallas y botones.

Pantallas: Inicio -> 1 Entrada -> 2 Elementos -> 3 Parámetros -> (carga) -> 4 Propuestas
           -> Siguiente ronda (hasta 3) -> 5 Resumen. Cada pantalla es una columna que se muestra
u oculta; las esperas largas (cargar modelos, generar, resumir) son generadores que van
cambiando el mensaje de la pantalla de carga.

Desde Colab (GPU), en una celda:
    from app.interfaz import lanzar
    lanzar()        # imprime un enlace https://xxxx.gradio.live
"""
from __future__ import annotations

import html
import inspect
from functools import partial
from typing import Dict, List

from portadas import config
from portadas.agentes.historia import MOMENTOS
from portadas.agentes.tipografia import titular_con_agente
from portadas.titulo import CATALOGO

from . import estilo as E
from . import flujo

PAGINAS = ["inicio", "entrada", "elementos", "parametros", "carga", "propuestas", "siguiente", "final"]
PASO_DE = {"inicio": 0, "entrada": 1, "elementos": 2, "parametros": 3, "carga": None,
           "propuestas": 4, "siguiente": 4, "final": 5}
N = 5          # portadas por ronda

MOTIVOS_VISTOS = [("Prefiero otro estilo", "estilo"), ("No me gustan los colores", "colores"),
                  ("No es apta para la edad", "no apto para la edad"),
                  ("No representa el ambiente", "ambiente"), ("Se aleja de mi boceto", "se aleja del boceto")]
MOMENTOS_VISTOS = [("— sin momento —", ""), ("Amanecer", "sunrise"), ("Mañana", "morning"),
                   ("Mediodía", "noon"), ("Tarde", "afternoon"), ("Atardecer", "sunset"),
                   ("Anochecer", "evening"), ("Noche", "night")]
MOMENTO_TEXTO = {v: t for t, v in MOMENTOS_VISTOS if v}
MOTORES_VISTOS = [("Fiel a mi boceto", "A"), ("Más libre y rápido", "B")]
LLM_VISTOS = [("Qwen 2.5 (recomendado)", "qwen2.5-7b"), ("Phi 3.5 (más liviano)", "phi-3.5-mini")]
EJES = ("P1", "P2", "P3", "P4", "P5")
FUENTES_VISTAS = [(flujo.NOMBRE_FUENTE[n], n) for n in CATALOGO]


class _Modelos:
    """Carga perezosa y una sola vez: los modelos tardan en cargarse y ocupan la GPU."""

    def __init__(self):
        self.motores: Dict[str, object] = {}
        self.revisor = None
        self._llm = None
        self._llm_nombre = None

    def motor(self, nombre: str):
        if nombre not in self.motores:
            if nombre == "A":
                from portadas.motores.motor_a import MotorA
                self.motores[nombre] = MotorA()
            else:
                from portadas.motores.motor_b import MotorB
                self.motores[nombre] = MotorB()
        return self.motores[nombre]

    def revisor_salida(self):
        if self.revisor is None:
            from portadas.guardrails.salida import RevisorSalida
            from portadas.metricas.clip_metricas import EvaluadorCLIP
            self.revisor = RevisorSalida(EvaluadorCLIP())
        return self.revisor

    def llm_cargado(self):
        """El LLM que ya está en la GPU (el del paso de la historia), o None; el agente tipográfico
        lo usa si existe y, si no, el título sale con la disposición por defecto."""
        return self._llm

    def llm(self, nombre: str):
        """Un solo LLM a la vez: al cambiar de modelo se libera la GPU del anterior."""
        if self._llm_nombre != nombre:
            if self._llm is not None:
                self._llm.liberar()
            from portadas.agentes.llm import LLMLocal
            self._llm, self._llm_nombre = LLMLocal(nombre), nombre
        return self._llm


MODELOS = _Modelos()


def _log(texto: str) -> None:
    """Mensajes en la celda de Colab (la interfaz no muestra los errores internos)."""
    print(f"[frog] {texto}", flush=True)


def aviso_historia(elem: Dict) -> str:
    """Tarjetas con lo que entendió el asistente y lo que no pudo comprobar."""
    if elem.get("origen") == "respaldo":
        return E.tarjeta("error", "No pudimos analizar tu historia",
                         "Escribe la escena a mano en el campo de abajo (en inglés, por ejemplo: "
                         "<i>a rabbit in a garden</i>) y continúa.")
    es = elem["es"]
    tarjetas = [E.tarjeta("ok", "Esto entendimos de tu historia",
                          f"Personajes: <b>{html.escape(', '.join(es['personajes']) or '—')}</b> · objetos: "
                          f"<b>{html.escape(', '.join(es['objetos']) or '—')}</b> · lugar: "
                          f"<b>{html.escape(es['lugar'] or '—')}</b>.")]
    if elem["no_verificados"]:
        tarjetas.append(E.tarjeta("aviso", "No lo encontramos en tu historia",
                                  f"{html.escape(', '.join(elem['no_verificados']))}. Bórralo de los campos "
                                  "si no debe aparecer en la portada."))
    return "".join(tarjetas)


def _elementos(personajes: str, objetos: str, lugar: str, momento: str, escena: str) -> Dict:
    """Elementos que se guardan en el registro: lo que la persona dejó en los campos finales."""
    datos = {"personajes": flujo.partir(personajes), "objetos": flujo.partir(objetos),
             "lugar": (lugar or "").strip().lower(), "momento": momento or ""}
    datos = {k: v for k, v in datos.items() if v}
    return datos or {"escena": escena}


def _opciones_estilo() -> Dict:
    """Tema, CSS y JS: en Gradio >= 6 van en launch(); en versiones anteriores, en Blocks()."""
    return {"theme": E.tema(), "css": E.CSS, "js": E.JS_CLARO}


def _galeria_kw() -> Dict:
    """Galería que crece con su contenido (los parámetros opcionales dependen de la versión)."""
    import gradio as gr
    posibles = inspect.signature(gr.Gallery.__init__).parameters
    kw = {"columns": 4, "object_fit": "contain", "height": None}
    return {k: v for k, v in kw.items() if k in posibles}


def _estilo_en_blocks() -> bool:
    import gradio as gr
    return "css" in inspect.signature(gr.Blocks.__init__).parameters


# ------------------------------------------------------------------------- interfaz
def construir_interfaz(pagina_inicial: str = "inicio"):
    import gradio as gr

    C: Dict[str, object] = {}      # todas las salidas posibles, por nombre
    vis = lambda p: p == pagina_inicial
    kw = _opciones_estilo() if _estilo_en_blocks() else {}

    with gr.Blocks(title="FROG · portadas para tus cuentos", **kw) as demo:
        C["est"] = gr.State(None)          # app.flujo.Estado de la sesión
        C["elem_st"] = gr.State({})        # elementos que extrajo el agente de historia
        C["ronda_st"] = gr.State(None)     # ronda en pantalla, esperando decisiones
        gr.HTML(E.filtros(), elem_classes="f-filtros")
        with gr.Row(elem_classes="f-cab"):
            gr.HTML(E.logo())
            C["pasos"] = gr.HTML(E.barra_pasos(PASO_DE[pagina_inicial] or 0))

        # ------------------------------------------------------------------ Inicio
        with gr.Column(visible=vis("inicio"), elem_classes="f-pagina") as C["p_inicio"]:
            with gr.Row(equal_height=False):
                with gr.Column(scale=11):
                    gr.HTML(E.inicio_texto())
                    btn_comenzar = gr.Button("Comenzar", variant="primary", elem_classes="f-centrar")
                with gr.Column(scale=9):
                    gr.HTML(E.inicio_imagen())
            gr.HTML(E.como_funciona())

        # ------------------------------------------------------------------ 1 Entrada
        with gr.Column(visible=vis("entrada"), elem_classes="f-pagina") as C["p_entrada"]:
            with gr.Row(equal_height=False):
                with gr.Column(scale=5, elem_classes="f-amarillo f-col-boceto"):
                    gr.HTML(E.etiqueta_campo("Tu boceto"))
                    C["boceto"] = gr.Image(type="pil", label="Boceto de tu portada", show_label=False,
                                           sources=["upload"], height=470, elem_classes="f-lamina f-boceto f-giro1")
                    gr.HTML(E.asoma("frog_hero", 250), elem_classes="f-asoma f-asoma-entrada")
                with gr.Column(scale=7):
                    gr.HTML(E.titulo("Cuéntanos tu cuento"))
                    C["err_entrada"] = gr.HTML(visible=False)
                    gr.HTML(E.etiqueta_campo("Título del libro"))
                    C["titulo_tb"] = gr.Textbox(label="Título del libro", show_label=False,
                                                placeholder="El conejo y las flores")
                    gr.HTML(E.etiqueta_campo("Tu historia", "Hasta 500 palabras, en español"))
                    C["historia"] = gr.Textbox(label="Tu historia", show_label=False, lines=6,
                                               placeholder="Quiénes son los personajes, dónde ocurre, qué pasa…")
                    with gr.Row():
                        motor = gr.Radio(MOTORES_VISTOS, value="A", label="Cómo dibuja", elem_classes="f-tira",
                                         info="Fiel sigue tu trazo; libre lo reinterpreta.")
                        llm_r = gr.Radio(LLM_VISTOS, value="qwen2.5-7b", label="Asistente", elem_classes="f-tira",
                                         info="Lee tu historia y redacta el resumen final.")
                    btn_entrada = gr.Button("Continuar", variant="primary", elem_classes="f-centrar")

        # ------------------------------------------------------------------ 2 Elementos
        with gr.Column(visible=vis("elementos"), elem_classes="f-pagina") as C["p_elementos"]:
            gr.HTML(E.titulo("Lo que encontramos en tu historia", "Corrige lo que haga falta antes de seguir."))
            C["aviso_hist"] = gr.HTML()
            C["err_elem"] = gr.HTML(visible=False)
            with gr.Row(equal_height=False):
                with gr.Column(scale=6):
                    with gr.Row(equal_height=False):
                        with gr.Column(min_width=220, elem_classes="f-ficha"):
                            gr.HTML(E.ficha("Personajes", "en inglés", 1))
                            C["personajes"] = gr.Textbox(label="Personajes", show_label=False)
                        with gr.Column(min_width=220, elem_classes="f-ficha"):
                            gr.HTML(E.ficha("Objetos", "", 2))
                            C["objetos"] = gr.Textbox(label="Objetos", show_label=False)
                    with gr.Row(equal_height=False):
                        with gr.Column(min_width=220, elem_classes="f-ficha"):
                            gr.HTML(E.ficha("Lugar", "", 3))
                            C["lugar"] = gr.Textbox(label="Lugar", show_label=False)
                        with gr.Column(min_width=220, elem_classes="f-ficha"):
                            gr.HTML(E.ficha("Momento del día", "", 4))
                            C["momento"] = gr.Dropdown(MOMENTOS_VISTOS, value="", label="Momento del día",
                                                       show_label=False)
                with gr.Column(scale=5, elem_classes="f-amarillo f-col-escena"):
                    C["escena_img"] = gr.HTML(E.escena(""))
                    gr.HTML(E.etiqueta_campo("Escena que se va a dibujar", "Se arma sola; también puedes escribirla."))
                    C["escena"] = gr.Textbox(label="Escena que se va a dibujar", show_label=False)
                    gr.HTML(E.asoma("frog_analiza", 210), elem_classes="f-asoma f-asoma-elem")
            with gr.Accordion("Agregar una indicación extra (opcional)", open=False):
                instruccion = gr.Textbox(show_label=False, placeholder="Por ejemplo: un zorro leyendo bajo un árbol")
            with gr.Row():
                btn_elem_volver = gr.Button("Volver", variant="secondary")
                btn_elem = gr.Button("Continuar", variant="primary")

        # ------------------------------------------------------------------ 3 Parámetros
        with gr.Column(visible=vis("parametros"), elem_classes="f-pagina") as C["p_parametros"]:
            gr.HTML(E.titulo("Define cómo se ve tu portada",
                             "Los seis ajustes se pueden cambiar. Elige cuál variará entre las cinco propuestas."))
            C["err_param"] = gr.HTML(visible=False)
            with gr.Row(equal_height=False):
                with gr.Column(scale=6):
                    def menu(eje, valores, clave=None):
                        """Menú de un parámetro con su rótulo."""
                        gr.HTML(E.etiqueta_campo(E.NOMBRES[eje]))
                        d = gr.Dropdown(E.opciones(eje, valores), value=config.POR_DEFECTO[eje],
                                        label=E.NOMBRES[eje], show_label=False)
                        if clave:
                            C[clave] = d
                        return d
                    with gr.Row():
                        with gr.Column():
                            p1 = menu("P1", config.ESTILOS)
                        with gr.Column():
                            p2 = menu("P2", config.PALETAS)
                    with gr.Row():
                        with gr.Column():
                            menu("P3", config.EDADES, "p3")
                        with gr.Column():
                            menu("P4", config.AMBIENTES, "p4")
                    with gr.Row():
                        with gr.Column():
                            menu("P5", config.FIDELIDAD, "p5")
                        with gr.Column():
                            p6 = menu("P6", config.ZONAS_TITULO)
                with gr.Column(scale=4, elem_classes="f-verde f-col-eje"):
                    gr.HTML(E.titulo_bloque("¿Qué cambia entre las cinco?",
                                            "Lo demás se mantiene igual para que puedas comparar."))
                    C["eje"] = gr.Radio([(E.NOMBRES[p], p) for p in EJES], value="P1", elem_classes="f-pila",
                                        label="¿Qué cambia entre las 5 propuestas?", show_label=False)
                    gr.HTML(E.asoma("frog_idea", 195), elem_classes="f-asoma f-asoma-param")
            with gr.Row():
                btn_param_volver = gr.Button("Volver", variant="secondary")
                btn_param = gr.Button("Generar propuestas", variant="primary")

        # ------------------------------------------------------------------ Carga
        with gr.Column(visible=vis("carga"), elem_classes="f-pagina") as C["p_carga"]:
            C["carga_html"] = gr.HTML()

        # ------------------------------------------------------------------ 4 Propuestas
        with gr.Column(visible=vis("propuestas"), elem_classes="f-pagina") as C["p_propuestas"]:
            with gr.Row(equal_height=False):
                with gr.Column(scale=7):
                    C["prop_titulo"] = gr.HTML()
                with gr.Column(scale=5):
                    C["prop_nota"] = gr.HTML()
            with gr.Row(equal_height=False):
                for i in range(N):
                    with gr.Column(min_width=200, elem_classes=f"f-lamina f-giro{i + 1}"):
                        C[f"img{i}"] = gr.Image(show_label=False, interactive=False, container=False,
                                                elem_classes="frog-portada")
                        C[f"ph{i}"] = gr.HTML(E.bloqueada(), visible=False)
                        C[f"pie{i}"] = gr.HTML()
                        C[f"op{i}"] = gr.Radio([("Me gusta", "Aceptar"), ("No me gusta", "Rechazar")],
                                               value=None, show_label=False, elem_classes="f-decision")
                        with gr.Accordion("Editar título", open=False, visible=False,
                                          elem_classes="f-editar") as C[f"ed{i}"]:
                            C[f"edf{i}"] = gr.Dropdown(FUENTES_VISTAS, value="Andika", label="Letra", interactive=True)
                            C[f"edt{i}"] = gr.Slider(0.04, 0.10, step=0.005, value=0.06, label="Tamaño")
                            C[f"edc{i}"] = gr.Slider(-0.4, 0.4, step=0.05, value=0.0, label="Curva")
                            C[f"edk{i}"] = gr.ColorPicker(value="#222222", label="Color")
                            C[f"eda{i}"] = gr.Button("Aplicar al título", size="sm", variant="secondary")
                        with gr.Column(visible=False) as C[f"gr{i}"]:
                            C[f"mo{i}"] = gr.CheckboxGroup(MOTIVOS_VISTOS, label="Qué no te convence",
                                                           elem_classes="f-motivos")
                            C[f"co{i}"] = gr.Textbox(label="Comentario", lines=1, placeholder="Comentario (opcional)",
                                                     show_label=False)
            with gr.Column(elem_classes="f-accion"):
                C["contador"] = gr.HTML()
                with gr.Row():
                    todo_si = gr.Button("Me gustan todas", variant="secondary", size="sm")
                    todo_no = gr.Button("Ninguna me convence", variant="secondary", size="sm")
                    C["btn_cerrar"] = gr.Button("Cerrar esta ronda", variant="primary", interactive=False)

        # ------------------------------------------------------------------ Siguiente ronda
        with gr.Column(visible=vis("siguiente"), elem_classes="f-pagina") as C["p_siguiente"]:
            with gr.Row(equal_height=False):
                with gr.Column(scale=6):
                    C["sig_html"] = gr.HTML()
                    C["btn_sig"] = gr.Button("Generar otra ronda", variant="primary", elem_classes="f-centrar")
                    btn_fin = gr.Button("Terminar y ver resumen", variant="secondary", elem_classes="f-centrar")
                with gr.Column(scale=5, elem_classes="f-verde f-col-eje"):
                    gr.HTML(E.titulo_bloque("¿Qué exploramos ahora?",
                                            "El sistema aprendió de lo que aceptaste y rechazaste."))
                    C["eje_sig"] = gr.Radio([], label="¿Qué quieres explorar ahora?", elem_classes="f-pila",
                                            show_label=False)
                    gr.HTML(E.asoma("frog_idea", 195), elem_classes="f-asoma f-asoma-param")

        # ------------------------------------------------------------------ 5 Resumen
        with gr.Column(visible=vis("final"), elem_classes="f-pagina") as C["p_final"]:
            with gr.Row(equal_height=False):
                with gr.Column(scale=8):
                    gr.HTML(E.titulo("Tus portadas elegidas",
                                     "Las propuestas que aceptaste y el resumen de tus decisiones."))
                with gr.Column(scale=2, min_width=180):
                    gr.HTML(E.imagen("frog_resumen", 260, "f-flota"))
            C["galeria"] = gr.Gallery(show_label=False, elem_classes="f-galeria", **_galeria_kw())
            C["fin_resumen"] = gr.HTML()
            C["archivo"] = gr.File(label="Descargar el registro de tu sesión (JSON)", elem_classes="f-archivo")
            btn_nueva = gr.Button("Crear otra portada", variant="primary", elem_classes="f-centrar")

        # ===================================================================== lógica
        nombres = list(C)
        salidas = [C[n] for n in nombres]
        skip = getattr(gr, "skip", gr.update)

        def P(*dicts, **kw):
            """Arma la lista de salidas: lo que no se menciona no cambia."""
            datos: Dict[str, object] = {}
            for d in dicts:
                datos.update(d)
            datos.update(kw)
            desconocidas = set(datos) - set(nombres)
            assert not desconocidas, desconocidas
            return [datos.get(n, skip()) for n in nombres]

        def nav(pagina: str, paso: int = None) -> Dict:
            d = {f"p_{n}": gr.update(visible=(n == pagina)) for n in PAGINAS}
            d["pasos"] = gr.update(value=E.barra_pasos(PASO_DE[pagina] if paso is None else paso))
            return d

        def error(pagina: str, campo: str, titulo: str, texto: str, paso: int = None) -> List:
            return P(nav(pagina, paso), **{campo: gr.update(value=E.tarjeta("error", titulo, texto), visible=True)})

        def cargando(paso: int, titulo: str, detalle: str, aviso: str = "", mascota: str = "frog_generando") -> List:
            return P(nav("carga", paso), carga_html=E.carga(titulo, detalle, aviso, mascota))

        def _generar(estado, ej):
            """Genera la ronda que toca (una vez creada la sesión)."""
            return flujo.proponer_ronda(estado, ej, lambda e, c, n: flujo.generar_real(
                e, c, n, MODELOS.motor, MODELOS.revisor_salida),
                titulador=partial(titular_con_agente, llm=MODELOS.llm_cargado()))

        # ---------------------------------------------------------------- navegación simple
        btn_comenzar.click(lambda: P(nav("entrada")), None, salidas, show_progress="hidden")
        btn_elem_volver.click(lambda: P(nav("entrada")), None, salidas, show_progress="hidden")
        btn_param_volver.click(lambda: P(nav("elementos")), None, salidas, show_progress="hidden")

        # ---------------------------------------------------------------- 1 -> 2
        def _entrada(img, tit, hist, nombre):
            falta = ("Sube el boceto de tu portada." if img is None else
                     "Escribe el título de tu libro." if not (tit or "").strip() else
                     "Escribe tu historia." if not (hist or "").strip() else "")
            if falta:
                yield error("entrada", "err_entrada", "Falta algo", falta)
                return
            primera = MODELOS._llm_nombre != nombre
            yield cargando(1, "Leyendo tu historia", "Estamos buscando a los personajes, los objetos y el lugar.",
                           "La primera vez puede tardar de 1 a 3 minutos mientras se prepara el asistente."
                           if primera else "Esto toma unos segundos.", "frog_analiza")
            try:
                _log(f"cargando {nombre}")
                elem = flujo.analizar_historia(hist, MODELOS.llm(nombre))
            except ValueError as e:                       # historia vacía, muy larga o con contenido no apto
                yield error("entrada", "err_entrada", "No pudimos usar tu historia", html.escape(str(e)))
                return
            except Exception as e:
                _log(f"error del asistente: {e!r}")
                yield error("entrada", "err_entrada", "El asistente no pudo arrancar", html.escape(str(e)))
                return
            esc = flujo.construir_escena(", ".join(elem["personajes"]), ", ".join(elem["objetos"]),
                                         elem["lugar"], elem["momento"])
            yield P(nav("elementos"), elem_st=elem, aviso_hist=aviso_historia(elem),
                    personajes=", ".join(elem["personajes"]), objetos=", ".join(elem["objetos"]),
                    lugar=elem["lugar"], momento=elem["momento"], escena=esc, p3=elem["edad"], p4=elem["tono"],
                    escena_img=E.escena(elem["momento"], MOMENTO_TEXTO.get(elem["momento"], "")),
                    err_entrada=gr.update(visible=False), err_elem=gr.update(visible=False))

        btn_entrada.click(_entrada, [C["boceto"], C["titulo_tb"], C["historia"], llm_r], salidas,
                          show_progress="hidden")

        def _reescena(pe, ob, lu, mo):
            return flujo.construir_escena(pe, ob, lu, mo)

        for campo in (C["personajes"], C["objetos"], C["lugar"], C["momento"]):
            campo.input(_reescena, [C["personajes"], C["objetos"], C["lugar"], C["momento"]], C["escena"])

        C["momento"].change(lambda m: E.escena(m, MOMENTO_TEXTO.get(m, "")), C["momento"], C["escena_img"],
                            show_progress="hidden")

        # ---------------------------------------------------------------- 2 -> 3
        def _elem_continuar(esc):
            if not (esc or "").strip():
                return error("elementos", "err_elem", "Falta la escena",
                             "Escribe qué quieres ver en la portada (en inglés, por ejemplo: a rabbit in a garden).")
            return P(nav("parametros"), err_elem=gr.update(visible=False))

        btn_elem.click(_elem_continuar, [C["escena"]], salidas, show_progress="hidden")

        def _motor_cambia(m):
            ejes = [p for p in EJES if not (m == "B" and p == "P5")]
            return (gr.update(interactive=(m != "B"), info="No aplica al modo libre" if m == "B" else ""),
                    gr.update(choices=[(E.NOMBRES[p], p) for p in ejes], value="P1"))

        motor.change(_motor_cambia, motor, [C["p5"], C["eje"]], show_progress="hidden")

        # ---------------------------------------------------------------- vista de una ronda
        def _vista(ronda: Dict) -> Dict:
            eje, n = ronda["axis"], ronda["round"]
            libres = ronda["planner_plan"]["free"]
            if libres:
                nota = E.tarjeta("info", "El sistema aprendió de tus decisiones",
                                 "Además de «" + E.NOMBRES[eje] + "», probó otras combinaciones de " +
                                 ", ".join(E.NOMBRES[p].lower() for p in libres) + " según lo que aceptaste.")
            else:
                nota = E.tarjeta("info", "Cada propuesta cambia solo una cosa",
                                 f"Aquí cambia únicamente «{E.NOMBRES[eje]}»; todo lo demás es igual para que "
                                 "puedas compararlas.")
            d = {"prop_titulo": E.titulo(f"Ronda {n} de {flujo.MAX_RONDAS}",
                                         "Acepta las que te gustan y rechaza las que no; si rechazas, cuéntanos por qué.",
                                         "mediano"),
                 "prop_nota": nota}
            visibles = 0
            for i, v in enumerate(ronda["variations"]):
                ok = bool(v.get("titled_path"))
                visibles += ok
                d[f"img{i}"] = gr.update(value=v["titled_path"] if ok else None, visible=ok)
                d[f"ph{i}"] = gr.update(visible=not ok)
                d[f"pie{i}"] = E.pie_tarjeta(v["id"], eje, v["params"][eje])
                d[f"op{i}"] = gr.update(value=None, visible=ok)
                estilo = ((v.get("typography") or {}).get("agent") or {}).get("style") or {}
                d[f"ed{i}"] = gr.update(visible=ok, open=False)
                d[f"edf{i}"] = gr.update(value=estilo.get("fuente", "Andika"))
                d[f"edt{i}"] = gr.update(value=estilo.get("tamano", 0.06))
                d[f"edc{i}"] = gr.update(value=estilo.get("curva", 0.0))
                d[f"edk{i}"] = gr.update(value="#%02X%02X%02X" % tuple(estilo.get("color") or (34, 34, 34)))
                d[f"gr{i}"] = gr.update(visible=False)
                d[f"mo{i}"] = gr.update(value=[])
                d[f"co{i}"] = gr.update(value="")
            d["contador"] = E.contador(0, visibles)
            d["btn_cerrar"] = gr.update(interactive=(visibles == 0))
            return d

        # ---------------------------------------------------------------- 3 -> 4 (ronda 1)
        def _generar_primera(img, tit, mot, esc, ins, v1, v2, v3, v4, v5, v6, ej, elem, pe, ob, lu, mo):
            base = {"P1": v1, "P2": v2, "P3": v3, "P4": v4, "P5": v5, "P6": v6}
            fijados = ["P3", "P4"] if elem and elem.get("origen") == "llm" else []
            frio = mot not in MODELOS.motores
            aviso = ("La primera vez se preparan los modelos de dibujo: puede tardar de 1 a 4 minutos."
                     if frio else "Esto toma alrededor de 30 segundos.")
            yield cargando(3, "Preparando tu primera ronda", "Estamos revisando tu boceto y tu historia.", aviso)
            try:
                estado = flujo.iniciar(img, tit, mot, base, esc, ins, fijados,
                                       elementos=_elementos(pe, ob, lu, mo, esc))
            except Exception as e:                            # boceto o texto no válido
                yield error("parametros", "err_param", "No pudimos empezar", html.escape(str(e)))
                return
            try:
                if frio:
                    _log(f"cargando motor {mot}")
                    yield cargando(3, "Despertando al ilustrador", "Cargando los modelos de dibujo y de seguridad.", aviso)
                MODELOS.motor(mot)
                MODELOS.revisor_salida()
                yield cargando(3, "Dibujando tus 5 portadas", "Cada una cambia solo un detalle para que puedas "
                                                                "compararlas.", "Esto toma alrededor de 30 segundos.")
                ronda = _generar(estado, ej)
                _log(f"ronda {ronda['round']} lista en {ronda['latency_round_s']:.1f} s")
            except Exception as e:
                _log(f"error al generar: {e!r}")
                yield error("parametros", "err_param", "No se pudo generar la ronda", html.escape(str(e)))
                return
            yield P(nav("propuestas"), _vista(ronda), est=estado, ronda_st=ronda,
                    err_param=gr.update(visible=False))

        btn_param.click(_generar_primera,
                        [C["boceto"], C["titulo_tb"], motor, C["escena"], instruccion, p1, p2, C["p3"], C["p4"],
                         C["p5"], p6, C["eje"], C["elem_st"], C["personajes"], C["objetos"], C["lugar"],
                         C["momento"]], salidas, show_progress="hidden")

        # ---------------------------------------------------------------- decisiones
        def _decision(ronda, *ops):
            if ronda is None:
                return [skip()] * (2 + N)
            visibles = [bool(v.get("titled_path")) for v in ronda["variations"]]
            hechas = sum(1 for ok, op in zip(visibles, ops) if ok and op)
            total = sum(visibles)
            return [E.contador(hechas, total), gr.update(interactive=hechas >= total),
                    *[gr.update(visible=(ok and op == "Rechazar")) for ok, op in zip(visibles, ops)]]

        entradas_op = [C["ronda_st"], *[C[f"op{i}"] for i in range(N)]]
        for i in range(N):
            C[f"op{i}"].change(_decision, entradas_op,
                               [C["contador"], C["btn_cerrar"], *[C[f"gr{j}"] for j in range(N)]],
                               show_progress="hidden")
        def _editar(i):
            def aplicar(estado, ronda, fuente, tamano, curva, color):
                if estado is None or ronda is None:
                    return [skip(), skip()]
                try:
                    ruta = flujo.editar_titulo(estado, ronda["variations"][i], fuente, tamano, curva, color)
                except ValueError as err:
                    gr.Warning(str(err))
                    return [skip(), skip()]
                flujo.guardar(estado)
                return [gr.update(value=ruta), ronda]
            return aplicar

        for i in range(N):
            C[f"eda{i}"].click(_editar(i), [C["est"], C["ronda_st"], C[f"edf{i}"], C[f"edt{i}"], C[f"edc{i}"],
                                            C[f"edk{i}"]], [C[f"img{i}"], C["ronda_st"]], show_progress="hidden")

        todo_si.click(lambda: ["Aceptar"] * N, None, [C[f"op{i}"] for i in range(N)], show_progress="hidden")
        todo_no.click(lambda: ["Rechazar"] * N, None, [C[f"op{i}"] for i in range(N)], show_progress="hidden")

        def _cerrar(estado, ronda, *valores):
            if estado is None or ronda is None:
                gr.Warning("Primero genera una ronda.")
                return P()
            ops = [v or "Sin decidir" for v in valores[:N]]
            mots, coms = list(valores[N:2 * N]), list(valores[2 * N:])
            try:
                flujo.cerrar_ronda(estado, ronda, ops, coms, mots)
            except ValueError as e:
                gr.Warning(str(e))
                return P()
            libres = flujo.ejes_disponibles(estado)
            hecha = ronda["round"]
            if libres:
                cabecera = E.titulo(f"Ronda {hecha} cerrada",
                                    f"Puedes hacer la ronda {hecha + 1} de {flujo.MAX_RONDAS}: elige qué quieres "
                                    "explorar ahora, o termina para ver tu resumen.")
            else:
                cabecera = E.titulo("Terminaste las tres rondas", "Veamos un resumen de todo lo que decidiste.")
            return P(nav("siguiente", 4), sig_html=cabecera,
                     eje_sig=gr.update(choices=[(E.NOMBRES[p], p) for p in libres],
                                       value=libres[0] if libres else None, visible=bool(libres)),
                     btn_sig=gr.update(visible=bool(libres)))

        C["btn_cerrar"].click(_cerrar, [C["est"], C["ronda_st"], *[C[f"op{i}"] for i in range(N)],
                                        *[C[f"mo{i}"] for i in range(N)], *[C[f"co{i}"] for i in range(N)]],
                              salidas, show_progress="hidden")

        # ---------------------------------------------------------------- rondas 2 y 3
        def _siguiente(estado, ej):
            if estado is None:
                gr.Warning("Genera primero la ronda 1.")
                yield P()
                return
            n = estado.sesion.numero
            yield cargando(4, f"Preparando la ronda {n}", "El sistema usa lo que aceptaste y rechazaste para "
                                                           "elegir las nuevas propuestas.",
                           "Esto toma alrededor de 30 segundos.")
            try:
                ronda = _generar(estado, ej)
                _log(f"ronda {ronda['round']} lista en {ronda['latency_round_s']:.1f} s")
            except Exception as e:
                _log(f"error al generar: {e!r}")
                yield error("siguiente", "sig_html", "No se pudo generar la ronda", html.escape(str(e)), 4)
                return
            yield P(nav("propuestas"), _vista(ronda), ronda_st=ronda)

        C["btn_sig"].click(_siguiente, [C["est"], C["eje_sig"]], salidas, show_progress="hidden")

        # ---------------------------------------------------------------- resumen
        def _terminar(estado, nombre):
            if estado is None or not estado.sesion.rondas:
                gr.Warning("Cierra al menos una ronda primero.")
                yield P()
                return
            yield cargando(5, "Escribiendo tu resumen", "El asistente redacta lo que decidiste y el sistema "
                                                         "comprueba que todo coincida.",
                           "Esto toma entre 30 y 60 segundos.", "frog_resumen")
            try:
                r = flujo.resumir_sesion(estado, MODELOS.llm(nombre), nombre)
            except Exception as e:
                _log(f"error en el resumen: {e!r}")
                yield error("siguiente", "sig_html", "No se pudo escribir el resumen", html.escape(str(e)), 4)
                return
            elegidas = [(v["titled_path"], f"{v['id']} · {E.etiqueta(rd['axis'], v['params'][rd['axis']])}")
                        for rd in estado.sesion.rondas for v in rd["variations"]
                        if v.get("decision") == "accepted" and v.get("titled_path")]
            yield P(nav("final"), galeria=gr.update(value=elegidas, visible=bool(elegidas)),
                    fin_resumen=E.resumen(r["texto"], r["origen"], nombre, r["intentos"]),
                    archivo=str(estado.carpeta / "sesion.json"))

        btn_fin.click(_terminar, [C["est"], llm_r], salidas, show_progress="hidden")

        def _nueva():
            return P(nav("inicio"), est=None, elem_st={}, ronda_st=None, boceto=None, titulo_tb="", historia="",
                     personajes="", objetos="", lugar="", momento="", escena="", galeria=[], archivo=None,
                     escena_img=E.escena(""),
                     err_entrada=gr.update(visible=False), err_param=gr.update(visible=False),
                     err_elem=gr.update(visible=False))

        btn_nueva.click(_nueva, None, salidas, show_progress="hidden")

    demo.frog_componentes = C          # para pruebas y capturas de pantalla
    return demo


def lanzar(compartir: bool = True, bloquear: bool = True, puerto: int = None):
    """Arranca la interfaz. En Colab, `compartir=True` da un enlace público temporal."""
    demo = construir_interfaz()
    # debug=True: en Colab, sin esto Gradio esconde los errores internos de la interfaz.
    extra = {} if _estilo_en_blocks() else _opciones_estilo()
    if puerto:
        extra["server_port"] = puerto
    return demo.queue().launch(share=compartir, debug=bloquear, prevent_thread_lock=not bloquear, **extra)


if __name__ == "__main__":
    lanzar(compartir=False)
