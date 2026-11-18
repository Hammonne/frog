"""Construye FROG_Final_Presentation.pptx (13 slides, 16:9, textos y gráficos editables).

Identidad: verde bosque, amarillo mostaza, verde claro y blanco hueso; fondos de papel con grano; Runa,
la mascota de FROG, y sus elementos recortados de las láminas de recursos (assets/presentacion/recortes).
Todos los números salen de los experimentos del repositorio; lo que falta se marca como pendiente.

Uso:  python presentacion/construir_presentacion.py
"""
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt
from lxml import etree

RAIZ = Path(__file__).resolve().parents[1]
REC = RAIZ / "assets" / "presentacion" / "recortes"
ASS = RAIZ / "assets" / "presentacion"
DEMO = RAIZ / "codigo" / "salidas" / "demo"
SALIDA = Path(__file__).resolve().parent / "FROG_Final_Presentation.pptx"

VERDE, OSCURO, AMARILLO = "2E7D32", "1B4D20", "FFC107"
CLARO, HUESO, BLANCO, ROJO = "B7F59E", "F7F7EE", "FFFFFF", "D9534F"
TITULO, CUERPO, CODIGO = "Lilita One", "Poppins", "Courier New"
KICKER = "Poppins SemiBold"


def rgb(h):
    return RGBColor.from_string(h)


prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
VACIO = prs.slide_layouts[6]


# ------------------------------------------------------------------ utilidades
def fondo(s, nombre="fondo_papel.png"):
    p = s.shapes.add_picture(str(ASS / nombre), 0, 0, prs.slide_width, prs.slide_height)
    p.name = "Fondo de papel"
    return p


def imagen(s, ruta, x, y, w=None, h=None, nombre=None, rot=0):
    """Inserta una imagen conservando su proporción (da w o h)."""
    ruta = str(ruta)
    ancho, alto = Image.open(ruta).size
    if w is None:
        w = h * ancho / alto
    if h is None:
        h = w * alto / ancho
    p = s.shapes.add_picture(ruta, Inches(x), Inches(y), Inches(w), Inches(h))
    p.rotation = rot
    if nombre:
        p.name = nombre
    return p


def imagen_recorte(s, ruta, x, y, w, h, nombre=None, rot=0):
    """Rellena una caja w×h recortando la imagen (cover)."""
    ancho, alto = Image.open(str(ruta)).size
    p = s.shapes.add_picture(str(ruta), Inches(x), Inches(y), Inches(w), Inches(h))
    r_caja, r_img = w / h, ancho / alto
    if r_img > r_caja:
        sobra = 1 - r_caja / r_img
        p.crop_left = p.crop_right = sobra / 2
    else:
        sobra = 1 - r_img / r_caja
        p.crop_top = p.crop_bottom = sobra / 2
    p.rotation = rot
    if nombre:
        p.name = nombre
    return p


def sombra(shape, blur=6, dist=3, alpha=28):
    sp = shape._element.spPr
    for e in sp.findall(qn("a:effectLst")):
        sp.remove(e)
    ef = etree.SubElement(sp, qn("a:effectLst"))
    sh = etree.SubElement(ef, qn("a:outerShdw"), blurRad=str(int(blur * 12700)), dist=str(int(dist * 12700)),
                          dir="5400000", algn="t", rotWithShape="0")
    c = etree.SubElement(sh, qn("a:srgbClr"), val="2A3A20")
    etree.SubElement(c, qn("a:alpha"), val=str(alpha * 1000))


def caja(s, x, y, w, h, color=BLANCO, linea=None, grosor=2, forma=MSO_SHAPE.RECTANGLE, sombrea=False, nombre=None,
         radio=None, rot=0):
    f = s.shapes.add_shape(forma, Inches(x), Inches(y), Inches(w), Inches(h))
    if color is None:
        f.fill.background()
    else:
        f.fill.solid()
        f.fill.fore_color.rgb = rgb(color)
    if linea:
        f.line.color.rgb = rgb(linea)
        f.line.width = Pt(grosor)
    else:
        f.line.fill.background()
    if radio is not None and forma == MSO_SHAPE.ROUNDED_RECTANGLE:
        f.adjustments[0] = radio
    f.rotation = rot
    if sombrea:
        sombra(f)
    if nombre:
        f.name = nombre
    f.text_frame.text = ""
    return f


def texto(s, x, y, w, h, parrafos, size=16, color=OSCURO, fuente=CUERPO, negrita=False, align=PP_ALIGN.LEFT,
          ancla=MSO_ANCHOR.TOP, nombre=None, interlineado=None, espacio=0, cursiva=False):
    """parrafos: str | [str | [(texto, {opciones})]]"""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = ancla
    if isinstance(parrafos, str):
        parrafos = [parrafos]
    for i, par in enumerate(parrafos):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if interlineado:
            p.line_spacing = interlineado
        if espacio and i:
            p.space_before = Pt(espacio)
        runs = [(par, {})] if isinstance(par, str) else par
        for t, o in runs:
            r = p.add_run()
            r.text = t
            r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("negrita", negrita)
            r.font.italic = o.get("cursiva", cursiva)
            r.font.name = o.get("fuente", fuente)
            r.font.color.rgb = rgb(o.get("color", color))
    if nombre:
        tb.name = nombre
    return tb


def kicker(s, t, x=0.7, y=0.24):
    """Rótulo amarillo con el criterio de la rúbrica que responde la slide."""
    ancho = 0.15 + 0.098 * len(t)
    caja(s, x, y, ancho, 0.34, color=AMARILLO, forma=MSO_SHAPE.ROUNDED_RECTANGLE, radio=0.5, nombre="Rótulo: " + t)
    texto(s, x, y, ancho, 0.34, t.upper(), size=11, color=OSCURO, fuente=KICKER, align=PP_ALIGN.CENTER,
          ancla=MSO_ANCHOR.MIDDLE, nombre="Rótulo de sección")


def titulo(s, t, x=0.7, y=0.45, w=11.9, h=1.2, size=38, color=VERDE, rotulo=None):
    if rotulo:
        kicker(s, rotulo, x=x)
        y, size = 0.66, min(size, 30)
    return texto(s, x, y, w, h, t, size=size, color=color, fuente=TITULO, nombre="Título", interlineado=0.95,
                 ancla=MSO_ANCHOR.TOP)


def deco(s, nombre, x, y, w=None, h=None, rot=0):
    return imagen(s, REC / f"{nombre}.png", x, y, w=w, h=h, nombre="Decoración: " + nombre, rot=rot)


def polaroid(s, ruta, x, y, w, h, rot=0, pie=None, nombre="Polaroid"):
    """Marco tipo Polaroid: papel blanco con sombra y la foto dentro (editable)."""
    marco = caja(s, x, y, w, h + (0.42 if pie else 0.3), color="F4F3EC", sombrea=True, nombre=nombre, rot=rot)
    foto = imagen_recorte(s, ruta, x + 0.1, y + 0.1, w - 0.2, h - 0.1 + 0.0, nombre=nombre + " (imagen)", rot=rot)
    foto.height = Inches(h - 0.1)
    if pie:
        texto(s, x + 0.1, y + h + 0.08, w - 0.2, 0.3, pie, size=12, color=OSCURO, align=PP_ALIGN.CENTER,
              nombre=nombre + " (pie)")
    return marco, foto


def etiqueta(s, t, x, y, w, h=0.38, color=CLARO, texto_color=OSCURO, size=13, punteada=False):
    f = caja(s, x, y, w, h, color=color, forma=MSO_SHAPE.ROUNDED_RECTANGLE, radio=0.5, nombre="Etiqueta: " + t)
    if punteada:
        f.fill.background()
        f.line.color.rgb = rgb(VERDE)
        f.line.width = Pt(1.5)
        f.line.dash_style = 4
    tf = f.text_frame
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = t
    r.font.size, r.font.bold, r.font.name = Pt(size), True, CUERPO
    r.font.color.rgb = rgb(texto_color)
    return f


def pendiente(s, t, x, y, w):
    return etiqueta(s, t, x, y, w, color=None, size=12, punteada=True)


def notas(s, t):
    s.notes_slide.notes_text_frame.text = t


def grafico_barras(s, x, y, w, h, categorias, series, colores, titulo_g=None, maximo=100, horizontal=False,
                   formato='0"%"', leyenda=True, tam=13, hueco=60):
    cd = CategoryChartData()
    cd.categories = categorias
    for nombre, vals in series:
        cd.add_series(nombre, vals)
    tipo = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    gf = s.shapes.add_chart(tipo, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.font.size, ch.font.name = Pt(tam), CUERPO
    ch.font.color.rgb = rgb(OSCURO)
    ch.has_title = bool(titulo_g)
    if titulo_g:
        ch.chart_title.text_frame.text = titulo_g
        r = ch.chart_title.text_frame.paragraphs[0].runs[0]
        r.font.size, r.font.bold, r.font.name = Pt(tam + 1), True, CUERPO
        r.font.color.rgb = rgb(OSCURO)
    ch.has_legend = leyenda and len(series) > 1
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.BOTTOM
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(tam)
    va, ca = ch.value_axis, ch.category_axis
    va.maximum_scale, va.minimum_scale = maximo, 0
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("D9D9CF")
    va.major_gridlines.format.line.width = Pt(0.5)
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(tam - 1)
    va.tick_labels.number_format = formato
    va.tick_labels.number_format_is_linked = False
    ca.format.line.color.rgb = rgb(OSCURO)
    ca.tick_labels.font.size = Pt(tam)
    ca.has_major_gridlines = False
    plot = ch.plots[0]
    plot.gap_width = hueco
    plot.overlap = -5 if len(series) > 1 else 0
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = formato, False
    dl.font.size, dl.font.bold = Pt(tam), True
    dl.font.color.rgb = rgb(OSCURO)
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    for i, ser in enumerate(plot.series):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(colores[i % len(colores)])
        ser.invert_if_negative = False
    gf.name = "Gráfico: " + (titulo_g or "barras")
    return gf


def grafico_lineas(s, x, y, w, h, categorias, series, colores, titulo_g, minimo=30, maximo=48, tam=13):
    cd = CategoryChartData()
    cd.categories = categorias
    for nombre, vals in series:
        cd.add_series(nombre, vals)
    gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.font.size, ch.font.name = Pt(tam), CUERPO
    ch.font.color.rgb = rgb(OSCURO)
    ch.has_title = True
    ch.chart_title.text_frame.text = titulo_g
    r = ch.chart_title.text_frame.paragraphs[0].runs[0]
    r.font.size, r.font.bold, r.font.name = Pt(tam + 1), True, CUERPO
    r.font.color.rgb = rgb(OSCURO)
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.BOTTOM
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(tam)
    va = ch.value_axis
    va.minimum_scale, va.maximum_scale = minimo, maximo
    va.major_unit = 5
    va.major_gridlines.format.line.color.rgb = rgb("D9D9CF")
    va.format.line.fill.background()
    va.tick_labels.number_format, va.tick_labels.number_format_is_linked = '0"%"', False
    va.tick_labels.font.size = Pt(tam - 1)
    ch.category_axis.tick_labels.font.size = Pt(tam)
    plot = ch.plots[0]
    plot.has_data_labels = True
    plot.data_labels.number_format, plot.data_labels.number_format_is_linked = '0.0', False
    plot.data_labels.font.size, plot.data_labels.font.bold = Pt(tam), True
    plot.data_labels.position = XL_LABEL_POSITION.ABOVE
    for i, ser in enumerate(plot.series):
        ser.format.line.color.rgb = rgb(colores[i])
        ser.format.line.width = Pt(3)
        ser.smooth = False
        ser.marker.format.fill.solid()
        ser.marker.format.fill.fore_color.rgb = rgb(colores[i])
        ser.marker.format.line.color.rgb = rgb(colores[i])
        ser.marker.size = 9
    plot.series[1].data_labels.position = XL_LABEL_POSITION.BELOW
    gf.name = "Gráfico: " + titulo_g
    return gf


def numero_grande(s, x, y, w, valor, pie, color=VERDE, tam=64, pie_tam=15, ancho_pie=None):
    texto(s, x, y, w, 1.0, valor, size=tam, color=color, fuente=TITULO, nombre="Cifra " + valor)
    texto(s, x, y + tam / 72 * 1.08, ancho_pie or w, 0.8, pie, size=pie_tam, color=OSCURO, nombre="Pie de cifra")


# =========================================================================== 1 PORTADA
s = prs.slides.add_slide(VACIO)
fondo(s)
deco(s, "deco_estrellas", 0.25, 0.3, w=0.75)
deco(s, "deco_rayitas", 6.9, 0.7, w=1.1, rot=8)
texto(s, 0.85, 0.95, 7.8, 2.6, "FROG", size=170, color=VERDE, fuente=TITULO, nombre="Título", ancla=MSO_ANCHOR.TOP)
bloque = caja(s, 0.85, 3.75, 7.55, 0.95, color=AMARILLO, nombre="Bloque amarillo")
texto(s, 1.1, 3.75, 7.1, 0.95, "Friendly Rounds Of Generation", size=33, color=OSCURO, fuente=TITULO,
      ancla=MSO_ANCHOR.MIDDLE, nombre="Subtítulo")
texto(s, 0.85, 4.95, 7.6, 0.8, "Portadas infantiles generativas con feedback humano: de un boceto y una historia "
      "a cinco propuestas.", size=17, nombre="Descripción")
texto(s, 0.85, 5.8, 7.6, 0.8, ["Andrea Coa · Jimena Gurbillon · Maria Surco", "Bihonda Epiquien · Nayeli Guzman"],
      size=15, negrita=True, color=VERDE, nombre="Integrantes", espacio=2)
texto(s, 0.85, 6.7, 7.8, 0.4, "Proyecto 2 · Planificación y Toma de Decisiones en IA · UTEC · Noviembre 2026", size=13, nombre="Curso")
imagen(s, REC / "runa_saluda_grande.png", 8.55, 0.7, h=5.4, nombre="Runa saluda")
imagen(s, REC / "papel_amarillo.png", 8.95, 5.95, w=4.1, nombre="Rótulo de papel amarillo", rot=-3)
tb = texto(s, 9.05, 6.0, 3.9, 0.7, "Runa", size=40, color=VERDE, fuente=TITULO, align=PP_ALIGN.CENTER,
           ancla=MSO_ANCHOR.MIDDLE, nombre="Nombre de la mascota")
tb.rotation = -3
tb = texto(s, 9.05, 6.62, 3.9, 0.35, "la mascota de FROG", size=14, color=OSCURO, fuente=KICKER,
           align=PP_ALIGN.CENTER, nombre="Rol de la mascota")
tb.rotation = -3
notas(s, "TIEMPO: 0:30. Buenas tardes. Somos el equipo de FROG, que significa Friendly Rounds Of Generation: rondas "
         "amigables de generación. FROG convierte un boceto y una historia en cinco portadas para un libro infantil, "
         "y aprende de lo que la persona acepta y rechaza. La mascota es Runa, que nos acompaña en la presentación.")

# =========================================================================== 2 PROBLEMA
s = prs.slides.add_slide(VACIO)
fondo(s)
deco(s, "deco_estrellas", 0.35, 0.4, w=1.0)
titulo(s, "Quien escribe un cuento no siempre puede ilustrarlo", x=1.45, w=7.0, size=30, rotulo="Problemática")
y0 = 1.95
for ico, linea in (("ico_lapiz", "No sabe dibujar bien: hace dibujos simples, pero sabe lo que quiere contar."),
                   ("ico_informe", "No puede pagar un ilustrador por cada cuento que escribe para su aula."),
                   ("ico_imagenes", "Las IA que probó dieron imágenes que no se parecían a su idea ni a su historia, "
                                    "con el título mal escrito.")):
    imagen(s, REC / f"{ico}.png", 0.85, y0, h=0.62, nombre="Icono")
    texto(s, 1.8, y0 - 0.03, 6.6, 1.0, linea, size=19, ancla=MSO_ANCHOR.MIDDLE, nombre="Problema")
    y0 += 1.05
texto(s, 0.85, 5.2, 7.6, 0.9, [[("¿Por qué IA? ", {"negrita": True, "color": VERDE}),
                                 ("Genera cinco opciones comparables y aprende de lo que la persona elige, con seis "
                                  "parámetros que ella controla.", {})]], size=16, nombre="Por qué IA")
texto(s, 0.85, 6.2, 7.6, 0.5, [[("Carmen, 34 años, docente de inicial", {"negrita": True, "color": VERDE}),
                                (" · proto-persona del caso de uso", {})]], size=15, nombre="Quién es Carmen")
pendiente(s, "Hipótesis previa: las 5 entrevistas aún no se hacen", 0.85, 6.7, 5.8)
caja(s, 8.65, 0.0, 4.68, 7.5, color=AMARILLO, nombre="Bloque amarillo")
polaroid(s, ASS.parent.parent / "codigo" / "app" / "ejemplos" / "boceto_conejo.png", 8.95, 0.7, 2.3, 2.3, rot=-4,
         pie="Su dibujo")
polaroid(s, DEMO / "R1-V1.png", 10.6, 3.05, 2.25, 3.0, rot=3, pie="Una de las 5 portadas")
imagen(s, REC / "runa_lee.png", 8.85, 5.35, h=1.75, nombre="Runa lee")
notas(s, "TIEMPO: 0:45. Diseñamos para Carmen, una docente de inicial que escribe cuentos para su aula. Sabe lo que "
         "quiere contar pero no sabe dibujar, no puede pagar un ilustrador por cada cuento, y las herramientas de IA "
         "genéricas le dan imágenes que no se parecen a su idea y con el título mal escrito. Aclaración honesta: Carmen "
         "es una hipótesis de diseño que construimos antes de las entrevistas; las cinco entrevistas con consentimiento "
         "están pendientes, por eso aquí no hay citas.")

# =========================================================================== 3 FLUJO
s = prs.slides.add_slide(VACIO)
fondo(s)
titulo(s, "La solución: de un boceto y una historia a cinco portadas", x=0.7, w=11.0, size=30,
       rotulo="Solución técnica · visión general")
deco(s, "deco_estrellas", 12.0, 0.45, w=0.9)
etapas = [("Tu boceto y tu historia", "Dibujas o subes un boceto y cuentas el cuento.", "ico_libro"),
          ("Cinco propuestas", "Cada una cambia solo un parámetro.", "ico_imagenes"),
          ("Aceptar o rechazar", "Con motivo, por portada o por paquete.", "ico_pulgar_arriba"),
          ("Planificador", "Aprende qué valores prefieres.", "ico_grafico"),
          ("Resumen final", "Un agente explica lo que pasó.", "ico_informe")]
ancho, sep, x0 = 2.1, 0.45, 0.7
for i, (t, d, ico) in enumerate(etapas):
    x = x0 + i * (ancho + sep)
    caja(s, x, 1.95, ancho, 3.35, color=BLANCO, linea=VERDE, grosor=2, forma=MSO_SHAPE.ROUNDED_RECTANGLE,
         sombrea=True, radio=0.08, nombre=f"Etapa {i + 1}")
    caja(s, x + 0.12, 2.07, 0.42, 0.42, color=AMARILLO, forma=MSO_SHAPE.OVAL, nombre="Número")
    texto(s, x + 0.12, 2.07, 0.42, 0.42, str(i + 1), size=16, fuente=TITULO, align=PP_ALIGN.CENTER,
          ancla=MSO_ANCHOR.MIDDLE, nombre="Número de etapa")
    imagen(s, REC / f"{ico}.png", x + ancho - 0.95, 2.05, h=0.7, nombre="Icono de etapa")
    texto(s, x + 0.15, 3.0, ancho - 0.3, 0.7, t, size=18, negrita=True, color=VERDE, nombre="Etapa")
    texto(s, x + 0.15, 3.65, ancho - 0.3, 0.9, d, size=14, nombre="Descripción")
    if i < len(etapas) - 1:
        imagen(s, REC / "flecha_recta.png", x + ancho + 0.03, 3.55, w=sep - 0.06, nombre="Flecha")
# miniaturas reales dentro de las etapas 1 y 2
imagen_recorte(s, ASS.parent.parent / "codigo" / "app" / "ejemplos" / "boceto_conejo.png", x0 + 0.25, 4.45, 1.0, 0.75,
               nombre="Boceto de ejemplo")
for k in range(5):
    imagen_recorte(s, DEMO / f"R1-V{k + 1}.png", x0 + ancho + sep + 0.14 + k * 0.38, 4.45, 0.34, 0.75,
                   nombre=f"Portada {k + 1}")
# bucle de rondas
imagen(s, REC / "ico_ronda.png", 3.4, 5.78, h=0.8, nombre="Icono de ronda")
texto(s, 4.35, 5.8, 6.4, 0.9, [[("Hasta 3 rondas. ", {"negrita": True, "color": VERDE}),
                                 ("Lo que aceptas y rechazas define la siguiente ronda.", {})]], size=19,
      ancla=MSO_ANCHOR.MIDDLE, nombre="Rondas")
imagen(s, REC / "runa_dibuja.png", 11.1, 5.35, h=1.9, nombre="Runa dibuja")
notas(s, "TIEMPO: 0:45. El flujo completo: la persona sube o dibuja un boceto y cuenta su historia; el sistema genera "
         "exactamente cinco portadas, donde cada una cambia un solo parámetro; la persona acepta o rechaza cada una, con "
         "el motivo; un planificador usa esas decisiones para proponer la siguiente ronda, hasta un máximo de tres; y al "
         "final un agente redacta un resumen de lo que ocurrió, que se verifica contra el registro.")

# =========================================================================== 3b ARQUITECTURA
s = prs.slides.add_slide(VACIO)
fondo(s)
titulo(s, "Arquitectura: siete componentes y un registro de cada decisión", x=0.7, w=11.0, size=30,
       rotulo="Solución técnica · arquitectura")
deco(s, "deco_estrellas", 12.1, 0.3, w=0.8)
imagen(s, ASS / "arquitectura.png", 0.65, 1.75, w=12.0, nombre="Diagrama de arquitectura")
texto(s, 0.6, 6.35, 10.2, 0.8, "Los rombos son decisiones. La flecha punteada de arriba es el rechazo de la entrada por los "
      "guardrails; si el resumen del LLM no coincide con el registro, se reintenta (máx. 2) y luego se usa una plantilla.",
      size=14, nombre="Cómo leer el diagrama")
imagen(s, REC / "runa_lupa.png", 11.4, 6.1, h=1.2, nombre="Runa con lupa")
notas(s, "TIEMPO: 1:00. La arquitectura completa. 1) Preprocesamiento, guardrails de entrada y agente de historia: se "
         "rechaza un boceto vacío, una foto de una persona real o texto no apto. 2) El planificador propone las cinco "
         "configuraciones con Thompson. 3) El motor A o el B genera las portadas. 4) Guardrails de salida, agente "
         "tipográfico y render del título. 5) La interfaz: aceptar o rechazar con motivo y editar la fuente. 6) Todo "
         "queda en un registro JSON. Si hay otra ronda, se actualizan las preferencias y se vuelve al planificador; "
         "si no, 7) el agente LLM redacta el resumen y un validador lo compara con el registro, con hasta dos "
         "reintentos y una plantilla de respaldo.")

# =========================================================================== 4 PARÁMETROS
s = prs.slides.add_slide(VACIO)
fondo(s)
titulo(s, "Personalización: seis parámetros y un planificador que aprende", x=0.7, w=7.8, size=30,
       rotulo="Solución técnica · personalización")
params = [("Estilo", "acuarela · lápices · collage · vectorial · plastilina"),
          ("Paleta", "pastel · cálida · fría · primarios · tierra"),
          ("Edad", "0-3 · 4-6 · 7-9 · 10-12 · sin"),
          ("Ambiente", "alegre · aventura · calma · misterio · humor"),
          ("Fidelidad al boceto", "muy baja · baja · media · alta · muy alta"),
          ("Zona del título", "superior · inferior · ambas · centrada · sin")]
for i, (n, v) in enumerate(params):
    x = 0.7 + (i % 2) * 3.95
    y = 1.8 + (i // 2) * 1.5
    caja(s, x, y, 3.75, 1.3, color=BLANCO, linea=CLARO, grosor=3, forma=MSO_SHAPE.ROUNDED_RECTANGLE, radio=0.1,
         sombrea=True, nombre=f"Parámetro {n}")
    texto(s, x + 0.2, y + 0.13, 3.35, 0.4, n, size=20, color=VERDE, fuente=TITULO, nombre="Parámetro")
    texto(s, x + 0.2, y + 0.62, 3.35, 0.6, v, size=14, nombre="Valores")
texto(s, 0.7, 6.4, 7.7, 0.7, [[("Una ronda: ", {"negrita": True, "color": VERDE}),
                                ("un parámetro toma sus 5 valores (una portada por valor) y los otros cinco quedan fijos.",
                                 {})]], size=16, nombre="Cómo funciona una ronda")
caja(s, 8.75, 0.0, 4.58, 7.5, color=AMARILLO, nombre="Bloque amarillo")
texto(s, 9.1, 0.75, 3.9, 0.9, "El planificador aprende de tus decisiones", size=25, color=VERDE, fuente=TITULO,
      nombre="Planificador")
paso = [("1", "Cada aceptación o rechazo actualiza qué valores prefieres."),
        ("2", "Los parámetros con evidencia se fijan en lo que aceptaste."),
        ("3", "Los demás se eligen al azar para seguir explorando."),
        ("4", "Máximo tres rondas por sesión.")]
for i, (n, t) in enumerate(paso):
    y = 2.0 + i * 0.95
    caja(s, 9.1, y, 0.45, 0.45, color=VERDE, forma=MSO_SHAPE.OVAL, nombre="Número")
    texto(s, 9.1, y, 0.45, 0.45, n, size=16, color=BLANCO, fuente=TITULO, align=PP_ALIGN.CENTER,
          ancla=MSO_ANCHOR.MIDDLE, nombre="Número")
    texto(s, 9.75, y - 0.04, 3.2, 0.85, t, size=15, nombre="Paso del planificador")
texto(s, 9.1, 5.75, 3.9, 0.4, "Muestreo de Thompson", size=15, negrita=True, color=VERDE, nombre="Método")
imagen(s, REC / "runa_piensa.png", 10.9, 5.95, h=1.45, nombre="Runa piensa")
notas(s, "TIEMPO: 0:45. La persona controla seis parámetros: estilo, paleta, edad, ambiente, fidelidad al boceto y zona "
         "del título. En cada ronda uno de ellos varía entre las cinco portadas y los otros quedan fijos, para que se "
         "entienda qué cambió. El planificador usa muestreo de Thompson: va aprendiendo qué valores prefiere la persona "
         "según lo que acepta, fija esos y explora al azar los demás, hasta un máximo de tres rondas.")

# =========================================================================== 5 MOTORES
s = prs.slides.add_slide(VACIO)
fondo(s)
titulo(s, "Dos motores: el A reinterpreta el boceto, el B lo conserva", x=0.7, w=11.0, size=30,
       rotulo="Solución técnica · modelo generativo")
deco(s, "deco_estrellas", 12.1, 0.3, w=0.8)
# láminas sin la fila de rótulos diminutos; los estilos se rotulan con texto editable
for nom in ("lamina_motor_a", "lamina_motor_b"):
    destino = ASS / f"{nom}_recortada.png"
    if not destino.exists():
        Image.open(ASS.parent / f"{nom}.png").convert("RGB").crop((0, 38, 1606, 444)).save(destino)
ESC = 8.0 / 1606                      # pulgadas por píxel de la lámina
estilos = ["acuarela", "lápices", "collage", "vectorial", "plastilina"]
for k, e in enumerate(estilos):
    cx = 0.65 + (404 + k * 266) * ESC
    texto(s, cx - 0.8, 1.35, 1.6, 0.3, e, size=14, negrita=True, color=VERDE, align=PP_ALIGN.CENTER,
          nombre="Estilo " + e)
texto(s, 0.65, 1.35, 1.2, 0.3, "Boceto", size=14, negrita=True, color=VERDE, align=PP_ALIGN.CENTER, nombre="Rótulo boceto")
for k, (img, lab, y) in enumerate((("lamina_motor_a", "Motor A", 1.85), ("lamina_motor_b", "Motor B", 4.3))):
    caja(s, 0.55, y, 8.2, 2.2, color="F4F3EC", sombrea=True, nombre=f"Marco {lab}")
    imagen(s, ASS / f"{img}_recortada.png", 0.65, y + 0.1, w=8.0, nombre=f"Lámina {lab}")
    etiqueta(s, lab, 0.62, y - 0.2, 1.15, color=AMARILLO if k == 0 else CLARO, size=14)
texto(s, 0.6, 6.7, 8.2, 0.5, "Mismo boceto e historia; una ronda con el eje estilo.", size=13, cursiva=True,
      nombre="Pie de las láminas")
x = 9.35
caja(s, x, 1.85, 3.45, 2.2, color=AMARILLO, nombre="Bloque motor A")
texto(s, x + 0.25, 1.95, 3.0, 0.45, "Motor A", size=24, color=VERDE, fuente=TITULO, nombre="Motor A")
texto(s, x + 0.25, 2.5, 3.0, 1.5, ["Stable Diffusion 1.5 con ControlNet", "93 % de acierto de estilo",
                                    "7,8 s por ronda"], size=16, espacio=4, nombre="Datos motor A")
caja(s, x, 4.3, 3.45, 2.2, color=CLARO, nombre="Bloque motor B")
texto(s, x + 0.25, 4.4, 3.0, 0.45, "Motor B", size=24, color=VERDE, fuente=TITULO, nombre="Motor B")
texto(s, x + 0.25, 4.95, 3.0, 1.5, ["SD-Turbo (img2img)", "98 % de fidelidad al boceto",
                                     "1,6 s por ronda, pero solo 20 % de acierto de estilo"], size=16, espacio=4,
      nombre="Datos motor B")
notas(s, "TIEMPO: 0:45. Usamos dos motores gratuitos en Colab. El A, Stable Diffusion con ControlNet, reinterpreta el "
         "boceto en cada estilo: 93 % de acierto de estilo, 7,8 segundos por ronda. El B, SD-Turbo, es cinco veces más "
         "rápido y casi copia el dibujo (98 % de fidelidad), pero por eso los cinco estilos apenas se distinguen: "
         "solo 20 % de acierto. Por eso A es el principal y B queda como respaldo y línea base.")

# =========================================================================== 6 AGENTES
s = prs.slides.add_slide(VACIO)
fondo(s)
titulo(s, "Tres agentes de IA, cada uno con su validador", x=0.7, w=10.5, size=30,
       rotulo="Solución técnica · agentes de IA")
deco(s, "deco_espiral", 11.1, 0.75, w=1.6)
cols = [("Agente de historia", "ico_libro",
         "Entra: “Un conejo que ama las flores y las cuida durante el invierno”",
         '{"personajes":["conejo"],\n "objetos":["flores"],\n "lugar":"jardin"}',
         "Cada personaje y objeto debe aparecer en el texto; lo que no aparece se marca."),
        ("Agente tipográfico", "ico_lupa",
         "Entra: medidas de la zona del título (contraste, bordes, color)",
         None,
         "Un renderizador determinista dibuja las letras: el título siempre sale correcto y con límites por edad."),
        ("Agente de resumen", "ico_informe",
         "Entra: el registro JSON de la sesión",
         "Ronda 1 (eje: Paleta)\nAceptadas: R1-V3 (fría)\nRechazadas: R1-V1 (pastel; motivo: colores)",
         "Contrasta IDs, motivos y parámetros con el registro; si falla, reintenta y luego usa una plantilla.")]
for i, (n, ico, entra, sale, valida) in enumerate(cols):
    x = 0.7 + i * 4.1
    caja(s, x, 1.75, 3.85, 5.15, color=BLANCO, linea=VERDE, grosor=2, forma=MSO_SHAPE.ROUNDED_RECTANGLE, radio=0.05,
         sombrea=True, nombre=n)
    imagen(s, REC / f"{ico}.png", x + 0.2, 1.9, h=0.6, nombre="Icono")
    texto(s, x + 1.2, 1.95, 2.55, 0.55, n, size=19, color=VERDE, fuente=TITULO, ancla=MSO_ANCHOR.MIDDLE,
          nombre="Agente")
    texto(s, x + 0.2, 2.7, 3.45, 0.85, entra, size=14, nombre="Entrada")
    if sale:
        caja(s, x + 0.2, 3.65, 3.45, 1.5, color="F1F6EA", forma=MSO_SHAPE.ROUNDED_RECTANGLE, radio=0.06,
             nombre="Salida")
        texto(s, x + 0.32, 3.72, 3.25, 1.4, sale.split("\n"), size=13, fuente=CODIGO, ancla=MSO_ANCHOR.MIDDLE,
              nombre="Salida del agente")
    else:
        imagen(s, ASS / "titulo_agente_conejo.png", x + 0.2, 3.65, w=3.45, nombre="Título del agente tipográfico")
    texto(s, x + 0.2, 5.4, 3.45, 0.3, "Validador", size=14, negrita=True, color=VERDE, nombre="Validador")
    texto(s, x + 0.2, 5.72, 3.45, 1.1, valida, size=14, nombre="Qué valida")
notas(s, "TIEMPO: 1:00. Hay tres agentes y ninguno recibe imágenes. El de historia lee el texto y extrae personajes, "
         "objetos y lugar; un verificador comprueba que cada elemento aparezca en la historia. El tipográfico recibe "
         "medidas de la zona del título y propone fuente y color; las letras las dibuja siempre un renderizador "
         "determinista, así el título nunca sale mal escrito. El de resumen redacta lo ocurrido a partir del registro y "
         "un validador contrasta cada ID y motivo con ese registro. Los modelos son Qwen 2.5 y Phi 3.5, que corren "
         "dentro de la sesión de Colab.")

# =========================================================================== 7 DEMO
s = prs.slides.add_slide(VACIO)
fondo(s)
deco(s, "deco_explosion", 11.3, 0.1, w=1.7)
titulo(s, "Demostración: de una idea a una portada", x=0.7, w=7.4, size=34, rotulo="Demostración en vivo")
etiqueta(s, "5 minutos", 0.75, 2.0, 1.7, h=0.42, color=AMARILLO, size=15)
pasos = [("ico_lapiz", "Dibujar o subir el boceto"), ("ico_libro", "Contar la historia y revisar los elementos"),
         ("ico_imagenes", "Generar las 5 portadas"), ("ico_pulgar_arriba", "Aceptar o rechazar, con motivo"),
         ("ico_ronda", "Segunda ronda guiada por tus decisiones"), ("ico_informe", "Leer el resumen del agente")]
for i, (ico, t) in enumerate(pasos):
    y = 2.7 + i * 0.7
    caja(s, 0.75, y + 0.04, 0.5, 0.5, color=VERDE, forma=MSO_SHAPE.OVAL, nombre="Número")
    texto(s, 0.75, y + 0.04, 0.5, 0.5, str(i + 1), size=16, color=BLANCO, fuente=TITULO, align=PP_ALIGN.CENTER,
          ancla=MSO_ANCHOR.MIDDLE, nombre="Número")
    imagen(s, REC / f"{ico}.png", 1.5, y, h=0.58, nombre="Icono de paso")
    texto(s, 2.7, y, 5.3, 0.58, t, size=18, ancla=MSO_ANCHOR.MIDDLE, nombre="Paso")
polaroid(s, ASS.parent.parent / "codigo" / "app" / "ejemplos" / "boceto_conejo.png", 8.3, 2.3, 2.1, 2.1, rot=-3,
         pie="Boceto")
polaroid(s, DEMO / "R1-V1.png", 10.7, 1.75, 1.95, 2.25, rot=3, pie="Propuesta")
polaroid(s, DEMO / "R1-V4.png", 11.1, 4.85, 1.75, 1.95, rot=-2, pie="Propuesta")
imagen(s, REC / "runa_dibuja.png", 8.6, 5.1, h=2.1, nombre="Runa dibuja")
notas(s, "TIEMPO: 5:00 (demostración en vivo). Recorrido: 1) subo o dibujo un boceto; 2) cuento la historia y el agente "
         "extrae los personajes, objetos y lugar, que puedo corregir; 3) se generan las cinco portadas, cada una con "
         "su etiqueta del valor que cambia; 4) acepto o rechazo cada una y, si rechazo, marco el motivo; 5) genero una "
         "segunda ronda y se ve que el planificador aprendió; 6) termino y leo el resumen que redactó el agente. "
         "También muestro un guardrail: un texto bloqueado. Plan B: si Colab tarda, tener una ronda ya generada.")

# =========================================================================== 8 SEGURIDAD
s = prs.slides.add_slide(VACIO)
fondo(s)
titulo(s, "Ética: cuatro capas de seguridad y sus fallos", x=0.7, w=10.5, size=32, rotulo="Aspectos éticos")
imagen(s, REC / "ico_escudo.png", 11.7, 0.35, h=0.95, nombre="Escudo")
compuertas = [("Texto", "Lista de bloqueo de violencia, contenido sexual, artistas y personajes con marca."),
              ("Foto", "Solo dibujos: se rechaza toda foto con el rostro de una persona."),
              ("Imagen", "CLIP compara cada portada con descriptores de contenido no apto para niños."),
              ("Derechos", "Estilos genéricos y aviso de que la protección de autor no está garantizada.")]
for i, (n, d) in enumerate(compuertas):
    x = 0.7 + i * 3.1
    caja(s, x, 1.65, 2.95, 2.2, color=BLANCO, linea=VERDE, grosor=2, forma=MSO_SHAPE.ROUNDED_RECTANGLE, radio=0.07,
         sombrea=True, nombre="Compuerta " + n)
    caja(s, x + 0.15, 1.8, 0.45, 0.45, color=AMARILLO, forma=MSO_SHAPE.OVAL, nombre="Número")
    texto(s, x + 0.15, 1.8, 0.45, 0.45, str(i + 1), size=16, fuente=TITULO, align=PP_ALIGN.CENTER,
          ancla=MSO_ANCHOR.MIDDLE, nombre="Número")
    texto(s, x + 0.75, 1.8, 2.0, 0.45, n, size=22, color=VERDE, fuente=TITULO, ancla=MSO_ANCHOR.MIDDLE, nombre="Nombre")
    texto(s, x + 0.2, 2.5, 2.6, 1.3, d, size=15, nombre="Descripción")
caja(s, 0.7, 4.2, 12.15, 2.8, color=AMARILLO, nombre="Bloque de resultados")
texto(s, 1.05, 4.3, 3.6, 1.2, "20 / 20", size=70, color=VERDE, fuente=TITULO, nombre="Cifra")
texto(s, 1.05, 5.6, 3.5, 1.2, "entradas adversariales bloqueadas por el filtro de texto", size=16, nombre="Pie de cifra")
texto(s, 5.0, 4.5, 7.6, 2.4, [[("1 de 5 ", {"negrita": True, "color": VERDE}),
                                ("entradas legítimas bloqueada por error (un nombre con marca).", {})],
                               [("5 de 5 ", {"negrita": True, "color": VERDE}),
                                ("evasiones con eufemismos pasan el filtro de texto; por eso existe el filtro de imagen.", {})],
                               [("Motor B: ", {"negrita": True, "color": VERDE}),
                                ("SD-Turbo no trae filtro propio; solo lo protege CLIP.", {})]],
      size=18, espacio=10, nombre="Resultados de seguridad")
notas(s, "TIEMPO: 0:45. Hay cuatro capas: texto, foto, imagen y derechos. En E5 probamos 30 entradas: el filtro de texto "
         "bloqueó las 20 que debía bloquear y se equivocó con 1 de 5 legítimas, por un nombre con marca. Las evasiones "
         "con eufemismos, como un perro herido sangrando, pasan el filtro de texto, por eso la imagen se revisa con CLIP. "
         "Un punto importante: el motor B, SD-Turbo, no trae filtro de seguridad propio; ahí CLIP es la única protección.")

# =========================================================================== 9 CALIDAD E1
s = prs.slides.add_slide(VACIO)
fondo(s)
titulo(s, "Calidad visual: el estilo cumple y la paleta llega al 79 %", x=0.7, w=10.4, size=30,
       rotulo="Evaluación · calidad visual")
imagen(s, REC / "runa_lupa.png", 11.35, 0.3, h=1.35, nombre="Runa con lupa")
grafico_barras(s, 0.6, 1.75, 6.4, 4.7, ["Estilo", "Paleta", "Elemento\nprincipal", "Fidelidad\nal boceto"],
               [("Motor A", [93.2, 69.7, 90.8, 28.3]), ("Motor B", [20.1, 83.8, 89.6, 97.7])], [VERDE, AMARILLO],
               titulo_g="Métricas de E1 por motor (3 000 portadas)", formato='0"%"', maximo=112)
grafico_barras(s, 7.1, 1.75, 5.7, 4.7, ["Pastel", "Fría", "Tierra", "Cálida", "Primarios"],
               [("Original", [100, 100, 93.5, 53.5, 1.5]), ("Prompt reforzado", [100, 100, 93.4, 71.5, 31.5])],
               [VERDE, AMARILLO], titulo_g="Motor A: acierto de paleta por tipo", formato='0"%"', maximo=112, tam=10, hueco=25)
texto(s, 0.7, 6.6, 6.3, 0.6, "Criterios: estilo ≥ 70 %, elemento principal ≥ 80 %, paleta ≥ 80 %.", size=14,
      nombre="Criterios")
etiqueta(s, "Paleta global: 69,7 % → 79,2 % (criterio 80 %)", 7.2, 6.62, 5.2, h=0.4, color=CLARO, size=13)
notas(s, "TIEMPO: 0:45. En E1 generamos 3 000 portadas. El motor A cumple estilo (93 % frente al 70 % exigido), elemento "
         "principal (91 %) y latencia, pero no la paleta: 70 % frente al 80 %. El gráfico de la derecha muestra por qué: "
         "pastel, fría y tierra pasan del 93 %, pero 'cálida' llega al 53 % y 'primarios vivos' al 1,5 %. Reforzamos el "
         "texto de esas dos paletas en el prompt y repetimos solo el eje paleta con los mismos 200 pares: sube a 79,2 %, "
         "con cálida en 71,5 % y primarios en 31,5 %; sigue por debajo del 80 %. Aclaración: el refuerzo se decidió "
         "después de ver el resultado y se midió sobre los mismos pares. El motor B gana en paleta y fidelidad al boceto "
         "porque casi lo copia.")

# =========================================================================== 10 RESULTADOS AGENTES
s = prs.slides.add_slide(VACIO)
fondo(s)
titulo(s, "Resultados: Thompson supera al azar en la ronda 3 y el resumen es fiel", x=0.7, w=10.6, size=30,
       rotulo="Evaluación · feedback y agentes")
grafico_lineas(s, 0.5, 1.75, 4.3, 4.3, ["Ronda 1", "Ronda 2", "Ronda 3"],
               [("Thompson", [35.3, 34.9, 43.0]), ("Aleatorio", [35.3, 34.7, 34.8])], [VERDE, "C28F00"],
               "Aceptación media (500 usuarios simulados)", minimo=30, maximo=48, tam=12)
grafico_barras(s, 4.85, 1.75, 3.9, 4.3, ["Qwen 2.5", "Phi 3.5"], [("Resúmenes fieles", [85, 50])], [VERDE],
               titulo_g="Resúmenes fieles al registro", formato='0"%"', leyenda=False, tam=12, maximo=112)
grafico_barras(s, 8.8, 1.75, 3.95, 4.3, ["Por defecto", "Agente"], [("CER", [43.4, 17.6])], [AMARILLO],
               titulo_g="Error por carácter del título (OCR)", maximo=56, formato='0.0"%"', leyenda=False, tam=12)
texto(s, 0.6, 6.2, 4.2, 0.9, "Con evidencia de dos rondas, Thompson supera al azar en la ronda 3.", size=14,
      nombre="Lectura Thompson")
texto(s, 4.9, 6.2, 3.8, 0.9, "Comprobación automática contra el registro; la parte interpretativa no se evalúa.", size=14,
      nombre="Lectura resúmenes")
texto(s, 8.85, 6.2, 3.9, 0.9, "Falla con títulos cortos o con un dibujo detrás; criterio: 5 %. Se leen bien a simple "
      "vista.", size=14, nombre="Lectura legibilidad")
imagen(s, REC / "runa_creando.png", 11.5, 0.2, h=1.5, nombre="Runa creando")
notas(s, "TIEMPO: 1:00. Tres resultados. Primero, el planificador: con 500 usuarios simulados, Thompson y el azar empiezan "
         "iguales, pero en la ronda 3, con la evidencia de dos rondas, Thompson llega a 43 % de aceptación frente a 34,8 %. "
         "Segundo, los resúmenes: una comprobación automática contra el registro halló fieles 23 de los 27 de Qwen, 85 %, "
         "y 7 de los 14 de Phi, 50 %; no mide la parte interpretativa. Tercero, la legibilidad del título con OCR: el "
         "agente baja el error de 43 a 17,6 %, sin llegar al 5 %; el error lo concentran títulos cortos o con un dibujo "
         "detrás, y las 20 portadas peor leídas por el OCR se revisaron a mano y se leían sin esfuerzo.")

# =========================================================================== 11 SEGURIDAD, SESGO, USUARIOS
s = prs.slides.add_slide(VACIO)
fondo(s)
titulo(s, "Seguridad y sesgo: 42 de 45 aptas y tendencia a la piel clara", x=0.7, w=11.3, size=30,
       rotulo="Evaluación · seguridad y sesgo")
caja(s, 0.6, 1.8, 4.3, 4.4, color=AMARILLO, nombre="Bloque E5a")
texto(s, 0.9, 1.9, 3.8, 1.2, "42 / 45", size=70, color=VERDE, fuente=TITULO, nombre="Cifra")
texto(s, 0.9, 3.15, 3.8, 0.7, "portadas aptas para niños, según revisión manual", size=15, nombre="Pie de cifra")
texto(s, 0.9, 3.95, 3.8, 2.2, [[("No aptas: ", {"negrita": True, "color": VERDE}),
                                 ("payaso tenebroso, fantasma triste, dragón con miedo a la oscuridad.", {})],
                                [("CLIP con umbral 0,5: ", {"negrita": True, "color": VERDE}), ("detecta 0 de 3 (y 0 de 10 en la calibración).", {})],
                                [("Con umbral 0,25: ", {"negrita": True, "color": VERDE}),
                                 ("detecta 2 de 3 y 5 de 10, y bloquea por error el 1,3 % de las aptas.", {})]],
      size=14, espacio=6, nombre="Detalle E5a")
grafico_barras(s, 5.05, 1.8, 3.9, 4.0, ["Ambiguo", "Femenino", "Masculino"], [("Género percibido", [79, 17, 4])],
               [VERDE], titulo_g="Género percibido (100 imágenes)", maximo=100, formato='0', leyenda=False, tam=12)
grafico_barras(s, 9.05, 1.8, 3.8, 4.0, ["No aplica", "Claro", "Medio", "Oscuro"],
               [("Tono de piel", [80, 17, 3, 0])], [AMARILLO], titulo_g="Tono de piel percibido", maximo=100,
               formato='0', leyenda=False, tam=12)
texto(s, 5.1, 5.95, 6.4, 0.9, "Una persona anotó 100 figuras sin rasgos definidos: cuando el modelo dibuja rasgos, "
      "tiende a la piel clara. Es una observación, no una conclusión.", size=14, nombre="Lectura del sesgo")
pendiente(s, "Estudio con usuarios (E4) y SUS: pendientes", 0.6, 6.55, 4.3)
imagen(s, REC / "runa_piensa.png", 11.85, 5.65, h=1.6, nombre="Runa piensa")
notas(s, "TIEMPO: 0:45. En E5 una persona revisó las 45 portadas generadas con las entradas de prueba: 42 eran aptas y 3 "
         "no. Con el umbral inicial de CLIP, 0,5, no detectó ninguna de las tres; con 0,25 detecta dos, aunque la "
         "calibración es débil porque son solo tres casos. Con 400 portadas más generadas sin filtro, una persona revisó las "
         "25 más sospechosas: 10 no eran aptas, sobre todo dragones del motor B; con 0,25 se detectan 5 de esas 10 y se "
         "bloquean 5 aptas, y con 0,5 no se detecta ninguna. En sesgo, generamos 100 figuras humanas sin rasgos definidos y "
         "una persona anotó género y tono de piel percibidos: casi todo ambiguo, pero cuando hay rasgos tiende a piel "
         "clara y a género femenino, y ninguna imagen salió con tono oscuro. Es una observación con un solo anotador. "
         "El estudio con usuarios, E4, y la escala SUS están pendientes; no los reportamos.")

# =========================================================================== 12 LIMITACIONES
s = prs.slides.add_slide(VACIO)
fondo(s)
titulo(s, "Limitaciones: qué no cumple y por qué", x=0.7, w=9.0, size=32, rotulo="Limitaciones")
imagen(s, REC / "runa_piensa.png", 11.2, 0.3, h=1.85, nombre="Runa piensa")
lim = [("Agente de historia", "59–80 % de precisión", "Meta: 90 %. Mejor caso: Qwen en inglés, 80 % (flexible)."),
       ("Paleta del motor A", "70 % → 79 %", "Meta: 80 %. Tras reforzar el prompt, «primarios» sigue en 31,5 %."),
       ("Legibilidad del título", "CER 17,6 %", "Meta: 5 %. El OCR falla con títulos cortos o con dibujo detrás."),
       ("Filtro de imagen (CLIP)", "5 de 10 no aptas", "Con 0,25 también bloquea el 1,3 % de las aptas; es un filtro débil."),
       ("Evidencia con personas", "Pendiente", "Entrevistas, estudio con usuarios (E4) y SUS aún no se hacen.")]
for i, (n, cifra, d) in enumerate(lim):
    y = 2.4 + i * 0.97
    caja(s, 0.7, y, 11.9, 0.86, color=BLANCO, forma=MSO_SHAPE.ROUNDED_RECTANGLE, radio=0.12, sombrea=True,
         nombre="Limitación " + n)
    caja(s, 0.7, y, 3.5, 0.86, color=AMARILLO if i < 4 else CLARO, forma=MSO_SHAPE.ROUNDED_RECTANGLE, radio=0.12,
         nombre="Etiqueta " + n)
    texto(s, 0.9, y, 3.2, 0.86, n, size=17, color=OSCURO, fuente=TITULO, ancla=MSO_ANCHOR.MIDDLE, nombre="Limitación")
    texto(s, 4.4, y, 2.8, 0.86, cifra, size=19, color=VERDE, fuente=TITULO, ancla=MSO_ANCHOR.MIDDLE, nombre="Cifra")
    texto(s, 7.3, y, 5.2, 0.86, d, size=15, ancla=MSO_ANCHOR.MIDDLE, nombre="Detalle")
notas(s, "TIEMPO: 0:30. Cinco limitaciones, sin esconderlas. El agente de historia no llega al 90 %: queda entre 59 y "
         "80 % según modelo, idioma y tipo de comparación. La paleta del motor A pasó de 70 a 79 % tras reforzar el prompt, "
         "todavía bajo el 80 % pedido. El OCR del título no llega al 5 %. El filtro CLIP se calibró con tres casos. Y nos faltan las "
         "entrevistas, el estudio con usuarios y el SUS.")

# =========================================================================== 13 CONCLUSIONES
s = prs.slides.add_slide(VACIO)
fondo(s)
deco(s, "deco_explosion", 9.9, 0.25, w=2.7)
titulo(s, "Conclusiones: lo logrado y lo que sigue", x=0.7, w=8.5, size=34, rotulo="Conclusiones")
aportes = [("Cinco propuestas comparables", "Cada una cambia un parámetro y se explica qué cambió."),
           ("Decisiones que se aprovechan", "Aceptar y rechazar guía las rondas, con Thompson en hasta tres."),
           ("Agentes que se pueden verificar", "Historia, tipografía y resumen con validadores deterministas."),
           ("Límites de seguridad medidos", "Texto, foto, imagen y derechos, con sus fallos a la vista.")]
for i, (n, d) in enumerate(aportes):
    y = 2.2 + i * 0.95
    imagen(s, REC / "destellos.png", 0.75, y + 0.02, h=0.62, nombre="Destello")
    texto(s, 1.5, y, 7.3, 0.4, n, size=20, color=VERDE, fuente=TITULO, nombre="Aporte")
    texto(s, 1.5, y + 0.42, 7.3, 0.4, d, size=15, nombre="Descripción del aporte")
texto(s, 0.75, 6.0, 7.4, 1.0, [[("Siguiente: ", {"negrita": True, "color": VERDE}),
                                  ("entrevistas, estudio con usuarios y SUS, y un filtro de imagen más fuerte, sobre "
                                   "todo para el motor B.", {})]], size=16, nombre="Próximos pasos")
imagen(s, REC / "runa_celebra.png", 8.85, 2.75, w=4.2, nombre="Runa celebra")
texto(s, 8.6, 6.3, 4.4, 0.5, "Gracias · ¿preguntas?", size=18, color=VERDE, fuente=TITULO,
      align=PP_ALIGN.CENTER, nombre="Cierre")
notas(s, "TIEMPO: 0:30. En resumen: FROG genera cinco portadas comparables a partir del boceto y la historia, usa "
         "las decisiones de la persona para guiar las rondas, tiene agentes cuyo trabajo se puede verificar y límites de "
         "seguridad cuyos fallos medimos. Lo que sigue: entrevistas, estudio con usuarios y SUS, y un filtro de imagen "
         "más fuerte, sobre todo para el motor B. Gracias. TIEMPO TOTAL APROXIMADO: 14 min 45 s con la demostración de 5 min.")

PREGUNTAS = {
    2: "¿Cómo saben que la necesidad es real? Carmen es una hipótesis de diseño; las cinco entrevistas están "
       "pendientes, así que no afirmamos evidencia de campo. ¿Por qué IA y no un ilustrador? No lo reemplaza: entrega "
       "un concepto de portada con cinco opciones comparables a partir del dibujo de la persona.",
    4: "¿Qué evita que el LLM invente? Un validador compara cada ID y motivo del resumen con el registro y reintenta "
       "hasta dos veces; si falla, usa una plantilla. ¿Qué conecta todo? El registro JSON de cada decisión.",
    5: "¿Por qué Thompson? Equilibra explorar y aprovechar con pocas rondas (máximo 3). En simulación supera al azar en "
       "la ronda 3 (43 % frente a 34,8 %); con usuarios reales todavía no está probado.",
    6: "¿Por qué dos motores? El A reinterpreta el estilo (93 %) y el B es muy rápido pero copia el boceto (20 % de "
       "estilo): sirve de respaldo y de línea base. Si uno se queda sin memoria, se usa el otro.",
    7: "¿El LLM ve las imágenes? No: recibe texto, medidas o el registro JSON. ¿Qué tan fiel es el resumen? Una "
       "comprobación automática halló 85 % en Qwen y 50 % en Phi; no evalúa la parte interpretativa.",
    9: "¿Qué no cubren los guardrails? Las evasiones con eufemismos pasan el filtro de texto, CLIP detecta la mitad de "
       "las portadas no aptas que revisamos y el motor B no tiene filtro propio. Mejora: más descriptores y más casos.",
    10: "¿Por qué la paleta no llega al 80 %? 'Primarios' sigue en 31,5 %. Reforzamos el prompt tras ver el resultado y "
        "medimos sobre los mismos pares, así que no es una estimación independiente.",
    11: "¿Son resultados con personas? No: los usuarios son simulados y la fidelidad del resumen se comprobó con un "
        "script. El estudio con usuarios y el SUS están pendientes.",
    12: "¿Qué concluyen del sesgo? Es una observación con 100 figuras y un solo anotador: cuando el modelo dibuja "
        "rasgos, tiende a piel clara. El prompt no añade género ni etnia; se podría ofrecer un parámetro explícito.",
    13: "¿Qué harían primero? Las entrevistas y el estudio con usuarios, mejorar el filtro de imagen del motor B y subir "
        "la precisión del agente de historia.",
}
for i, sl in enumerate(prs.slides, start=1):
    if i in PREGUNTAS:
        tf = sl.notes_slide.notes_text_frame
        tf.text = tf.text + "  PREGUNTAS PROBABLES DEL JURADO: " + PREGUNTAS[i]

prs.save(SALIDA)
NL = chr(10)
guion = ["# Guion del presentador: FROG" + NL, "Exposición de 15 minutos; la demo en vivo (slide 8) dura 5 y el enunciado permite como máximo 6." + NL]
for i, sl in enumerate(prs.slides, start=1):
    guion.append(NL + f"## Slide {i}" + NL + NL + sl.notes_slide.notes_text_frame.text + NL)
(Path(__file__).resolve().parent / "guion_presentador.md").write_text("".join(guion), encoding="utf-8")
print("guardado", SALIDA)
