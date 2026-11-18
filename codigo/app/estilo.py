"""Aspecto de FROG: tema de Gradio, CSS y bloques de HTML. Sin lógica de negocio.

Dirección de arte (inspirada en diseño editorial infantil y collage): titulares enormes en
Lilita One con bordes irregulares de papel recortado, bloques planos de amarillo y verde,
fotos como láminas inclinadas, y la ranita sentada sobre los bloques como motivo de marca.
Tipografías con licencia SIL OFL: Lilita One (titulares, va incrustada en la aplicación) y
Nunito (textos y formularios; si no hay internet se usa la del sistema).
"""
from __future__ import annotations

import base64
import html
import math
import random
from pathlib import Path
from typing import Dict, List

from . import recursos as R

VERDE, TINTA, AMARILLO, CREMA = "#347A37", "#1E4D22", "#FFC51B", "#F8F1E4"
PAPEL, CLARO, MORADO, ROJO, TEXTO = "#FBF7EE", "#A5DB91", "#A58BD3", "#B3261E", "#22331F"

ASSETS = Path(__file__).parent / "assets"

# ------------------------------------------------------------- etiquetas para personas
ETIQUETAS: Dict[str, Dict[str, str]] = {
    "P1": {"acuarela": "Acuarela", "lapices": "Lápices de colores", "collage": "Collage de papel",
           "vectorial": "Vectorial plano", "plastilina": "Plastilina 3D"},
    "P2": {"pastel": "Pastel", "calida": "Cálida", "fria": "Fría", "primarios": "Colores primarios",
           "tierra": "Tierra"},
    "P3": {"0-3": "0 a 3 años", "4-6": "4 a 6 años", "7-9": "7 a 9 años", "10-12": "10 a 12 años",
           "sin": "Sin indicar"},
    "P4": {"alegre": "Alegre", "aventura": "Aventura", "calma": "Calma (para dormir)",
           "misterio": "Misterio suave", "humor": "Humor"},
    "P5": {"muy_baja": "Muy libre", "baja": "Libre", "media": "Equilibrada", "alta": "Fiel",
           "muy_alta": "Muy fiel"},
    "P6": {"superior": "Arriba", "inferior": "Abajo", "ambas": "Arriba y abajo", "centrada": "Al centro",
           "sin": "Sin título"},
}
NOMBRES = {"P1": "Estilo de ilustración", "P2": "Paleta de colores", "P3": "Edad del lector",
           "P4": "Ambiente", "P5": "Parecido a tu boceto", "P6": "Dónde va el título"}
CORTO = {"P1": "Estilo", "P2": "Paleta", "P3": "Edad", "P4": "Ambiente", "P5": "Parecido al boceto",
         "P6": "Título"}


def etiqueta(eje: str, valor: str) -> str:
    return ETIQUETAS[eje].get(valor, valor)


def opciones(eje: str, valores) -> List[tuple]:
    """Lista (texto para personas, valor interno) para un menú o grupo de botones."""
    return [(etiqueta(eje, v), v) for v in valores]


# ------------------------------------------------------------------------- mascota
def _svg_uri() -> str:
    try:
        datos = (ASSETS / "frog.svg").read_bytes()
        return "data:image/svg+xml;base64," + base64.b64encode(datos).decode()
    except OSError:
        return ""


_RANA = _svg_uri()


def rana(tam: int = 120, clase: str = "") -> str:
    """Ranita plana del logotipo del README (respaldo si faltaran las ilustraciones)."""
    if not _RANA:
        return f'<span class="frog-emoji {clase}">FROG</span>'
    return f'<img class="frog-mascota {clase}" src="{_RANA}" width="{tam}" height="{tam}" alt="Runa, la ranita de FROG">'


# --------------------------------------------------------------------- piezas gráficas
def filtros() -> str:
    """Filtros SVG que dan bordes de papel recortado a los titulares y de lápiz a los estallidos."""
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'
            '<filter id="f-recorte" x="-4%" y="-8%" width="108%" height="116%">'
            '<feTurbulence type="fractalNoise" baseFrequency="0.03 0.045" numOctaves="2" seed="4" result="r"/>'
            '<feDisplacementMap in="SourceGraphic" in2="r" scale="5" xChannelSelector="R" yChannelSelector="G"/>'
            '</filter>'
            '<filter id="f-lapiz" x="-6%" y="-6%" width="112%" height="112%">'
            '<feTurbulence type="fractalNoise" baseFrequency="0.018 0.022" numOctaves="3" seed="9" result="r"/>'
            '<feDisplacementMap in="SourceGraphic" in2="r" scale="16" xChannelSelector="R" yChannelSelector="G"/>'
            '</filter></defs></svg>')


def estallido(clase: str = "") -> str:
    """Estallido amarillo irregular, como el de la referencia (dos capas: sombra y color)."""
    rnd = random.Random(11)
    n, pts = 15, []
    for i in range(2 * n):
        ang = math.pi * i / n - math.pi / 2
        r = (292 if i % 2 == 0 else 196) + rnd.uniform(-16, 16)
        pts.append(f"{300 + r * math.cos(ang):.0f},{300 + r * math.sin(ang):.0f}")
    puntos = " ".join(pts)
    return (f'<svg class="f-estallido {clase}" viewBox="0 0 600 600" aria-hidden="true" style="filter:url(#f-lapiz)">'
            f'<polygon points="{puntos}" fill="#F0AE00" transform="translate(12 14)"/>'
            f'<polygon points="{puntos}" fill="{AMARILLO}"/></svg>')



# --------------------------------------------------------------------- bloques HTML
PASOS = ["Entrada", "Elementos", "Parámetros", "Propuestas", "Resumen"]


def logo() -> str:
    return '<a class="f-logo f-display" aria-label="FROG">FROG</a>'


def barra_pasos(actual: int) -> str:
    """Línea editorial de cinco pasos. actual: 1 a 5; 0 = no mostrar (pantalla de inicio)."""
    if actual <= 0:
        return ""
    celdas = []
    for i, nombre in enumerate(PASOS, start=1):
        estado = "hecho" if i < actual else "actual" if i == actual else "futuro"
        celdas.append(f'<li class="f-paso {estado}"{" aria-current=step" if i == actual else ""}>'
                      f'<b>{i:02d}</b><span>{nombre}</span></li>')
    return f'<ol class="f-pasos" aria-label="Progreso">{"".join(celdas)}</ol>'


def titulo(texto: str, sub: str = "", tam: str = "grande") -> str:
    """Titular de pantalla: enorme, en verde, alineado a la izquierda. tam: grande | mediano."""
    s = f'<p class="f-sub">{sub}</p>' if sub else ""
    return f'<div class="f-titulo {tam}"><h2 class="f-display">{texto}</h2>{s}</div>'


def titulo_bloque(texto: str, sub: str = "") -> str:
    """Titular que va dentro de un bloque verde: amarillo sobre verde, con una línea de apoyo en blanco."""
    s = f"<p>{sub}</p>" if sub else ""
    return f'<div class="f-tb"><h3 class="f-display">{texto}</h3>{s}</div>'


def etiqueta_campo(texto: str, ayuda: str = "") -> str:
    """Rótulo de un campo: mayúsculas pequeñas y, solo si ayuda a entenderlo, una línea de apoyo."""
    a = f"<small>{ayuda}</small>" if ayuda else ""
    return f'<div class="f-etiqueta"><b>{texto}</b>{a}</div>'


def ficha(texto: str, ayuda: str = "", tono: int = 1) -> str:
    """Pestaña de color de una ficha de elemento (personajes, objetos, lugar, momento)."""
    a = f"<small>{ayuda}</small>" if ayuda else ""
    return f'<div class="f-tab t{tono}"><b>{texto}</b>{a}</div>'


def inicio_texto() -> str:
    spark = R.img("ico_brillo", ancho=54, clase="f-chispa c1") + R.img("ico_brillo", ancho=32, clase="f-chispa c2")
    return f"""
<div class="f-hero-texto">
  {spark}
  <h1 class="f-display f-gigante">FROG</h1>
  <p class="f-lema">Convierte tu historia en una portada ilustrada.</p>
  <p class="f-parrafo">Sube un boceto y cuéntanos tu cuento. En cada ronda recibes cinco propuestas de
  portada, eliges las que te gustan y el sistema aprende de tus decisiones. Te acompaña <b>Runa</b>.</p>
</div>"""


def inicio_imagen() -> str:
    rana_ = R.img("frog_hero", ancho=430, clase="f-hero-rana", alt="Runa, la ranita de FROG, leyendo un libro") or rana(300)
    return f'<div class="f-hero-imagen">{estallido()}{rana_}</div>'


def como_funciona() -> str:
    pasos = [("Sube tu boceto", "Un dibujo con líneas oscuras sobre fondo claro, y tu historia en español."),
             ("Elige entre cinco portadas", "Cada propuesta cambia un detalle para que puedas compararlas."),
             ("El sistema aprende", "Hasta tres rondas, y al final un resumen de tus decisiones.")]
    items = "".join(f"<li><b class='f-display'>{i}</b><div><h3>{t}</h3><p>{d}</p></div></li>"
                    for i, (t, d) in enumerate(pasos, start=1))
    return f'<ol class="f-como">{items}</ol>'


def carga(titulo_: str, detalle: str, aviso: str = "", mascota: str = "frog_generando") -> str:
    extra = f'<p class="f-aviso-tiempo">{aviso}</p>' if aviso else ""
    rana_ = R.img(mascota, alto=230, clase="salta", alt="Runa trabajando") or rana(180, "salta")
    return (f'<div class="f-carga"><div class="f-carga-rana">{rana_}</div>'
            f'<div class="f-carga-texto"><h2 class="f-display">{titulo_}</h2><p>{detalle}</p>'
            f'<div class="f-barra" role="progressbar" aria-label="Trabajando"><span></span></div>{extra}</div></div>')


def tarjeta(tipo: str, titulo_: str, texto: str) -> str:
    """Nota editorial con una barra de color a la izquierda. tipo: ok | aviso | error | info"""
    return (f'<div class="f-nota {tipo}" role="{"alert" if tipo == "error" else "status"}">'
            f'<b>{titulo_}</b><p>{texto}</p></div>')


def bloqueada() -> str:
    return (f'<div class="f-bloqueada">{R.img("ico_bloqueo", alto=54)}'
            '<b>Propuesta bloqueada por seguridad</b>'
            '<p>No podemos mostrar esta imagen porque no cumple nuestras políticas de contenido.</p></div>')


# Escena de ejemplo según el momento del día (no es la portada: solo ambienta el paso 2).
ESCENA_DE = {"sunrise": "escena_dia", "morning": "escena_dia", "noon": "escena_dia", "afternoon": "escena_dia",
             "evening": "escena_noche", "night": "escena_noche"}


def escena(momento: str, texto: str = "") -> str:
    """Lámina inclinada que ambienta el momento del día elegido. Sin momento o en el atardecer, bosque."""
    imagen = R.img(ESCENA_DE.get(momento, "escena_bosque"), ancho=300, alt="")
    return (f'<figure class="f-escena">{imagen}'
            f'<figcaption>{texto or "Ambiente de tu historia"}</figcaption></figure>')


def imagen(nombre: str, ancho: int, clase: str = "") -> str:
    """Una ilustración de la marca a un ancho dado (decorativa: sin texto alternativo)."""
    return R.img(nombre, ancho=ancho, clase=clase, alt="") or ""


def asoma(nombre: str, ancho: int, clase: str = "") -> str:
    """La ranita asomada sobre el borde de un bloque (motivo de marca)."""
    return R.img(nombre, ancho=ancho, clase=f"f-asoma-img {clase}", alt="") or ""


def pie_tarjeta(idp: str, eje: str, valor: str) -> str:
    """Pie de la lámina: qué parámetro cambia y con qué valor."""
    return (f'<div class="f-pie"><span class="f-id">{html.escape(idp)}</span>'
            f'<span class="f-eje">{html.escape(CORTO[eje])}</span>'
            f'<b class="f-valor f-display">{html.escape(etiqueta(eje, valor))}</b></div>')


def contador(decididas: int, total: int) -> str:
    segmentos = "".join(f'<i class="{"on" if k < decididas else ""}"></i>' for k in range(total))
    if total == 0:
        return tarjeta("aviso", "Ninguna propuesta se pudo mostrar",
                       "Todas fueron bloqueadas por seguridad. Cierra la ronda y prueba con otra indicación.")
    if decididas >= total:
        texto = "<b>Listo</b><span>Ya decidiste en todas las propuestas. Puedes cerrar la ronda.</span>"
    else:
        texto = (f"<b>Has decidido {decididas} de {total}</b>"
                 "<span>Acepta o rechaza todas las propuestas para continuar.</span>")
    return f'<div class="f-contador" role="status"><div class="f-seg">{segmentos}</div>{texto}</div>'


def insignia(origen: str, modelo: str, intentos: int) -> str:
    if origen == "llm":
        return (f'<span class="f-insignia ok">Resumen redactado por {html.escape(modelo)} y verificado '
                f'contra tus decisiones</span>')
    return ('<span class="f-insignia plantilla">Resumen automático: el modelo no pasó la verificación, '
            'así que mostramos solo lo que quedó registrado</span>')


def _para_personas(texto: str) -> str:
    """Solo al mostrar: 'eje: P1 (Estilo)' -> 'eje: Estilo'. El texto guardado y validado no cambia."""
    import re
    return re.sub(r"P\d \(([^)]+)\)", lambda m: m.group(1), texto)


def resumen(texto: str, origen: str, modelo: str, intentos: int) -> str:
    texto = _para_personas(texto)
    lineas = "".join(f"<p>{html.escape(l)}</p>" for l in texto.splitlines() if l.strip())
    return (f'<div class="f-resumen">{insignia(origen, modelo, intentos)}'
            f'<h3 class="f-display">Lo que decidiste</h3>{lineas}</div>')


# ------------------------------------------------------------------------------ tema
def tema():
    import gradio as gr
    verde = gr.themes.Color(c50="#EAF4E8", c100="#D3E8CF", c200="#A5DB91", c300="#7CBF6E", c400="#4F9B50",
                            c500="#347A37", c600="#2B6830", c700="#1E4D22", c800="#183F1C", c900="#103015",
                            c950="#0A2010", name="verde_bosque")
    amarillo = gr.themes.Color(c50="#FFF8DC", c100="#FFEFAE", c200="#FFE37A", c300="#FFD64A", c400="#FFCB2E",
                               c500="#FFC51B", c600="#E6AE00", c700="#B38700", c800="#806000", c900="#4D3A00",
                               c950="#2B2000", name="amarillo")
    t = gr.themes.Base(primary_hue=verde, secondary_hue=amarillo, neutral_hue=gr.themes.colors.stone,
                       radius_size=gr.themes.sizes.radius_sm,
                       font=[gr.themes.GoogleFont("Nunito"), "ui-sans-serif", "system-ui", "sans-serif"])
    return t.set(
        body_background_fill=CREMA, body_background_fill_dark=CREMA, body_text_color=TEXTO,
        body_text_color_dark=TEXTO, block_background_fill="transparent", block_background_fill_dark="transparent",
        block_border_color="transparent", block_border_color_dark="transparent",
        block_label_text_color=TINTA, block_label_text_color_dark=TINTA,
        block_title_text_color=TINTA, block_title_text_color_dark=TINTA,
        input_background_fill=PAPEL, input_background_fill_dark=PAPEL,
        input_border_color=TINTA, input_border_color_dark=TINTA,
        button_primary_background_fill=AMARILLO, button_primary_background_fill_hover="#FFD24D",
        button_primary_background_fill_dark=AMARILLO, button_primary_background_fill_hover_dark="#FFD24D",
        button_primary_text_color=TINTA, button_primary_text_color_dark=TINTA,
        button_secondary_background_fill=PAPEL, button_secondary_background_fill_dark=PAPEL,
        button_secondary_text_color=TINTA, button_secondary_text_color_dark=TINTA,
        button_secondary_border_color=TINTA, button_secondary_border_color_dark=TINTA,
        color_accent_soft="#EAF4E8", color_accent_soft_dark="#EAF4E8",
    )


def _fuente_incrustada() -> str:
    """Lilita One (SIL OFL) como @font-face: los titulares se ven igual sin conexión."""
    try:
        datos = (ASSETS / "fuentes" / "LilitaOne-Regular.ttf").read_bytes()
    except OSError:
        return ""
    return ("@font-face { font-family: 'Lilita One'; font-style: normal; font-display: swap; "
            f"src: url(data:font/ttf;base64,{base64.b64encode(datos).decode()}) format('truetype'); }}\n")


_CSS_BASE = """
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
__FUENTE__
:root { color-scheme: light; --verde:#347A37; --tinta:#1E4D22; --amarillo:#FFC51B; --amarillo-osc:#F0AE00;
        --crema:#F8F1E4; --papel:#FBF7EE; --claro:#A5DB91; --morado:#A58BD3; --rojo:#B3261E; --texto:#22331F; }
html, body, gradio-app, .gradio-container { background-color: var(--crema) !important;
  background-image: linear-gradient(rgba(248,241,228,.70), rgba(248,241,228,.70)), url(__PAPEL__) !important;
  background-repeat: repeat !important; background-size: auto, 272px auto !important; }
.gradio-container { width: min(1740px, 100%) !important; max-width: 1740px !important; margin: 0 auto !important;
  padding: 6px 18px 70px !important; font-family: 'Nunito', system-ui, sans-serif; color: var(--texto); font-size: 17px; }
footer { display: none !important; }
.f-filtros { position: absolute !important; width: 0 !important; height: 0 !important; overflow: hidden;
  padding: 0 !important; margin: 0 !important; border: 0 !important; }

/* titulares: Lilita One con bordes de papel recortado */
.f-display { font-family: 'Lilita One', 'Fredoka', system-ui, sans-serif !important; font-weight: 400 !important;
  text-transform: uppercase; color: var(--verde); letter-spacing: .01em; line-height: .94; margin: 0;
  filter: url(#f-recorte); }
.f-titulo h2 { font-size: clamp(46px, 5.6vw, 88px); }
.f-titulo.mediano h2 { font-size: clamp(40px, 4.2vw, 66px); }
.f-tb h3 { font-size: clamp(30px, 2.8vw, 42px); color: var(--amarillo) !important; line-height: 1; }
.f-tb p { font-size: 16px; margin: 8px 0 14px; color: #fff; }
.f-pagina { gap: 22px !important; }
.f-sub { font-size: 19px; line-height: 1.45; max-width: 560px; margin: 14px 0 0; }

/* cabecera editorial: logotipo y pasos sobre una regla gruesa */
.f-cab { align-items: center !important; justify-content: space-between !important; gap: 20px !important;
  border-bottom: 3px solid var(--tinta); padding: 10px 2px 8px !important; margin-bottom: 26px !important; flex-wrap: nowrap !important; }
.f-cab > * { min-width: 0 !important; }
.f-logo { font-size: 40px; display: inline-block; text-decoration: none; }
.f-pasos { list-style: none; display: flex; gap: 4px; margin: 0; padding: 0; justify-content: flex-end; }
.f-paso { display: flex; align-items: baseline; gap: 7px; padding: 6px 14px 5px; position: relative; color: var(--tinta); }
.f-paso b { font-family: 'Lilita One', sans-serif; font-weight: 400; font-size: 24px; line-height: 1; }
.f-paso span { font-size: 12px; font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
.f-paso.futuro { opacity: .42; }
.f-paso.hecho b { color: var(--verde); }
.f-paso.hecho::after { content: ""; position: absolute; left: 14px; right: 14px; bottom: 0; height: 4px; background: var(--verde); }
.f-paso.actual { background: var(--amarillo); transform: rotate(-1.4deg); box-shadow: 3px 3px 0 var(--tinta); }

/* bloques de color con borde irregular (el color va en ::before para no recortar lo que asoma) */
.f-amarillo, .f-verde { position: relative !important; isolation: isolate; padding: 30px 32px !important; }
.f-amarillo::before, .f-verde::before { content: ""; position: absolute; inset: 0; z-index: -1;
  clip-path: polygon(0 2.5%, 2.5% 0, 24% 1.2%, 51% 0, 78% 1.4%, 100% 0, 99.2% 33%, 100% 64%, 98.8% 100%, 72% 98.6%,
                     44% 100%, 16% 98.7%, 0 100%, .9% 62%); }
.f-amarillo::before { background: var(--amarillo); }
.f-verde::before { background: var(--verde); }
.f-verde, .f-verde label, .f-verde span, .f-verde p, .f-verde h3, .f-verde .f-etiqueta { color: #fff; }

/* la ranita asomada sobre el borde de un bloque */
.f-asoma { position: absolute !important; z-index: 4; padding: 0 !important; background: none !important;
  border: 0 !important; pointer-events: none; width: auto !important; min-width: 0 !important; }
.f-asoma-img { filter: drop-shadow(0 6px 8px rgba(30,40,20,.25)); display: block; }
.f-asoma .f-asoma-img { max-width: none !important; }
.f-col-boceto { min-height: 740px; padding-bottom: 150px !important; }
.f-asoma-entrada { width: 200px !important; right: 6px; bottom: -66px; }
.f-col-escena { padding-bottom: 36px !important; }
.f-asoma-elem { width: 190px !important; right: 22px; top: -64px; }
.f-col-eje { padding-bottom: 175px !important; margin-bottom: 40px !important; }
.f-asoma-param { width: 195px !important; right: 18px; bottom: -34px; }

/* etiquetas, textos de apoyo y campos */
.f-etiqueta { margin-bottom: -20px; }
.f-etiqueta b { display: block; font-size: 12.5px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
  color: var(--tinta); }
.f-etiqueta small { display: block; font-size: 14px; color: #4b5d46; margin-top: 2px; }
.f-verde .f-etiqueta b, .f-verde .f-etiqueta small { color: #fff; }
.gradio-container .block, .gradio-container .form, .gradio-container fieldset { background: transparent !important;
  border: 0 !important; box-shadow: none !important; }
.gradio-container input[type=text], .gradio-container textarea, .gradio-container .wrap-inner {
  background: var(--papel) !important; border: 2.5px solid var(--tinta) !important; border-radius: 3px !important;
  font-size: 18px; color: var(--texto); }
.gradio-container input[type=text]:focus, .gradio-container textarea:focus { outline: 4px solid var(--amarillo) !important;
  outline-offset: 0; }
.gradio-container label > span, .gradio-container .block-title { font-weight: 800; font-size: 12.5px;
  letter-spacing: .09em; text-transform: uppercase; color: var(--tinta); }
.gradio-container .info { font-size: 14px; font-weight: 400; text-transform: none; letter-spacing: 0; color: #4b5d46; }

/* botones: planos, con borde y sombra dura */
.gradio-container button.primary, .gradio-container button.secondary { font-family: 'Nunito', sans-serif !important;
  font-weight: 800 !important; font-size: 16px !important; letter-spacing: .08em; text-transform: uppercase;
  border: 3px solid var(--tinta) !important; border-radius: 3px !important; padding: 15px 30px !important;
  box-shadow: 5px 5px 0 var(--tinta) !important; transition: transform .1s, box-shadow .1s; }
.gradio-container button.primary { background: var(--amarillo) !important; color: var(--tinta) !important; }
.gradio-container button.secondary { background: var(--papel) !important; color: var(--tinta) !important; }
.gradio-container button.primary:hover, .gradio-container button.secondary:hover { transform: translate(2px, 2px);
  box-shadow: 3px 3px 0 var(--tinta) !important; }
.gradio-container button:disabled { opacity: .45; box-shadow: none !important; transform: none; cursor: not-allowed; }
.gradio-container button.sm { padding: 9px 16px !important; font-size: 13px !important; box-shadow: 3px 3px 0 var(--tinta) !important; }
.f-centrar { max-width: 420px; }

/* opciones en tira (modo de dibujo, asistente) */
.f-tira .wrap { display: flex !important; flex-direction: column; align-items: stretch; gap: 0 !important; }
.f-tira label { border: 2.5px solid var(--tinta) !important; background: var(--papel) !important; padding: 9px 16px !important;
  margin: 0 0 -2.5px 0 !important; border-radius: 0 !important; font-weight: 700 !important; cursor: pointer; }
.f-tira label input { position: absolute; opacity: 0; pointer-events: none; }
.f-tira label.selected { background: var(--amarillo) !important; color: var(--tinta) !important; position: relative; z-index: 1; }
.f-tira label span { text-transform: none; letter-spacing: 0; font-size: 15px; color: var(--tinta); }

/* opciones apiladas sobre el bloque verde (qué cambia entre las cinco) */
.f-pila .wrap { display: flex !important; flex-direction: column; gap: 10px !important; }
.f-pila label { border: 2.5px solid #fff !important; background: transparent !important; padding: 13px 16px !important;
  border-radius: 3px !important; cursor: pointer; }
.f-pila label span { color: #fff !important; font-size: 17px !important; text-transform: none; letter-spacing: 0;
  font-weight: 700; }
.f-pila label input { position: absolute; opacity: 0; pointer-events: none; }
.f-pila label.selected { background: var(--amarillo) !important; border-color: var(--amarillo) !important; }
.f-pila label.selected span { color: var(--tinta) !important; }

/* pantalla de inicio */
.f-hero-texto { position: relative; padding-top: 18px; }
.f-gigante { font-size: clamp(120px, 15vw, 230px); line-height: .82; }
.f-chispa { position: absolute; }
.f-chispa.c1 { left: -8px; top: -4px; } .f-chispa.c2 { left: 52px; top: -22px; }
.f-lema { font-size: clamp(26px, 2.5vw, 38px); font-weight: 800; line-height: 1.12; margin: 26px 0 12px; color: var(--tinta); }
.f-parrafo { font-size: 19px; line-height: 1.55; max-width: 500px; margin: 0 0 26px; }
.f-hero-imagen { position: relative; display: flex; justify-content: center; align-items: center; min-height: 520px; }
.f-estallido { position: absolute; width: min(560px, 100%); left: 50%; top: 50%; transform: translate(-50%, -50%); z-index: 0; }
.f-hero-rana { position: relative; z-index: 2; max-width: 92%; height: auto; }
.f-como { list-style: none; display: grid; grid-template-columns: repeat(3, 1fr); gap: 0; margin: 38px 0 0; padding: 22px 0 0;
  border-top: 3px solid var(--tinta); }
.f-como li { display: flex; gap: 16px; padding-right: 32px; }
.f-como b { font-size: 64px; line-height: .9; color: var(--amarillo-osc); }
.f-como h3 { font-size: 19px; margin: 4px 0 4px; color: var(--tinta); }
.f-como p { margin: 0; font-size: 16px; line-height: 1.45; }

/* láminas: el boceto y las portadas, como fotos impresas */
.f-lamina { background: var(--papel) !important; padding: 12px 12px 14px !important; gap: 8px !important;
  box-shadow: 0 16px 26px -12px rgba(30,40,20,.55), 0 2px 0 rgba(0,0,0,.06) !important; transition: transform .18s; }
.f-lamina img { border-radius: 0 !important; }
.f-lamina button[aria-label="Descargar"], .f-lamina button[aria-label="Compartir"],
.f-lamina button[aria-label="Download"], .f-lamina button[aria-label="Share"] { display: none !important; }
.f-lamina:hover { transform: rotate(0deg) translateY(-4px) !important; }
.f-giro1 { transform: rotate(-1.6deg); } .f-giro2 { transform: rotate(1.1deg); } .f-giro3 { transform: rotate(-.7deg); }
.f-giro4 { transform: rotate(1.4deg); } .f-giro5 { transform: rotate(-1.1deg); }
.f-boceto.f-lamina { padding-bottom: 54px !important; }

/* fichas de elementos: pestaña de color y campo */
.f-ficha { background: var(--papel) !important; border: 2.5px solid var(--tinta) !important; padding: 0 !important;
  gap: 0 !important; box-shadow: 5px 5px 0 var(--tinta); }
.f-ficha > .block { padding: 12px 14px !important; }
.f-tab { padding: 8px 14px; border-bottom: 2.5px solid var(--tinta); display: flex; align-items: baseline; gap: 10px; }
.f-tab b { font-size: 12.5px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--tinta); }
.f-tab small { font-size: 13px; color: var(--tinta); opacity: .75; }
.f-tab.t1 { background: var(--claro); } .f-tab.t2 { background: var(--amarillo); }
.f-tab.t3 { background: var(--morado); } .f-tab.t4 { background: #fff; }
.f-escena { margin: 0; text-align: center; transform: rotate(1.6deg); background: var(--papel); padding: 10px 10px 8px;
  box-shadow: 0 14px 22px -12px rgba(30,40,20,.55); width: fit-content; }
.f-escena img { display: block; }
.f-escena figcaption { font-size: 13px; font-weight: 800; letter-spacing: .09em; text-transform: uppercase;
  color: var(--tinta); margin-top: 8px; }

/* propuestas */
.f-pie { display: flex; flex-direction: column; gap: 1px; padding: 2px 2px 0; }
.f-id { font-size: 11px; font-weight: 800; letter-spacing: .12em; color: #6a7a62; }
.f-eje { font-size: 12px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--tinta); }
.f-valor { font-size: 25px; line-height: 1; margin-top: 2px; filter: none; }
.f-bloqueada { aspect-ratio: 2/3; display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; gap: 8px; padding: 14px; border: 2.5px dashed var(--tinta); color: var(--tinta); }
.f-bloqueada p { font-size: 13px; margin: 0; }
.f-decision .wrap { display: grid !important; grid-template-columns: 1fr; gap: 8px !important; }
.f-decision label { display: flex !important; justify-content: center; align-items: center; text-align: center;
  border: 2.5px solid var(--tinta) !important; border-radius: 3px !important; background: var(--papel) !important;
  padding: 10px 6px !important; cursor: pointer; }
.f-decision label input { position: absolute; opacity: 0; pointer-events: none; }
.f-decision label span { font-size: 13.5px !important; font-weight: 800; letter-spacing: .05em; text-transform: uppercase;
  white-space: nowrap; color: var(--tinta); }
.f-decision label:has(input[value="Rechazar"]) { border-color: var(--rojo) !important; }
.f-decision label:has(input[value="Rechazar"]) span { color: var(--rojo); }
.f-decision label.selected:has(input[value="Aceptar"]) { background: var(--verde) !important; border-color: var(--tinta) !important; }
.f-decision label.selected:has(input[value="Aceptar"]) span { color: #fff; }
.f-decision label.selected:has(input[value="Rechazar"]) { background: var(--rojo) !important; }
.f-decision label.selected:has(input[value="Rechazar"]) span { color: #fff; }
.f-editar { border: 2px solid var(--tinta) !important; border-radius: 0 !important; background: transparent !important;
  box-shadow: none !important; }
.f-editar > button, .f-editar .label-wrap { font-size: 12.5px !important; font-weight: 800 !important; letter-spacing: .06em;
  text-transform: uppercase; padding: 8px 10px !important; color: var(--tinta) !important; }
.f-editar label span, .f-editar .block-info { font-size: 12px !important; }
.f-editar input[type=number] { max-width: 64px !important; }
.f-motivos .wrap { display: flex !important; flex-wrap: wrap; gap: 6px !important; }
.f-motivos label { border: 2px solid var(--tinta) !important; border-radius: 999px !important; padding: 4px 11px !important;
  background: var(--papel) !important; cursor: pointer; }
.f-motivos label input { position: absolute; opacity: 0; pointer-events: none; }
.f-motivos label span { font-size: 12.5px !important; font-weight: 700; text-transform: none; letter-spacing: 0; }
.f-motivos label.selected { background: var(--amarillo) !important; }
.f-lamina textarea, .f-lamina input[type=text] { font-size: 15px !important; }

/* barra de acción de las propuestas: siempre a la vista */
/* fija al borde inferior de la ventana (sticky no funciona dentro de la estructura de Gradio) */
.f-accion { position: fixed !important; bottom: 0; left: 50%; transform: translateX(-50%); z-index: 50;
  width: min(1740px, 100%); box-sizing: border-box; background: var(--crema) !important;
  border-top: 3px solid var(--tinta); padding: 12px 18px 14px !important; margin: 0 !important; }
.f-pagina:has(.f-accion) { padding-bottom: 190px; }
.f-contador { display: flex; align-items: center; gap: 14px; }
.f-contador .f-seg { display: flex; gap: 4px; }
.f-contador .f-seg i { width: 34px; height: 12px; border: 2.5px solid var(--tinta); background: var(--papel); }
.f-contador .f-seg i.on { background: var(--verde); }
.f-contador b { font-size: 17px; color: var(--tinta); }
.f-contador span { font-size: 15px; }

/* notas: barra de color a la izquierda, sin iconos */
.f-nota { border-left: 8px solid var(--verde); background: var(--papel); padding: 11px 16px; margin: 4px 0; }
.f-nota > b { display: block; font-size: 13px; letter-spacing: .09em; text-transform: uppercase; color: var(--tinta); }
.f-nota p { margin: 2px 0 0; font-size: 16px; }
.f-nota.aviso { border-left-color: var(--amarillo); } .f-nota.error { border-left-color: var(--rojo); }
.f-nota.info { border-left-color: var(--morado); }

/* carga */
.f-carga { position: relative; isolation: isolate; display: flex; align-items: center; gap: 40px; padding: 44px 52px; }
.f-carga::before { content: ""; position: absolute; inset: 0; z-index: -1; background: var(--amarillo);
  clip-path: polygon(0 3%, 2% 0, 30% 1.4%, 62% 0, 100% 1.8%, 99% 38%, 100% 70%, 98.6% 100%, 66% 98.4%, 34% 100%, 0 98.5%, 1.2% 55%); }
.f-carga-rana img { display: block; } .f-carga-texto { flex: 1; }
.f-carga h2 { font-size: clamp(40px, 4.4vw, 68px); color: var(--tinta); }
.f-carga p { font-size: 19px; margin: 12px 0 0; color: var(--tinta); max-width: 560px; }
.f-barra { height: 18px; max-width: 560px; margin: 24px 0 14px; border: 3px solid var(--tinta); background: var(--papel); overflow: hidden; }
.f-barra span { display: block; height: 100%; width: 36%; background: var(--verde); animation: barra 1.7s ease-in-out infinite; }
.f-aviso-tiempo { font-size: 15px !important; font-weight: 800; letter-spacing: .02em; }
.salta { animation: salta 1.1s ease-in-out infinite; }
.flota { animation: flota 3.6s ease-in-out infinite; }
@keyframes salta { 0%, 100% { transform: translateY(0) } 40% { transform: translateY(-20px) } }
@keyframes flota { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-10px) } }
@keyframes barra { 0% { transform: translateX(-110%) } 100% { transform: translateX(300%) } }

/* resumen final */
.f-resumen { background: var(--papel); border: 2.5px solid var(--tinta); box-shadow: 6px 6px 0 var(--tinta); padding: 22px 28px 12px; }
.f-resumen h3 { font-size: 34px; margin: 12px 0 8px; }
.f-resumen p { font-size: 17px; line-height: 1.55; margin: 8px 0; }
.f-insignia { display: inline-block; font-size: 14px; font-weight: 700; padding: 5px 12px; border: 2px solid var(--tinta); }
.f-insignia.ok { background: var(--claro); } .f-insignia.plantilla { background: var(--amarillo); }
.f-galeria, .f-galeria .grid-wrap, .f-galeria .grid-container { max-height: none !important; height: auto !important; overflow: visible !important; }
.f-galeria .thumbnail-item { background: var(--papel) !important; border: 0 !important; padding: 10px 10px 36px !important;
  box-shadow: 0 14px 22px -12px rgba(30,40,20,.5); aspect-ratio: auto !important; }
.f-galeria .caption-label, .f-galeria .thumbnail-item .caption-label { font-size: 12.5px !important; font-weight: 800 !important;
  letter-spacing: .08em; text-transform: uppercase; color: var(--tinta) !important; background: transparent !important; opacity: 1 !important; }
.f-archivo { border: 2.5px solid var(--tinta) !important; background: var(--papel) !important; border-radius: 3px !important; }
.frog-img, .f-img { max-width: 100%; }
img.f-chispa { height: auto; }

@media (max-width: 900px) {
  .f-como { grid-template-columns: 1fr; gap: 16px; } .f-carga { flex-direction: column; text-align: center; padding: 30px; }
  .f-pasos .f-paso span { display: none; } .f-hero-imagen { min-height: 340px; }
}
"""

JS_CLARO = "() => { document.body.classList.remove('dark'); }"
CSS = (_CSS_BASE.replace("__FUENTE__", _fuente_incrustada()).replace("__PAPEL__", R.uri("textura_papel") or "none"))
