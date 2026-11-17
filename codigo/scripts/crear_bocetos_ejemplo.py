"""Genera bocetos de ejemplo para probar la interfaz (`app/ejemplos/`).

Tres dibujos de cuentos (zorra, dragón con tortuga, castillo de arena) y dos defectuosos
(vacío y garabato saturado) para comprobar los avisos de error.

Uso (desde la carpeta `codigo`):  python -m scripts.crear_bocetos_ejemplo
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

SALIDA = Path(__file__).resolve().parents[1] / "app" / "ejemplos"
W, H, G = 800, 1000, 9          # lienzo y grosor de trazo


def lienzo():
    img = Image.new("L", (W, H), 255)
    return img, ImageDraw.Draw(img)


def arco(d, caja, ini, fin, g=G):
    d.arc(caja, ini, fin, fill=0, width=g)


def zorra():
    img, d = lienzo()
    d.ellipse((230, 520, 560, 800), outline=0, width=G)                       # cuerpo
    d.polygon([(560, 640), (740, 560), (770, 700), (700, 800), (560, 780)], outline=0, width=G)   # cola
    d.polygon([(700, 640), (770, 700), (740, 760), (690, 700)], outline=0, width=G)               # punta
    d.ellipse((250, 380, 470, 560), outline=0, width=G)                       # cabeza
    d.polygon([(260, 420), (250, 300), (340, 390)], outline=0, width=G)       # orejas
    d.polygon([(460, 420), (480, 300), (380, 390)], outline=0, width=G)
    d.polygon([(300, 500), (360, 580), (420, 500)], outline=0, width=G)       # hocico
    d.ellipse((345, 560, 375, 585), fill=0)
    d.ellipse((310, 450, 332, 472), fill=0); d.ellipse((398, 450, 420, 472), fill=0)
    d.line((270, 790, 270, 850), fill=0, width=G); d.line((340, 800, 340, 855), fill=0, width=G)
    d.line((430, 800, 430, 855), fill=0, width=G); d.line((500, 790, 500, 850), fill=0, width=G)
    d.ellipse((600, 70, 740, 210), outline=0, width=G)                        # luna
    d.ellipse((640, 70, 780, 210), fill=255); d.arc((640, 70, 780, 210), 100, 260, fill=0, width=G)
    for x, y in [(80, 140), (200, 90), (330, 170), (480, 80)]:                # estrellas
        d.line((x - 18, y, x + 18, y), fill=0, width=6); d.line((x, y - 18, x, y + 18), fill=0, width=6)
    for x, base, alto in [(60, 760, 300), (130, 800, 250)]:                   # árboles
        d.line((x, base, x, base + 90), fill=0, width=G)
        for k in range(3):
            d.polygon([(x - 70 + k * 12, base - k * alto // 3), (x + 70 - k * 12, base - k * alto // 3),
                       (x, base - alto // 3 - k * alto // 3)], outline=0, width=G - 2)
    for x, y in [(560, 440), (620, 380), (150, 480)]:                         # luciérnagas
        d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=0)
        for a in range(0, 360, 90):
            d.line((x + 18 * math.cos(math.radians(a)), y + 18 * math.sin(math.radians(a)),
                    x + 30 * math.cos(math.radians(a)), y + 30 * math.sin(math.radians(a))), fill=0, width=4)
    d.line((0, 900, W, 900), fill=0, width=G)
    return img


def dragon():
    img, d = lienzo()
    d.ellipse((220, 520, 560, 840), outline=0, width=G)                       # cuerpo
    d.ellipse((260, 640, 520, 820), outline=0, width=6)                       # barriga
    d.ellipse((250, 300, 480, 500), outline=0, width=G)                       # cabeza
    d.rounded_rectangle((200, 400, 340, 480), 40, outline=0, width=G)         # hocico
    d.ellipse((340, 350, 372, 382), fill=0)
    d.polygon([(290, 310), (280, 220), (340, 300)], outline=0, width=G)       # cuernos
    d.polygon([(420, 310), (450, 220), (390, 300)], outline=0, width=G)
    d.polygon([(480, 560), (680, 420), (700, 600), (600, 640)], outline=0, width=G)    # ala
    d.line((560, 840, 700, 880, 760, 800), fill=0, width=G, joint="curve")     # cola
    d.polygon([(760, 800), (800, 760), (790, 830)], outline=0, width=G)
    for x in range(300, 520, 55):                                             # púas
        d.polygon([(x, 525), (x + 22, 470), (x + 44, 525)], outline=0, width=G - 2)
    d.line((250, 830, 250, 910), fill=0, width=G); d.line((480, 830, 480, 910), fill=0, width=G)
    d.polygon([(196, 440), (150, 405), (132, 440), (80, 425), (116, 462), (66, 500), (150, 488), (192, 468)],
              outline=0, width=G - 2)                                                           # llama
    # tortuga
    d.pieslice((470, 800, 690, 960), 180, 360, outline=0, fill=255, width=G)
    d.line((470, 880, 690, 880), fill=0, width=G)
    d.ellipse((690, 850, 750, 905), outline=0, width=G)
    d.ellipse((718, 866, 730, 878), fill=0)
    d.line((520, 880, 520, 925), fill=0, width=G); d.line((640, 880, 640, 925), fill=0, width=G)
    for x in (540, 580, 620):
        d.line((x, 810, x, 880), fill=0, width=5)
    # galletas
    for x, y in [(70, 800), (170, 850)]:
        d.ellipse((x, y, x + 70, y + 70), outline=0, width=G - 3)
        for cx, cy in [(x + 22, y + 25), (x + 46, y + 40), (x + 28, y + 48)]:
            d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=0)
    return img


def castillo():
    img, d = lienzo()
    d.rectangle((250, 560, 560, 780), outline=0, width=G)                     # muro
    for x in range(250, 560, 60):                                             # almenas
        d.rectangle((x, 520, x + 30, 560), outline=0, width=G - 3)
    for x0 in (180, 560):                                                     # torres
        d.rectangle((x0, 440, x0 + 90, 780), outline=0, width=G)
        for k in range(3):
            d.rectangle((x0 + k * 32 - 4, 400, x0 + k * 32 + 24, 440), outline=0, width=G - 3)
    d.rectangle((370, 450, 440, 560), outline=0, width=G)                     # torre central
    d.line((405, 450, 405, 360), fill=0, width=G)
    d.polygon([(405, 360), (470, 385), (405, 410)], outline=0, width=G - 3)   # bandera
    d.rounded_rectangle((350, 650, 450, 780), 50, outline=0, width=G)         # puerta
    d.line((0, 790, W, 790), fill=0, width=G)
    for y, a in [(850, 0), (910, 30)]:                                        # olas
        for x in range(a - 60, W, 120):
            d.arc((x, y, x + 120, y + 60), 200, 340, fill=0, width=G - 2)
    d.ellipse((570, 90, 720, 240), outline=0, width=G)                        # sol
    for a in range(0, 360, 30):
        r1, r2 = 100, 150
        d.line((645 + r1 * math.cos(math.radians(a)), 165 + r1 * math.sin(math.radians(a)),
                645 + r2 * math.cos(math.radians(a)), 165 + r2 * math.sin(math.radians(a))), fill=0, width=6)
    # perro
    d.ellipse((60, 640, 220, 740), outline=0, width=G); d.ellipse((30, 600, 100, 670), outline=0, width=G)
    d.polygon([(40, 610), (20, 570), (60, 600)], outline=0, width=G - 2)
    d.line((220, 660, 260, 620), fill=0, width=G)
    d.line((90, 735, 90, 790), fill=0, width=G); d.line((190, 735, 190, 790), fill=0, width=G)
    # niña
    d.ellipse((620, 640, 680, 700), outline=0, width=G)
    d.polygon([(650, 700), (600, 790), (700, 790)], outline=0, width=G)
    d.line((630, 725, 590, 760), fill=0, width=G); d.line((670, 725, 710, 755), fill=0, width=G)
    return img


def vacio():
    return Image.new("L", (W, H), 255)


def garabato():
    img, d = lienzo()
    rnd = random.Random(7)
    for _ in range(700):
        d.line((rnd.randint(0, W), rnd.randint(0, H), rnd.randint(0, W), rnd.randint(0, H)), fill=0, width=14)
    return img


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    for nombre, f in [("boceto_zorro", zorra), ("boceto_dragon", dragon), ("boceto_castillo", castillo),
                      ("boceto_vacio", vacio), ("boceto_garabato", garabato)]:
        f().save(SALIDA / f"{nombre}.png")
        print("creado", nombre)


if __name__ == "__main__":
    main()
