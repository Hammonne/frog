"""FROG_Final_Presentation_v2.pptx: rediseño editorial (14 slides, 16:9, todo editable).

Sistema visual
- Paleta: verde bosque 287A36, amarillo FFC107, verde lima B7F59E, blanco hueso F7F5EE, verde oscuro 24452C (texto).
- Tipografías: Balsamiq Sans (títulos), Poppins SemiBold (subtítulos y cifras), Poppins (texto).
- Composición: márgenes de 0,7", rótulo FROG + sección arriba, título de una línea cuando cabe, una idea por slide.
- Runa solo en 6 slides (portada, solución, demo, calidad, limitaciones, cierre).
Los datos son los mismos de la v1 y de los experimentos; no se modifica ningún resultado.

Uso:  python presentacion/construir_presentacion_v2.py
"""
from pathlib import Path

from lxml import etree
from PIL import Image, ImageFont
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
REC = RAIZ / "assets" / "presentacion" / "recortes"
ASS = RAIZ / "assets" / "presentacion"
DEMO, DEMO_B = RAIZ / "codigo" / "salidas" / "demo", RAIZ / "codigo" / "salidas" / "demo_b"
FUENTES = AQUI / "fuentes"
V1 = AQUI / "FROG_Final_Presentation.pptx"
SALIDA = AQUI / "FROG_Final_Presentation_v2.pptx"

VERDE, AMARILLO, LIMA, HUESO, TEXTO = "287A36", "FFC107", "B7F59E", "F7F5EE", "24452C"
LIMA_SUAVE, AMARILLO_SUAVE, ROJO, BLANCO = "E6F7D9", "FFF1BF", "C0463C", "FFFFFF"
TIT, SUB, CUE = "Balsamiq Sans", "Poppins SemiBold", "Poppins"
F_TIT = ImageFont.truetype(str(FUENTES / "BalsamiqSans-Bold.ttf"), 100)
F_SUB = ImageFont.truetype(str(FUENTES / "Poppins-SemiBold.ttf"), 100)


def ancho_pulgadas(texto, pt, fuente=F_TIT):
    """Ancho del texto en pulgadas a `pt` puntos (se mide con la fuente real)."""
    return fuente.getlength(texto) * pt / 100 / 72


def rgb(h):
    return RGBColor.from_string(h)


prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
VACIO = prs.slide_layouts[6]
MARGEN = 0.7


# ------------------------------------------------------------------ utilidades
def nueva():
    s = prs.slides.add_slide(VACIO)
    p = s.shapes.add_picture(str(ASS / "fondo_hueso.png"), 0, 0, prs.slide_width, prs.slide_height)
    p.name = "Fondo de papel"
    return s


def imagen(s, ruta, x, y, w=None, h=None, rot=0, nombre=None):
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


def imagen_cover(s, ruta, x, y, w, h, rot=0, nombre=None):
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


def sombra(shape, blur=7, dist=3, alpha=30):
    sp = shape._element.spPr
    for e in sp.findall(qn("a:effectLst")):
        sp.remove(e)
    ef = etree.SubElement(sp, qn("a:effectLst"))
    sh = etree.SubElement(ef, qn("a:outerShdw"), blurRad=str(int(blur * 12700)), dist=str(int(dist * 12700)),
                          dir="5400000", algn="t", rotWithShape="0")
    c = etree.SubElement(sh, qn("a:srgbClr"), val="2A3A20")
    etree.SubElement(c, qn("a:alpha"), val=str(alpha * 1000))


def forma(s, tipo, x, y, w, h, relleno=None, linea=None, grosor=1.5, rot=0, sombrea=False, nombre=None, radio=None,
          dash=False):
    f = s.shapes.add_shape(tipo, Inches(x), Inches(y), Inches(w), Inches(h))
    if relleno is None:
        f.fill.background()
    else:
        f.fill.solid()
        f.fill.fore_color.rgb = rgb(relleno)
    if linea:
        f.line.color.rgb = rgb(linea)
        f.line.width = Pt(grosor)
        if dash:
            f.line.dash_style = 4
    else:
        f.line.fill.background()
    if radio is not None and tipo == MSO_SHAPE.ROUNDED_RECTANGLE:
        f.adjustments[0] = radio
    f.rotation = rot
    if sombrea:
        sombra(f)
    if nombre:
        f.name = nombre
    return f


def texto(s, x, y, w, h, parrafos, size=16, color=TEXTO, fuente=CUE, align=PP_ALIGN.LEFT, ancla=MSO_ANCHOR.TOP,
          nombre=None, interlineado=None, espacio=0, rot=0, cursiva=False):
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
        for t, o in ([(par, {})] if isinstance(par, str) else par):
            r = p.add_run()
            r.text = t
            r.font.size = Pt(o.get("size", size))
            r.font.name = o.get("fuente", fuente)
            r.font.italic = o.get("cursiva", cursiva)
            r.font.color.rgb = rgb(o.get("color", color))
    tb.rotation = rot
    if nombre:
        tb.name = nombre
    return tb


def flecha(s, x1, y1, x2, y2, color=VERDE, grosor=2.25, dash=False, punta=True, nombre="Flecha"):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(grosor)
    if dash:
        c.line.dash_style = 4
    if punta:
        ln = c.line._get_or_add_ln()
        etree.SubElement(ln, qn("a:tailEnd"), type="triangle", w="med", len="med")
    c.name = nombre
    return c


def ruta(s, puntos, **kw):
    """Camino de varios tramos; solo el último lleva punta."""
    for i in range(len(puntos) - 1):
        (a, b), (c, d) = puntos[i], puntos[i + 1]
        flecha(s, a, b, c, d, punta=(i == len(puntos) - 2) and kw.get("punta", True),
               **{k: v for k, v in kw.items() if k != "punta"})


def marcador(s, x, y, w, h=0.16, color=AMARILLO):
    """Subrayado tipo resaltador, ligeramente inclinado."""
    return forma(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, relleno=color, radio=0.5, rot=-0.8, nombre="Subrayado")


def numero(s, x, y, n, d=0.46, relleno=AMARILLO, color=VERDE):
    forma(s, MSO_SHAPE.OVAL, x, y, d, d, relleno=relleno, nombre=f"Número {n}")
    texto(s, x, y, d, d, str(n), size=16, color=color, fuente=TIT, align=PP_ALIGN.CENTER, ancla=MSO_ANCHOR.MIDDLE,
          nombre="Número")


def pastilla(s, t, x, y, w, h=0.4, relleno=LIMA, color=TEXTO, size=14, fuente=SUB, punteada=False):
    f = forma(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, relleno=None if punteada else relleno,
              linea=VERDE if punteada else None, grosor=1.5, radio=0.5, dash=punteada, nombre="Pastilla: " + t)
    texto(s, x, y, w, h, t, size=size, color=color, fuente=fuente, align=PP_ALIGN.CENTER, ancla=MSO_ANCHOR.MIDDLE,
          nombre="Texto de pastilla")
    return f


def encabezado(s, seccion, titulo, ancho_max=12.0, subrayar=None, ancho_titulo=None, y_titulo=0.92, size=40):
    """Rótulo FROG + sección, y título en Balsamiq Sans (una línea si cabe)."""
    pastilla(s, "FROG", MARGEN, 0.38, 0.95, h=0.42, relleno=AMARILLO, color=VERDE, size=18, fuente=TIT)
    texto(s, MARGEN + 1.15, 0.38, 8, 0.42, seccion, size=14, fuente=CUE, ancla=MSO_ANCHOR.MIDDLE, nombre="Sección")
    limite = ancho_titulo or ancho_max
    pt = size
    while ancho_pulgadas(titulo, pt) > limite and pt > 30:
        pt -= 1
    texto(s, MARGEN, y_titulo, limite + 0.3, 1.0, titulo, size=pt, color=VERDE, fuente=TIT, interlineado=0.92,
          nombre="Título")
    if subrayar:
        previo, palabra = subrayar
        x = MARGEN + ancho_pulgadas(previo, pt)
        marcador(s, x, y_titulo + pt / 72 * 1.18, ancho_pulgadas(palabra, pt))
    return pt


def polaroid(s, ruta_img, x, y, w, h, rot=0, pie=None, nombre="Polaroid"):
    marco = forma(s, MSO_SHAPE.RECTANGLE, x, y, w, h + (0.55 if pie else 0.3), relleno="FBFAF5", rot=rot,
                  sombrea=True, nombre=nombre)
    foto = imagen_cover(s, ruta_img, x + 0.1, y + 0.1, w - 0.2, h - 0.1, rot=rot, nombre=nombre + " (imagen)")
    if pie:
        texto(s, x + 0.1, y + h + 0.1, w - 0.2, 0.4, pie, size=12, align=PP_ALIGN.CENTER, rot=rot,
              nombre=nombre + " (pie)")
    return marco, foto


def deco(s, nombre, x, y, w=None, h=None, rot=0):
    return imagen(s, REC / f"{nombre}.png", x, y, w=w, h=h, rot=rot, nombre="Decoración: " + nombre)


def barras(s, x, y, w, h, categorias, series, colores, titulo_g=None, maximo=100, formato='0"%"', leyenda=True,
           tam=14, hueco=60):
    cd = CategoryChartData()
    cd.categories = categorias
    for nombre, vals in series:
        cd.add_series(nombre, vals)
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.font.size, ch.font.name = Pt(tam), CUE
    ch.font.color.rgb = rgb(TEXTO)
    ch.has_title = bool(titulo_g)
    if titulo_g:
        ch.chart_title.text_frame.text = titulo_g
        r = ch.chart_title.text_frame.paragraphs[0].runs[0]
        r.font.size, r.font.name = Pt(tam), SUB
        r.font.color.rgb = rgb(TEXTO)
    ch.has_legend = leyenda and len(series) > 1
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.BOTTOM
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(tam)
    va, ca = ch.value_axis, ch.category_axis
    va.maximum_scale, va.minimum_scale = maximo, 0
    va.major_unit = 20
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("DDDACB")
    va.major_gridlines.format.line.width = Pt(0.5)
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(tam - 2)
    va.tick_labels.number_format, va.tick_labels.number_format_is_linked = formato, False
    ca.format.line.color.rgb = rgb(TEXTO)
    ca.tick_labels.font.size = Pt(tam)
    plot = ch.plots[0]
    plot.gap_width = hueco
    plot.overlap = -5 if len(series) > 1 else 0
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = formato, False
    dl.font.size, dl.font.name = Pt(tam), SUB
    dl.font.color.rgb = rgb(TEXTO)
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    for i, ser in enumerate(plot.series):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(colores[i % len(colores)])
        ser.invert_if_negative = False
    gf.name = "Gráfico: " + (titulo_g or "barras")
    return gf


def lineas(s, x, y, w, h, categorias, series, colores, minimo=30, maximo=48, tam=14):
    cd = CategoryChartData()
    cd.categories = categorias
    for nombre, vals in series:
        cd.add_series(nombre, vals)
    gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.font.size, ch.font.name = Pt(tam), CUE
    ch.font.color.rgb = rgb(TEXTO)
    ch.has_title = False
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.BOTTOM
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(tam)
    va = ch.value_axis
    va.minimum_scale, va.maximum_scale, va.major_unit = minimo, maximo, 5
    va.major_gridlines.format.line.color.rgb = rgb("DDDACB")
    va.format.line.fill.background()
    va.tick_labels.number_format, va.tick_labels.number_format_is_linked = '0"%"', False
    va.tick_labels.font.size = Pt(tam - 2)
    ch.category_axis.tick_labels.font.size = Pt(tam)
    plot = ch.plots[0]
    plot.has_data_labels = True
    plot.data_labels.number_format, plot.data_labels.number_format_is_linked = '0.0', False
    plot.data_labels.font.size, plot.data_labels.font.name = Pt(tam), SUB
    plot.data_labels.position = XL_LABEL_POSITION.ABOVE
    for i, ser in enumerate(plot.series):
        ser.format.line.color.rgb = rgb(colores[i])
        ser.format.line.width = Pt(3.5)
        ser.smooth = False
        ser.marker.format.fill.solid()
        ser.marker.format.fill.fore_color.rgb = rgb(colores[i])
        ser.marker.format.line.color.rgb = rgb(colores[i])
        ser.marker.size = 10
    plot.series[1].data_labels.position = XL_LABEL_POSITION.BELOW
    gf.name = "Gráfico: líneas"
    return gf


def cifra(s, x, y, w, valor, pie, size=44, color=VERDE, pie_size=14, pie_w=None, subrayado=True):
    """Métrica protagonista: cifra grande con resaltador y una línea de explicación."""
    ancho = ancho_pulgadas(valor, size, F_SUB)
    if subrayado:
        marcador(s, x, y + size / 72 * 0.82, min(ancho, w), h=0.14)
    texto(s, x, y, w, size / 72 * 1.25, valor, size=size, color=color, fuente=SUB, nombre="Cifra " + valor)
    texto(s, x, y + size / 72 * 1.3, pie_w or w, 0.9, pie, size=pie_size, nombre="Explicación de la cifra")


# =========================================================================== 1 PORTADA
s = nueva()
deco(s, "deco_estrellas", 0.2, 0.3, w=0.62)
deco(s, "deco_rayitas", 7.4, 0.8, w=1.1, rot=8)
texto(s, 0.55, 0.95, 8.5, 3.0, "FROG", size=190, color=VERDE, fuente=TIT, nombre="Título")
texto(s, MARGEN, 4.0, 7.6, 0.6, "Friendly Rounds Of Generation", size=30, color=TEXTO, fuente=SUB,
      nombre="Nombre completo")
marcador(s, MARGEN, 4.62, 6.05, h=0.15)
texto(s, MARGEN, 5.0, 6.8, 0.9, "Portadas infantiles generativas con feedback humano: de un boceto y una historia a "
      "cinco propuestas.", size=17, nombre="Subtítulo")
texto(s, MARGEN, 6.35, 7.4, 0.8, ["Andrea Coa · Jimena Gurbillon · Maria Surco · Bihonda Epiquien · Nayeli Guzman",
                                    "Proyecto 2 · Planificación y Toma de Decisiones en IA · UTEC · Noviembre 2026"],
      size=12, nombre="Integrantes y curso", espacio=3)
deco(s, "deco_explosion", 9.0, 0.45, w=3.6)
imagen(s, REC / "runa_saluda_grande.png", 8.7, 0.7, h=5.5, nombre="Runa saluda")
imagen(s, REC / "papel_amarillo.png", 9.15, 5.9, w=3.9, rot=-3, nombre="Rótulo de papel amarillo")
texto(s, 9.25, 5.93, 3.7, 0.7, "Runa", size=40, color=VERDE, fuente=TIT, align=PP_ALIGN.CENTER,
      ancla=MSO_ANCHOR.MIDDLE, rot=-3, nombre="Nombre de la mascota")
texto(s, 9.25, 6.55, 3.7, 0.35, "la mascota de FROG", size=14, fuente=SUB, align=PP_ALIGN.CENTER, rot=-3,
      nombre="Rol de la mascota")

# =========================================================================== 2 PROBLEMÁTICA
s = nueva()
encabezado(s, "Problemática", "Quien escribe un cuento no siempre puede ilustrarlo", ancho_titulo=6.4, size=38)
dif = [("No sabe dibujar bien", "Hace dibujos simples, pero sabe lo que quiere contar."),
       ("No puede pagar a un ilustrador", "No alcanza para cada cuento que escribe para su aula."),
       ("La IA genérica no le sirve", "Las imágenes no se parecen a su idea ni a su historia, y el título sale mal escrito.")]
for i, (t, d) in enumerate(dif):
    y = 2.95 + i * 1.12
    numero(s, MARGEN, y, i + 1)
    texto(s, MARGEN + 0.7, y - 0.02, 5.2, 0.4, t, size=18, fuente=SUB, color=VERDE, nombre="Dificultad")
    texto(s, MARGEN + 0.7, y + 0.4, 5.2, 0.7, d, size=14, nombre="Detalle")
texto(s, MARGEN, 6.35, 6.3, 0.7, [[("Carmen, 34 años, docente de inicial", {"fuente": SUB, "color": VERDE}),
                                    (" · proto-persona del caso de uso, construida antes de las entrevistas "
                                     "(pendientes).", {})]], size=13, nombre="Proto-persona")
polaroid(s, DEMO / "boceto_preprocesado.png", 7.55, 1.75, 2.6, 3.4, rot=-3, pie="Su boceto", nombre="Boceto")
polaroid(s, DEMO / "R1-V1.png", 10.15, 2.0, 2.6, 3.4, rot=3, pie="Una de las 5 portadas", nombre="Portada")
marcador(s, 7.7, 6.1, 4.8, h=0.13)
texto(s, 7.55, 6.3, 5.2, 0.8, "Una idea, cinco opciones comparables.", size=18, fuente=SUB, color=VERDE,
      align=PP_ALIGN.CENTER, nombre="Idea")

# =========================================================================== 3 SOLUCIÓN (flujo continuo)
s = nueva()
pastilla(s, "FROG", MARGEN, 0.38, 0.95, h=0.42, relleno=AMARILLO, color=VERDE, size=18, fuente=TIT)
texto(s, MARGEN + 1.15, 0.38, 8, 0.42, "Solución técnica · Visión general", size=14, ancla=MSO_ANCHOR.MIDDLE, nombre="Sección")
texto(s, MARGEN, 0.95, 7.6, 1.8, ["De un boceto y una historia", "a cinco portadas"], size=40, color=VERDE, fuente=TIT,
      interlineado=0.92, nombre="Título")
marcador(s, MARGEN + ancho_pulgadas("a cinco ", 40), 2.18, ancho_pulgadas("portadas", 40), h=0.14)
burbuja = forma(s, MSO_SHAPE.OVAL_CALLOUT, 8.55, 0.35, 3.05, 1.65, relleno=LIMA_SUAVE, nombre="Globo de Runa")
burbuja.adjustments[0], burbuja.adjustments[1] = 0.62, 0.36
texto(s, 8.8, 0.62, 2.55, 1.2, "Runa genera cinco opciones, aprende de tu feedback y refina la siguiente ronda.",
      size=13, align=PP_ALIGN.CENTER, ancla=MSO_ANCHOR.MIDDLE, nombre="Mensaje de Runa")
imagen(s, REC / "runa_dibuja.png", 11.55, 0.3, h=2.1, nombre="Runa dibuja")
centros = [1.95, 4.45, 6.95, 9.45, 11.95]
etapas = [("Boceto e historia", "Dibujas o subes un boceto y cuentas el cuento."),
          ("Cinco propuestas", "Cada una cambia solo un parámetro."),
          ("Aceptar o rechazar", "Con motivo, por portada o por paquete."),
          ("Planificador", "Aprende qué valores prefieres (muestreo de Thompson)."),
          ("Resumen final", "Un agente explica lo que pasó.")]
for i, cx in enumerate(centros):
    forma(s, MSO_SHAPE.OVAL, cx - 0.975, 3.1, 1.95, 1.95, relleno=LIMA_SUAVE, nombre=f"Fondo de etapa {i + 1}")
    numero(s, cx - 1.0, 3.0, i + 1, d=0.52)
    pastilla(s, etapas[i][0], cx - 1.15, 5.3, 2.3, h=0.42, relleno=LIMA, size=14)
    texto(s, cx - 1.1, 5.85, 2.2, 0.8, etapas[i][1], size=13, align=PP_ALIGN.CENTER, nombre="Descripción de etapa")
    if i < 4:
        flecha(s, cx + 1.03, 4.08, cx + 1.47, 4.08, grosor=3)
# 1: boceto + historia
polaroid(s, DEMO / "boceto_preprocesado.png", centros[0] - 0.78, 3.45, 0.95, 1.3, rot=-5, nombre="Boceto")
forma(s, MSO_SHAPE.RECTANGLE, centros[0] + 0.1, 3.55, 0.8, 1.1, relleno=LIMA, rot=6, sombrea=True, nombre="Historia")
for k in range(4):
    forma(s, MSO_SHAPE.ROUNDED_RECTANGLE, centros[0] + 0.2, 3.72 + k * 0.2, 0.55, 0.07, relleno=BLANCO, rot=6, radio=0.5,
          nombre="Línea de texto")
# 2: cinco portadas en abanico
for k, ang in sorted(enumerate((-14, -7, 0, 7, 14)), key=lambda t: -abs(t[1])):
    imagen_cover(s, DEMO / f"R1-V{k + 1}.png", centros[1] - 0.4 + (k - 2) * 0.28, 3.4 + abs(k - 2) * 0.04, 0.8, 1.2,
                 rot=ang, nombre=f"Portada {k + 1}")
# 3: aceptar / rechazar
forma(s, MSO_SHAPE.OVAL, centros[2] - 0.92, 3.6, 0.85, 0.85, relleno=LIMA, nombre="Aceptar")
forma(s, MSO_SHAPE.OVAL, centros[2] + 0.07, 3.6, 0.85, 0.85, relleno="F4C7C0", nombre="Rechazar")
imagen(s, REC / "ico_pulgar_arriba.png", centros[2] - 0.78, 3.72, h=0.6, nombre="Pulgar arriba")
imagen(s, REC / "ico_pulgar_arriba.png", centros[2] + 0.2, 3.72, h=0.6, rot=180, nombre="Pulgar abajo")
# 4: planificador
imagen(s, REC / "deco_nube.png", centros[3] - 0.75, 3.35, w=1.5, nombre="Mancha amarilla")
imagen(s, REC / "ico_grafico.png", centros[3] - 0.45, 3.65, h=0.9, nombre="Gráfico")
# 5: resumen
imagen(s, REC / "ico_informe.png", centros[4] - 0.65, 3.4, h=1.35, nombre="Resumen")
# bucle de rondas
ruta(s, [(centros[4], 6.72), (centros[4], 6.98), (centros[0], 6.98), (centros[0], 6.72)], color=VERDE, grosor=2.5)
pastilla(s, "Hasta 3 rondas", 5.75, 6.76, 2.4, h=0.46, relleno=AMARILLO, size=16)
deco(s, "hierba", 0.1, 6.95, w=1.5)
deco(s, "flores", 12.3, 6.5, w=0.85)

# =========================================================================== 4 ARQUITECTURA
s = nueva()
encabezado(s, "Solución técnica · Arquitectura", "Siete componentes y un registro de cada decisión")
NODO = BLANCO


def zona(x, y, w, h, nombre, relleno, lx=None):
    forma(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, relleno=relleno, radio=0.06, nombre="Zona " + nombre)
    texto(s, lx if lx else x + 0.18, y + 0.07, 1.4 if lx else w - 0.3, 0.3, nombre.upper(), size=11, fuente=SUB,
          color=VERDE, nombre="Etiqueta de zona")


def nodo(x, y, w, h, t, num=None, relleno=NODO, tamano=12, forma_=MSO_SHAPE.ROUNDED_RECTANGLE):
    forma(s, forma_, x, y, w, h, relleno=relleno, linea=VERDE, grosor=1.5,
          radio=0.14 if forma_ == MSO_SHAPE.ROUNDED_RECTANGLE else None, nombre="Nodo: " + t.split("\n")[0])
    texto(s, x + 0.08, y, w - 0.16, h, t.split("\n"), size=tamano, align=PP_ALIGN.CENTER, ancla=MSO_ANCHOR.MIDDLE,
          nombre="Texto de nodo", interlineado=0.95)
    if num:
        numero(s, x - 0.14, y - 0.16, num, d=0.34)


def rombo(x, y, w, h, t):
    forma(s, MSO_SHAPE.DIAMOND, x, y, w, h, relleno=AMARILLO, linea=VERDE, grosor=1.5, nombre="Decisión: " + t)
    texto(s, x + w * 0.2, y, w * 0.6, h, t.split("\n"), size=11, fuente=SUB, align=PP_ALIGN.CENTER,
          ancla=MSO_ANCHOR.MIDDLE, nombre="Texto de decisión", interlineado=0.9)


def rotulo_flecha(x, y, w, t, align=PP_ALIGN.CENTER, color=TEXTO):
    texto(s, x, y, w, 0.3, t, size=10.5, color=color, align=align, nombre="Etiqueta de flecha")


# zonas
zona(0.55, 1.95, 4.65, 1.95, "Entrada", LIMA_SUAVE)
zona(5.35, 1.95, 7.45, 1.95, "Generación", AMARILLO_SUAVE)
zona(5.35, 4.55, 7.45, 1.95, "Interacción", LIMA_SUAVE)
zona(0.55, 4.55, 4.65, 1.95, "Validación", AMARILLO_SUAVE, lx=4.1)
# fila superior
nodo(0.75, 2.4, 1.75, 1.2, "Usuario\nboceto + historia\n+ título + parámetros")
nodo(2.95, 2.4, 2.0, 1.2, "Preprocesamiento\n+ guardrails de entrada\n+ agente de historia", num=1)
nodo(5.6, 2.4, 2.0, 1.2, "Planificador\n5 configuraciones\n(Thompson, Beta)", num=2)
nodo(8.0, 2.4, 2.1, 1.2, "Motor A: SD 1.5\n+ ControlNet\nMotor B: SD-Turbo", num=3)
nodo(10.5, 2.4, 2.1, 1.2, "Guardrails de salida\n+ agente tipográfico\n+ render del título", num=4)
for (a, b) in ((2.5, 2.95), (4.95, 5.6), (7.6, 8.0), (10.1, 10.5)):
    flecha(s, a + 0.0, 3.0, b, 3.0)
# fila inferior (el flujo vuelve hacia la izquierda)
nodo(10.5, 4.95, 2.1, 1.2, "Interfaz Gradio\naceptar / rechazar\n+ motivo + editar fuente", num=5)
forma(s, MSO_SHAPE.CAN, 8.15, 4.9, 1.75, 1.3, relleno=BLANCO, linea=VERDE, grosor=1.5, nombre="Nodo: Registro JSON")
texto(s, 8.2, 5.15, 1.65, 1.0, ["Registro JSON", "parámetros, semillas,", "decisiones, motivos"], size=11,
      align=PP_ALIGN.CENTER, ancla=MSO_ANCHOR.MIDDLE, nombre="Texto del registro", interlineado=0.92)
numero(s, 8.0, 4.78, 6, d=0.34)
rombo(5.85, 4.95, 1.9, 1.25, "¿Otra ronda?\n(r < 3)")
# flechas fila inferior
flecha(s, 11.55, 3.6, 11.55, 4.95)                      # 4 -> 5
flecha(s, 12.35, 4.95, 12.35, 3.6, dash=True)           # cambio de fuente
texto(s, 11.65, 4.12, 0.7, 0.55, ["cambio", "de fuente"], size=9.5, align=PP_ALIGN.CENTER, nombre="Etiqueta de flecha")
flecha(s, 10.5, 5.55, 9.9, 5.55)                        # 5 -> 6
flecha(s, 8.15, 5.55, 7.75, 5.55)                       # 6 -> ¿otra ronda?
ruta(s, [(6.8, 4.95), (6.8, 4.25), (6.6, 4.25), (6.6, 3.6)], color=VERDE)  # sí -> planificador
rotulo_flecha(6.9, 4.17, 2.1, "sí: actualizar preferencias", align=PP_ALIGN.LEFT)
# validación
nodo(2.95, 4.95, 2.0, 1.2, "Agente LLM\nQwen2.5 | Phi-3.5\nresumen + JSON", num=7)
rombo(0.75, 4.95, 1.9, 1.25, "¿Coincide con\nel registro?")
flecha(s, 5.85, 5.55, 4.95, 5.55)                       # no -> LLM
rotulo_flecha(5.05, 5.25, 0.7, "no")
flecha(s, 2.95, 5.55, 2.65, 5.55)                       # LLM -> coincide
ruta(s, [(1.7, 4.95), (1.7, 4.45), (3.95, 4.45), (3.95, 4.95)], color=VERDE)      # reintento
rotulo_flecha(1.9, 4.18, 2.1, "no: reintento (máx. 2)", align=PP_ALIGN.LEFT)
# salida
nodo(0.75, 6.62, 1.95, 0.6, "Resumen final al usuario", relleno=LIMA, tamano=12)
nodo(3.1, 6.62, 2.2, 0.6, "Resumen por plantilla (respaldo)", tamano=11)
flecha(s, 1.7, 6.2, 1.7, 6.62)
rotulo_flecha(1.8, 6.28, 0.6, "sí", align=PP_ALIGN.LEFT)
flecha(s, 3.95, 6.15, 3.95, 6.62)
rotulo_flecha(4.05, 6.2, 2.2, "si fallan los reintentos", align=PP_ALIGN.LEFT)
flecha(s, 3.1, 6.92, 2.7, 6.92)
# rechazo de la entrada
flecha(s, 3.95, 3.6, 3.95, 4.1, color=ROJO, dash=True)
texto(s, 4.05, 3.7, 1.2, 0.5, ["rechazo de la", "entrada"], size=9.5, color=ROJO, nombre="Rechazo")
texto(s, 5.6, 6.7, 7.1, 0.7, ["Los rombos son decisiones. La flecha roja punteada es el rechazo de la entrada "
                               "(boceto vacío, rostro real o contenido no apto).",
                               "El registro JSON guarda parámetros, semillas, decisiones y motivos de cada ronda."],
      size=12, nombre="Cómo leer", espacio=3)

# =========================================================================== 5 PERSONALIZACIÓN
s = nueva()
encabezado(s, "Solución técnica · Personalización", "Seis parámetros para personalizar cada portada")
params = [("Estilo", "acuarela · lápices · collage · vectorial · plastilina"),
          ("Paleta", "pastel · cálida · fría · primarios · tierra"),
          ("Edad", "0-3 · 4-6 · 7-9 · 10-12 · sin"),
          ("Ambiente", "alegre · aventura · calma · misterio · humor"),
          ("Fidelidad al boceto", "muy baja · baja · media · alta · muy alta"),
          ("Zona del título", "superior · inferior · ambas · centrada · sin")]
for i, (n, v) in enumerate(params):
    x = MARGEN + (i % 2) * 3.35
    y = 2.3 + (i // 2) * 1.5
    texto(s, x, y, 3.1, 0.4, n, size=20, color=VERDE, fuente=SUB, nombre="Parámetro")
    texto(s, x, y + 0.45, 3.1, 0.8, v, size=13, nombre="Valores")
    if i < 4:
        flecha(s, x, y + 1.28, x + 3.0, y + 1.28, color=LIMA, grosor=1.5, punta=False, nombre="Separador")
texto(s, MARGEN, 6.62, 6.4, 0.6, [[("En cada ronda ", {}), ("uno", {"fuente": SUB, "color": VERDE}),
                                    (" de los seis toma sus cinco valores; los otros cinco quedan fijos.", {})]],
      size=14, nombre="Cómo funciona una ronda")
forma(s, MSO_SHAPE.ROUNDED_RECTANGLE, 7.75, 1.95, 5.0, 5.0, relleno=AMARILLO_SUAVE, radio=0.04, nombre="Fondo del planificador")
texto(s, 8.1, 2.15, 4.4, 0.5, "Thompson Sampling", size=22, fuente=TIT, color=VERDE, nombre="Planificador")
paso = ["Recibe feedback", "Actualiza preferencias", "Explora valores restantes", "Genera una nueva ronda"]
det = ["Aceptar o rechazar, con motivo.", "Qué valores prefiere la persona.", "Los demás se eligen al azar.",
       "Con lo aprendido."]
for i, (p_, d_) in enumerate(zip(paso, det)):
    y = 2.85 + i * 0.88
    numero(s, 8.1, y, i + 1, d=0.5, relleno=VERDE, color=BLANCO)
    texto(s, 8.8, y - 0.03, 3.8, 0.4, p_, size=16, fuente=SUB, nombre="Paso")
    texto(s, 8.8, y + 0.34, 3.8, 0.4, d_, size=12, nombre="Detalle del paso")
    if i < 3:
        flecha(s, 8.35, y + 0.52, 8.35, y + 0.86, color=VERDE, grosor=2)
pastilla(s, "Hasta 3 rondas", 8.1, 6.4, 2.5, h=0.46, relleno=AMARILLO, size=16)
imagen(s, REC / "ico_ronda.png", 10.85, 6.3, h=0.65, nombre="Icono de ronda")

# =========================================================================== 6 MOTORES
s = nueva()
encabezado(s, "Solución técnica · Modelo generativo", "El motor A reinterpreta el boceto; el B lo conserva")
polaroid(s, DEMO / "boceto_preprocesado.png", 0.8, 2.85, 1.9, 2.55, rot=-3, pie="Boceto original", nombre="Boceto")
flecha(s, 2.9, 3.6, 3.6, 2.9, color=VERDE)
flecha(s, 2.9, 4.7, 3.6, 5.45, color=VERDE)
filas = [("Motor A", "Stable Diffusion 1.5 + ControlNet", DEMO, 1.9, ("93 %", "7,8 s", "28 %")),
         ("Motor B", "SD-Turbo (img2img)", DEMO_B, 4.55, ("20 %", "1,6 s", "98 %"))]
for nombre_m, sub_m, carpeta, y, (est, tiempo, fid) in filas:
    pastilla(s, nombre_m, 3.7, y - 0.02, 1.35, h=0.4, relleno=AMARILLO if nombre_m == "Motor A" else LIMA, size=15)
    texto(s, 5.2, y - 0.02, 4.0, 0.4, sub_m, size=13, ancla=MSO_ANCHOR.MIDDLE, nombre="Modelo")
    for k, v in enumerate((1, 3, 5)):
        imagen_cover(s, carpeta / f"R1-V{v}.png", 3.7 + k * 1.6, y + 0.5, 1.5, 2.0, nombre=f"{nombre_m}: portada {k + 1}")
    for j, (val, cap) in enumerate(((est, "acierto de estilo"), (fid, "fidelidad al boceto"), (tiempo, "por ronda"))):
        cifra(s, 9.1 + j * 1.25, y + 0.55, 1.2, val, cap, size=26, pie_size=11, pie_w=1.1,
              subrayado=(nombre_m == "Motor A" and j == 0) or (nombre_m == "Motor B" and j > 0))
texto(s, 3.7, 7.0, 9.0, 0.3, "Estilos mostrados: acuarela, collage y plastilina · E1: 3 000 portadas · el resaltado marca lo que gana cada motor", size=10.5, nombre="Nota de datos")

# =========================================================================== 7 AGENTES
s = nueva()
encabezado(s, "Solución técnica · Agentes de IA", "Tres agentes de IA, cada uno con su validador")
agentes = [("Agente de historia", "ico_libro", "Un cuento en español, hasta 500 palabras.",
            '{"personajes":["conejo"],\n "objetos":["flores"],\n "lugar":"jardin"}',
            "Cada personaje y objeto debe aparecer en el texto; lo que no aparece se marca."),
           ("Agente tipográfico", "ico_lupa", "Medidas de la zona del título: contraste, bordes y color.", None,
            "Un renderizador determinista dibuja las letras: el título sale correcto y dentro de los límites por edad."),
           ("Agente de resumen", "ico_informe", "El registro JSON de la sesión.",
            "Ronda 1 (eje: Paleta)\nAceptadas: R1-V3 (fría)\nRechazadas: R1-V1 (pastel;\nmotivo: colores)",
            "Contrasta IDs, motivos y parámetros con el registro; reintenta y, si falla, usa una plantilla.")]
for i, (n, ico, recibe, produce, valida) in enumerate(agentes):
    x = MARGEN + i * 4.1
    imagen(s, REC / f"{ico}.png", x, 2.0, h=0.7, nombre="Icono")
    texto(s, x + 1.3, 2.05, 2.5, 0.6, n, size=17, fuente=SUB, color=VERDE, ancla=MSO_ANCHOR.MIDDLE, nombre="Agente")
    pastilla(s, "RECIBE", x, 3.0, 1.0, h=0.3, relleno=LIMA, size=10.5)
    texto(s, x + 1.15, 2.96, 2.55, 0.8, recibe, size=13, nombre="Recibe")
    pastilla(s, "PRODUCE", x, 4.05, 1.0, h=0.3, relleno=LIMA, size=10.5)
    if produce:
        forma(s, MSO_SHAPE.RECTANGLE, x, 4.5, 3.7, 1.2, relleno=LIMA_SUAVE, nombre="Salida")
        texto(s, x + 0.15, 4.55, 3.45, 1.1, produce.split("\n"), size=13, fuente="Consolas", ancla=MSO_ANCHOR.MIDDLE,
              nombre="Salida del agente")
    else:
        imagen_cover(s, ASS / "titulo_agente_conejo.png", x, 4.5, 3.7, 1.25, nombre="Título que produce el agente")
    pastilla(s, "SE VALIDA", x, 5.95, 1.2, h=0.3, relleno=AMARILLO, size=10.5)
    texto(s, x, 6.35, 3.7, 0.9, valida, size=13, nombre="Cómo se valida")

# =========================================================================== 8 DEMOSTRACIÓN
s = nueva()
encabezado(s, "Demostración en vivo", "Demostración: de una idea a una portada")
pastilla(s, "5 minutos · una interacción completa", 8.4, 0.4, 4.3, h=0.42, relleno=AMARILLO, size=14)
pasos = ["Dibujar o subir el boceto", "Contar la historia y revisar elementos", "Generar las 5 portadas",
         "Aceptar o rechazar, con motivo", "Segunda ronda guiada", "Leer el resumen del agente"]
contenido = [("img", DEMO / "boceto_preprocesado.png"), ("txt", None), ("img", DEMO / "R1-V3.png"),
             ("img", DEMO / "R1-V5.png"), ("img", DEMO / "R1-V4.png"), ("res", None)]
for i, (paso_t, (tipo, ruta_img)) in enumerate(zip(pasos, contenido)):
    x = 0.75 + i * 2.02
    rot = (-2.5, 2, -1.5, 2.5, -2, 1.5)[i]
    y = 2.2 + (0.12 if i % 2 else 0)
    marco = forma(s, MSO_SHAPE.RECTANGLE, x, y, 1.82, 2.95, relleno="FBFAF5", rot=rot, sombrea=True, nombre=f"Cuadro {i + 1}")
    if tipo == "img":
        imagen_cover(s, ruta_img, x + 0.09, y + 0.09, 1.64, 2.3, rot=rot, nombre=f"Imagen del paso {i + 1}")
    elif tipo == "txt":
        forma(s, MSO_SHAPE.RECTANGLE, x + 0.09, y + 0.09, 1.64, 2.3, relleno=LIMA_SUAVE, rot=rot, nombre="Historia")
        texto(s, x + 0.24, y + 0.22, 1.36, 2.2, [[("“Un conejo que ama las flores…”", {"cursiva": True})],
                                                 [("conejo · flores · jardín", {"fuente": SUB, "color": VERDE})]],
              size=11.5, rot=rot, espacio=8, nombre="Historia y elementos")
    else:
        forma(s, MSO_SHAPE.RECTANGLE, x + 0.09, y + 0.09, 1.64, 2.3, relleno=BLANCO, rot=rot, nombre="Resumen")
        texto(s, x + 0.24, y + 0.22, 1.36, 2.2, ["Ronda 1 (eje: Paleta)", "Aceptadas: R1-V3 (fría)",
                                                 "Rechazadas: R1-V1 (pastel; motivo: colores)"], size=10.5, rot=rot,
              espacio=4, nombre="Resumen de ejemplo")
    numero(s, x - 0.12, y - 0.18, i + 1, d=0.44, relleno=VERDE, color=BLANCO)
    texto(s, x - 0.05, y + 3.1, 1.95, 0.7, paso_t, size=13, align=PP_ALIGN.CENTER, fuente=SUB, nombre="Paso")
imagen(s, REC / "ico_pulgar_arriba.png", 8.3, 4.55, h=0.55, rot=8, nombre="Pulgar arriba")
imagen(s, REC / "runa_dibuja.png", 0.75, 6.05, h=1.3, nombre="Runa dibuja")
texto(s, 2.3, 6.6, 9.8, 0.6, "Cuadros de ejemplo con material real del proyecto; la interfaz se mostrará en vivo.",
      size=12, cursiva=True, nombre="Nota")

# =========================================================================== 9 ÉTICA
s = nueva()
encabezado(s, "Aspectos éticos", "La generación tiene cuatro capas de protección")
capas = [("Texto", "Lista de bloqueo: violencia, contenido sexual, artistas y personajes con marca."),
         ("Fotografías", "Solo dibujos: se rechaza toda foto con el rostro de una persona."),
         ("Imagen generada", "CLIP compara cada portada con descriptores de contenido no apto."),
         ("Derechos de autor", "Estilos genéricos y aviso: la protección de autor no está garantizada.")]
flecha(s, 1.2, 2.55, 12.2, 2.55, color=LIMA, grosor=6, punta=True, nombre="Flujo de protección")
for i, (n, d) in enumerate(capas):
    x = MARGEN + i * 3.1
    numero(s, x, 2.3, i + 1, d=0.52, relleno=AMARILLO)
    texto(s, x, 3.0, 2.85, 0.45, n, size=18, fuente=SUB, color=VERDE, nombre="Capa")
    texto(s, x, 3.5, 2.85, 1.0, d, size=13, nombre="Descripción de capa")
imagen(s, REC / "ico_escudo.png", 12.1, 0.28, h=0.62, nombre="Escudo")
cifra(s, MARGEN, 4.55, 4.6, "20 / 20", "entradas adversariales bloqueadas por el filtro de texto", size=64, pie_size=15,
      pie_w=4.0)
texto(s, 5.9, 4.6, 3.3, 0.4, "Lo que funciona", size=16, fuente=SUB, color=VERDE, nombre="Funciona")
texto(s, 5.9, 5.1, 3.3, 1.8, ["20 de 20 entradas peligrosas bloqueadas.", "El texto y la foto se revisan antes de generar."],
      size=13, espacio=6, nombre="Aciertos")
texto(s, 9.4, 4.6, 3.3, 0.4, "Lo que falla", size=16, fuente=SUB, color=ROJO, nombre="Falla")
texto(s, 9.4, 5.1, 3.4, 2.0, ["1 de 5 entradas legítimas se bloquea por error (un nombre con marca).",
                               "5 de 5 evasiones con eufemismos pasan el texto.",
                               "El motor B no trae filtro propio: solo lo protege CLIP."],
      size=13, espacio=6, nombre="Fallos")
flecha(s, 5.7, 4.65, 5.7, 6.9, color=LIMA, grosor=1.5, punta=False, nombre="Separador")
flecha(s, 9.2, 4.65, 9.2, 6.9, color="F0C7C2", grosor=1.5, punta=False, nombre="Separador")

# =========================================================================== 10 CALIDAD VISUAL
s = nueva()
encabezado(s, "Evaluación · Calidad visual", "Calidad visual: estilo 93 %, paleta de 69,7 a 79,2 %", ancho_titulo=10.3)
imagen(s, REC / "runa_lupa.png", 11.5, 0.3, h=1.3, nombre="Runa con lupa")
cifra(s, MARGEN, 1.95, 5.5, "93 %", "acierto de estilo del motor A (criterio: 70 %)", size=40, pie_size=13, pie_w=5.2)
cifra(s, 7.0, 1.95, 5.6, "69,7 → 79,2 %", "paleta del motor A tras reforzar el prompt (criterio: 80 %)", size=40,
      pie_size=13, pie_w=5.6)
barras(s, 0.5, 3.25, 6.3, 3.85, ["Estilo", "Paleta", "Elemento\nprincipal", "Fidelidad\nal boceto"],
       [("Motor A", [93.2, 69.7, 90.8, 28.3]), ("Motor B", [20.1, 83.8, 89.6, 97.7])], [VERDE, AMARILLO],
       titulo_g="Métricas de E1 por motor (3 000 portadas)", maximo=115, tam=13)
barras(s, 6.9, 3.25, 6.0, 3.85, ["Pastel", "Fría", "Tierra", "Cálida", "Primarios"],
       [("Original", [100, 100, 93.5, 53.5, 1.5]), ("Prompt reforzado", [100, 100, 93.4, 71.5, 31.5])],
       [VERDE, AMARILLO], titulo_g="Motor A: acierto de paleta por tipo", maximo=115, tam=12, hueco=30)

# =========================================================================== 11 FEEDBACK Y AGENTES
s = nueva()
encabezado(s, "Evaluación · Feedback y agentes", "Thompson supera al azar en la ronda 3")
bloques = [("43,0 %", "aceptación de Thompson en la ronda 3 (aleatorio: 34,8 %)", "Con la evidencia de dos rondas, "
            "Thompson supera al azar (500 usuarios simulados)."),
           ("85 %", "de los resúmenes de Qwen son fieles al registro (Phi: 50 %)", "Comprobación automática; la parte "
            "interpretativa no se evalúa."),
           ("17,6 %", "error por carácter del título con el agente (por defecto: 43,4 %)", "No llega al 5 %: falla con "
            "títulos cortos o con dibujo detrás, aunque se leen a simple vista.")]
for i, (val, cap, concl) in enumerate(bloques):
    x = MARGEN + i * 4.1
    cifra(s, x, 1.95, 3.8, val, cap, size=44, pie_size=12, pie_w=3.7)
    texto(s, x, 5.95, 3.7, 1.0, concl, size=13, fuente=SUB, color=VERDE, nombre="Conclusión")
lineas(s, 0.5, 3.35, 4.0, 2.55, ["Ronda 1", "Ronda 2", "Ronda 3"],
       [("Thompson", [35.3, 34.9, 43.0]), ("Aleatorio", [35.3, 34.7, 34.8])], [VERDE, "C28F00"], tam=12)
barras(s, 4.75, 3.35, 3.9, 2.55, ["Qwen 2.5", "Phi 3.5"], [("Fieles", [85, 50])], [VERDE], maximo=115, leyenda=False,
       tam=12)
barras(s, 8.85, 3.35, 3.9, 2.55, ["Por defecto", "Agente"], [("CER", [43.4, 17.6])], [AMARILLO], maximo=60,
       formato='0.0"%"', leyenda=False, tam=12)

# =========================================================================== 12 SEGURIDAD Y SESGO
s = nueva()
encabezado(s, "Evaluación · Seguridad y sesgo", "42 de 45 portadas aptas, con una señal de sesgo")
cifra(s, MARGEN, 1.95, 5.2, "42 / 45", "portadas aptas para niños, según revisión manual", size=70, pie_size=14, pie_w=4.6)
texto(s, MARGEN, 4.15, 5.0, 0.4, "Seguridad y detección", size=17, fuente=SUB, color=VERDE, nombre="Zona 1")
texto(s, MARGEN, 4.65, 5.0, 2.2,
      [[("No aptas: ", {"fuente": SUB}), ("payaso tenebroso, fantasma triste y dragón con miedo a la oscuridad.", {})],
       [("CLIP 0,5: ", {"fuente": SUB}), ("detecta 0 de 3, y 0 de 10 en la calibración.", {})],
       [("CLIP 0,25: ", {"fuente": SUB}), ("detecta 2 de 3 y 5 de 10, y bloquea por error el 1,3 % de las aptas.", {})]],
      size=13, espacio=7, nombre="Detalle de seguridad")
flecha(s, 6.15, 2.0, 6.15, 6.9, color=LIMA, grosor=2, punta=False, nombre="Separador")
texto(s, 6.5, 1.95, 6.2, 0.4, "Género y tono de piel percibidos", size=17, fuente=SUB, color=VERDE, nombre="Zona 2")
barras(s, 6.4, 2.45, 3.2, 3.3, ["Ambiguo", "Fem.", "Masc."], [("Género", [79, 17, 4])], [VERDE], maximo=100,
       formato='0', leyenda=False, tam=12, titulo_g="Género (100 imágenes)")
barras(s, 9.65, 2.45, 3.3, 3.3, ["No aplica", "Claro", "Medio", "Oscuro"], [("Tono", [80, 17, 3, 0])], [AMARILLO],
       maximo=100, formato='0', leyenda=False, tam=12, titulo_g="Tono de piel")
texto(s, 6.5, 5.9, 6.3, 0.7, "Observación, no conclusión: 100 figuras sin rasgos definidos y un solo anotador. "
      "Cuando el modelo dibuja rasgos, tiende a la piel clara.", size=13, nombre="Advertencia")
pastilla(s, "Estudio con usuarios (E4) y SUS: pendientes", 6.5, 6.75, 4.6, h=0.42, punteada=True, size=12)

# =========================================================================== 13 LIMITACIONES
s = nueva()
encabezado(s, "Limitaciones", "Cinco limitaciones que dejamos a la vista")
imagen(s, REC / "runa_piensa.png", 11.4, 0.3, h=1.65, nombre="Runa piensa")
cols = [(MARGEN, 2.55, "Componente"), (3.35, 2.4, "Resultado actual"), (5.9, 2.7, "Meta o problema"), (8.75, 4.0, "Qué significa")]
for x, w, t in cols:
    texto(s, x, 2.05, w, 0.3, t.upper(), size=11, fuente=SUB, color=VERDE, nombre="Encabezado de columna")
flecha(s, MARGEN, 2.42, 12.75, 2.42, color=VERDE, grosor=1.5, punta=False, nombre="Línea de encabezado")
filas = [("Agente de historia", "59–80 %", "Meta: 90 %", "La persona confirma o edita los elementos antes de generar."),
         ("Paleta del motor A", "70 → 79 %", "Meta: 80 %", "«Primarios» sigue en 31,5 % tras reforzar el prompt."),
         ("Legibilidad del título", "CER 17,6 %", "Meta: 5 %", "El OCR falla con títulos cortos o con dibujo detrás; a simple vista se leen."),
         ("Filtro de imagen (CLIP)", "5 de 10 no aptas", "Detectar las no aptas", "Con 0,25 bloquea el 1,3 % de las aptas: es un filtro débil."),
         ("Evidencia con personas", "Pendiente", "Entrevistas, E4 y SUS", "Los resultados con usuarios son simulados.")]
for i, (comp, res, meta, sig) in enumerate(filas):
    y = 2.6 + i * 0.88
    if i < 4:
        marcador(s, 3.35, y + 0.4, min(ancho_pulgadas(res, 20, F_SUB), 2.4), h=0.13)
    texto(s, cols[0][0], y, cols[0][1], 0.7, comp, size=15, fuente=SUB, ancla=MSO_ANCHOR.MIDDLE, nombre="Componente")
    texto(s, cols[1][0], y, cols[1][1] + 0.2, 0.55, res, size=20, fuente=SUB, color=VERDE, ancla=MSO_ANCHOR.MIDDLE, nombre="Resultado")
    texto(s, cols[2][0], y, cols[2][1], 0.7, meta, size=13, ancla=MSO_ANCHOR.MIDDLE, nombre="Meta")
    texto(s, cols[3][0], y, cols[3][1], 0.75, sig, size=13, ancla=MSO_ANCHOR.MIDDLE, nombre="Qué significa")
    if i < 4:
        flecha(s, MARGEN, y + 0.8, 12.75, y + 0.8, color="DDDACB", grosor=1, punta=False, nombre="Separador")

# =========================================================================== 14 CONCLUSIONES
s = nueva()
encabezado(s, "Conclusiones", "De un boceto a una experiencia creativa")
deco(s, "deco_explosion", 9.8, 1.7, w=2.7)
aportes = ["Cinco propuestas comparables", "Decisiones que guían las rondas", "Agentes que se pueden verificar",
           "Límites de seguridad medidos"]
for i, a in enumerate(aportes):
    y = 2.2 + i * 0.82
    numero(s, MARGEN, y, i + 1, d=0.52)
    texto(s, MARGEN + 0.8, y, 6.8, 0.52, a, size=22, fuente=SUB, color=VERDE, ancla=MSO_ANCHOR.MIDDLE, nombre="Aporte")
texto(s, MARGEN, 5.7, 7.0, 0.9, [[("Siguiente: ", {"fuente": SUB, "color": VERDE}),
                                   ("entrevistas, estudio con usuarios y SUS, y un filtro de imagen más fuerte.", {})]],
      size=15, nombre="Próximos pasos")
imagen(s, REC / "runa_celebra.png", 8.6, 3.05, w=4.3, nombre="Runa celebra")
texto(s, MARGEN, 6.55, 7.5, 0.7, "Gracias · ¿Preguntas?", size=36, fuente=TIT, color=VERDE, nombre="Cierre")
marcador(s, MARGEN, 7.12, 4.95, h=0.12)

# ------------------------------------------------------------------ notas del presentador (las de la v1)
v1 = Presentation(str(V1))
for sl, base in zip(prs.slides, v1.slides):
    sl.notes_slide.notes_text_frame.text = base.notes_slide.notes_text_frame.text

prs.save(SALIDA)
print("guardado", SALIDA)
