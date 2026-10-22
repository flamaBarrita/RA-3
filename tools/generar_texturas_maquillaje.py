"""Texturas de catrín y catrina estilo maquillaje (pintura sobre la piel real).

En lugar de una calavera blanca opaca, se pinta como maquillaje de Día de
Muertos: un velo claro que deja ver la piel y cubre toda la cara, sombras de
color alrededor de los ojos con pedrería, nariz y labios de color, costuras
finas en la boca, filigrana en mejillas y, en la catrina, corona de rosas.
Sin contornos negros.

Escribe en assets/mascara/:
  textura_catrina.png, textura_catrin.png  (2048 x 2048, RGBA)
  textura.png                              (copia de la catrina)

Uso:  python3 tools/generar_texturas_maquillaje.py      (requiere Pillow y numpy)
"""
import math
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generar_texturas_catrines import (  # noqa: E402
    ANILLO1, EXTERNO, FINAL, K, OJO_DER, OJO_IZQ, OVALO, RAIZ, S, Lienzo, capa_color, elipse,
    espiral, guardar, hexa, huecos, lerp, mascara_poligono, p, q,
)

LABIOS = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181,
          91, 146]
OJO_C = {1: (790, 792), -1: (FINAL - 790, 792)}   # centro de cada ojo (px de 2048)


def X(x, lado):
    return x if lado == 1 else FINAL - x


def tono(c, f):
    """Aclara (f > 1) u oscurece (f < 1) un color."""
    if f >= 1:
        return tuple(int(v + (255 - v) * (f - 1)) for v in c[:3]) + c[3:]
    return tuple(int(v * f) for v in c[:3]) + c[3:]


def en_anillo(k, t):
    """Punto k del contorno: t = 0 en el óvalo, 0.5 en el primer anillo, 1 en el externo."""
    o, a, e = p(OVALO[k]), p(ANILLO1[k]), p(EXTERNO[k])
    return lerp(o, a, t * 2) if t <= 0.5 else lerp(a, e, (t - 0.5) * 2)


# ---------- velo de la cara ----------
def velo(l, color, alfa, sombra):
    """Base clara translúcida que llega al borde de la cara y se desvanece."""
    m = mascara_poligono([en_anillo(k, 0.12) for k in range(len(OVALO))], 22 * K)
    l.pegar(capa_color(color, m.point(lambda v: int(v * alfa))))
    # contorno suave: sienes, bajo los pómulos y mandíbula
    s = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(s)
    for lado in (1, -1):
        elipse(d, q(X(330, lado), 860), 110 * K, 170 * K, fill=255)
        d.line([q(X(400, lado), 1150), q(X(560, lado), 1250), q(X(700, lado), 1300)],
               fill=255, width=90 * K, joint="curve")
    s = ImageChops.multiply(s.filter(ImageFilter.GaussianBlur(55 * K)), m)
    l.pegar(capa_color(sombra, s.point(lambda v: int(v * 0.35))))
    # grano fino: que no se vea plano
    rnd = np.random.default_rng(3)
    ruido = rnd.normal(0, 1, (S // 24, S // 24)).astype(np.float32)
    ruido = Image.fromarray(((ruido * 0.5 + 0.5).clip(0, 1) * 255).astype(np.uint8))
    ruido = ruido.resize((S, S), Image.BICUBIC)
    l.pegar(capa_color(tono(color, 0.8), ImageChops.multiply(ruido, m).point(lambda v: int(v * 0.07))))


# ---------- sombras de ojos ----------
def forma_ojo(lado, rx, ry, y0=0):
    """Óvalo redondeado alrededor del ojo, un poco más ancho hacia la sien."""
    cx, cy = OJO_C[lado]
    pts = []
    for t in range(120):
        a = 2 * math.pi * t / 120
        x, y = math.cos(a), math.sin(a)
        ancho = rx * (1.12 if x * lado < 0 else 0.92)   # hacia la sien (x < 0 para lado 1)
        alto = ry * (1.0 if y < 0 else 0.92)
        pts.append(q(cx + x * ancho, cy + y0 + y * alto))
    return pts


def sombra_ojos(l, centro, medio, orilla, rx=205, ry=175, brillo=True):
    rnd = np.random.default_rng(11)
    for lado in (1, -1):
        cx, cy = OJO_C[lado]
        m = mascara_poligono(forma_ojo(lado, rx, ry), 14 * K)
        # degradado radial: oscuro junto al ojo, claro en la orilla
        yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
        x0, y0 = cx * K, cy * K
        r = np.sqrt(((xx - x0) / (rx * K)) ** 2 + ((yy - y0) / (ry * K)) ** 2)
        t = np.clip((r - 0.25) / 0.75, 0, 1)[..., None]
        c1, c2, c3 = (np.array(c[:3], np.float32) for c in (centro, medio, orilla))
        col = np.where(t < 0.5, c1 + (c2 - c1) * (t / 0.5), c2 + (c3 - c2) * ((t - 0.5) / 0.5))
        img = np.dstack([col, np.array(m, np.float32)[..., None] * 0.92]).astype(np.uint8)
        l.pegar(Image.fromarray(img, "RGBA"))
        del yy, xx, r, t, col, img
        if brillo:
            # destellos finos (shimmer)
            capa = l.capa()
            d = ImageDraw.Draw(capa)
            for _ in range(260):
                a = rnd.uniform(0, 2 * math.pi)
                rr = math.sqrt(rnd.uniform(0.1, 0.9))
                x, y = cx + math.cos(a) * rr * rx, cy + math.sin(a) * rr * ry
                s = rnd.uniform(1.2, 3) * K
                elipse(d, q(x, y), s, s, fill=(255, 255, 255, int(rnd.uniform(40, 130))))
            l.pegar(capa)
    # delineado junto al ojo, con una pequeña cola
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    for ojo, lado in ((OJO_DER, 1), (OJO_IZQ, -1)):
        pts = [p(i) for i in ojo]
        d.line(pts + pts[:1], fill=tono(centro, 0.55), width=7 * K, joint="curve")
        e = p(ojo[0])
        d.line([e, (e[0] - lado * 40 * K, e[1] - 18 * K)], fill=tono(centro, 0.55), width=6 * K)
    l.pegar(capa.filter(ImageFilter.GaussianBlur(1.5 * K)), 0.85)


def gema(d, c, r, color):
    elipse(d, c, r, r, fill=tono(color, 0.6))
    elipse(d, c, r * 0.82, r * 0.82, fill=color)
    elipse(d, (c[0] - r * 0.2, c[1] - r * 0.2), r * 0.45, r * 0.4, fill=tono(color, 1.45))
    elipse(d, (c[0] - r * 0.3, c[1] - r * 0.32), r * 0.16, r * 0.16, fill=(255, 255, 255, 235))


def pedreria_ojos(l, colores, rx=212, ry=182, tam=(11, 17), arco=(200, 520)):
    """Piedritas alrededor de la sombra (desde abajo de la sien, por arriba, hasta la mejilla)."""
    rnd = np.random.default_rng(5)
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    for lado in (1, -1):
        cx, cy = OJO_C[lado]
        n = 30
        for j in range(n):
            g = math.radians(arco[0] + (arco[1] - arco[0]) * j / (n - 1))
            x, y = math.cos(g), math.sin(g)
            ancho = rx * (1.12 if x < 0 else 0.92)
            alto = ry * (1.0 if y < 0 else 0.92)
            xx = cx + (x * ancho) * lado
            r = rnd.uniform(*tam) * K
            gema(d, q(xx, cy + y * alto), r, colores[j % len(colores)])
    # sombra suave bajo las piedras: se ven puestas sobre la piel
    sombra = capa.getchannel("A").filter(ImageFilter.GaussianBlur(5 * K)).point(lambda v: int(v * 0.35))
    sombra = ImageChops.offset(sombra, 2 * K, 4 * K)
    l.pegar(capa_color((40, 20, 30, 255), sombra))
    l.pegar(capa)


def joyas(l, c, colores, grande=24):
    """Joya central en forma de gota con piedritas alrededor (frente o barbilla)."""
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    x, y = c
    r = grande
    d.polygon([q(x, y - r * 2.2), q(x - r * 0.95, y - r * 0.2), q(x + r * 0.95, y - r * 0.2)],
              fill=tono(colores[0], 0.7))
    gema(d, q(x, y), r * K, colores[0])
    for k, (dx, dy, rr) in enumerate([(0, -r * 3.2, 0.5), (-r * 1.6, r * 0.6, 0.45), (r * 1.6, r * 0.6, 0.45),
                                      (0, r * 1.8, 0.42), (-r * 1.2, -r * 1.8, 0.35), (r * 1.2, -r * 1.8, 0.35)]):
        gema(d, q(x + dx, y + dy), r * rr * K, colores[(k + 1) % len(colores)])
    sombra = capa.getchannel("A").filter(ImageFilter.GaussianBlur(5 * K)).point(lambda v: int(v * 0.35))
    l.pegar(capa_color((40, 20, 30, 255), ImageChops.offset(sombra, 2 * K, 4 * K)))
    l.pegar(capa)


# ---------- nariz, labios y costuras ----------
def nariz(l, color):
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    c = (1024, 1046)
    # punta y aletas: tres círculos que se funden
    elipse(d, q(*c), 46 * K, 40 * K, fill=color)
    for lado in (1, -1):
        elipse(d, q(c[0] + lado * 46, c[1] + 16), 32 * K, 28 * K, fill=color)
    capa = capa.filter(ImageFilter.GaussianBlur(6 * K))
    l.pegar(capa, 0.95)
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    elipse(d, q(c[0] - 10, c[1] - 16), 15 * K, 9 * K, fill=tono(color, 1.6))
    l.pegar(capa.filter(ImageFilter.GaussianBlur(6 * K)), 0.6)


def labios(l, color):
    m = mascara_poligono([p(i) for i in LABIOS], 4 * K)
    l.pegar(capa_color(color, m.point(lambda v: int(v * 0.78))))


def costuras(l, color):
    """Línea fina de comisura a comisura y hacia las mejillas, con puntadas."""
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    izq, der = p(61), p(291)
    for lado, e in ((1, izq), (-1, der)):
        fin = (e[0] - lado * 160 * K, e[1] - 30 * K)
        d.line([e, lerp(e, fin, 0.5), fin], fill=color, width=4 * K, joint="curve")
        for k in range(1, 5):
            pt = lerp(e, fin, k / 5)
            d.line([(pt[0], pt[1] - 18 * K), (pt[0], pt[1] + 18 * K)], fill=color, width=4 * K)
    # puntadas que cruzan los labios (se cortan en la boca abierta)
    sup = [p(i) for i in (40, 37, 0, 267, 270)]
    inf = [p(i) for i in (91, 84, 17, 314, 321)]
    for a, b in zip(sup, inf):
        d.line([a, b], fill=color, width=4 * K)
    l.pegar(capa.filter(ImageFilter.GaussianBlur(0.8 * K)), 0.9)


def filigrana_mejillas(l, color, puntos):
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    for lado in (1, -1):
        espiral(d, q(X(560, lado), 1185), 38 * K, 1.4, color, 4 * K, sentido=-lado)
        d.line([q(X(560, lado), 1150), q(X(520, lado), 1080), q(X(540, lado), 1010)], fill=color,
               width=4 * K, joint="curve")
        for k in range(4):
            elipse(d, q(X(600 + k * 26, lado), 1250 + k * 12), (6 - k) * K, (6 - k) * K, fill=puntos)
        # rayitas bajo el ojo, como pestañas pintadas
        for k in range(3):
            a = q(X(690 + k * 50, lado), 1000 + k * 6)
            d.line([a, (a[0], a[1] + 34 * K)], fill=color, width=3 * K)
            elipse(d, (a[0], a[1] + 40 * K), 5 * K, 5 * K, fill=puntos)
    l.pegar(capa.filter(ImageFilter.GaussianBlur(0.8 * K)), 0.9)


# ---------- flores ----------
def rosa_suave(l, c, r, base, claro, ang=0.0):
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    elipse(d, c, r, r, fill=tono(base, 0.85))
    for j in range(6):
        t = j / 5
        rr = r * (0.95 - 0.78 * t)
        color = tuple(int(v) for v in lerp(tono(base, 0.9), claro, t ** 0.8))
        for k in range(5 if j < 3 else 4):
            a = ang + 2 * math.pi * k / 5 + j * 0.7
            cx, cy = c[0] + math.cos(a) * rr * 0.35, c[1] + math.sin(a) * rr * 0.35
            caja = [cx - rr * 0.7, cy - rr * 0.7, cx + rr * 0.7, cy + rr * 0.7]
            ini = math.degrees(a) - 70
            d.pieslice(caja, ini, ini + 140, fill=color)
            d.arc(caja, ini, ini + 140, fill=tono(base, 0.7), width=max(2, int(r * 0.04)))
    espiral(d, c, r * 0.2, 1.3, tono(base, 0.65), max(3, int(r * 0.05)), ang0=ang)
    sombra = capa.getchannel("A").filter(ImageFilter.GaussianBlur(10 * K)).point(lambda v: int(v * 0.4))
    l.pegar(capa_color((30, 20, 20, 255), ImageChops.offset(sombra, 4 * K, 8 * K)))
    l.pegar(capa)


def hoja_suave(d, c, largo, ancho, ang, color):
    pts = []
    for t in range(25):
        s = t / 24
        pts.append(((s - 0.5) * largo, math.sin(math.pi * s) * ancho / 2))
    pts = pts + [(x, -y) for x, y in reversed(pts[1:-1])]
    ca, sa = math.cos(ang), math.sin(ang)
    d.polygon([(c[0] + x * ca - y * sa, c[1] + x * sa + y * ca) for x, y in pts], fill=color)
    d.line([(c[0] - largo * 0.45 * ca, c[1] - largo * 0.45 * sa),
            (c[0] + largo * 0.4 * ca, c[1] + largo * 0.4 * sa)], fill=tono(color, 0.7), width=2 * K)


def corona_rosas(l, paleta):
    """Corona de rosas en la parte de arriba (sobre el nacimiento del pelo)."""
    arco = list(range(29, 36)) + list(range(0, 9))
    d = ImageDraw.Draw(l.img)
    for j, k in enumerate(arco):
        c = en_anillo(k, 0.6)
        ang = math.atan2(c[1] - S / 2, c[0] - S / 2)
        hoja_suave(d, c, 90 * K, 36 * K, ang + 0.7 * (1 if j % 2 else -1), hexa("4E7A3A"))
    for j, k in enumerate(arco):
        lateral = j < 3 or j > len(arco) - 4
        base, claro = paleta[j % len(paleta)]
        rosa_suave(l, en_anillo(k, 0.45), (84 if lateral else 70) * K, base, claro, ang=j * 0.9)


def cempasuchil_suave(l, c, r):
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    for k, col in enumerate((hexa("E8780C"), hexa("FFB020"), hexa("FF9A10"))):
        rr = r * (1 - k * 0.28)
        n = 13 - k * 3
        for j in range(n):
            a = 2 * math.pi * j / n + k * 0.4
            elipse(d, (c[0] + math.cos(a) * rr * 0.66, c[1] + math.sin(a) * rr * 0.66), rr * 0.34,
                   rr * 0.34, fill=col)
    elipse(d, c, r * 0.16, r * 0.16, fill=hexa("8A4500"))
    sombra = capa.getchannel("A").filter(ImageFilter.GaussianBlur(6 * K)).point(lambda v: int(v * 0.35))
    l.pegar(capa_color((30, 20, 20, 255), ImageChops.offset(sombra, 3 * K, 6 * K)))
    l.pegar(capa)


# ---------- variantes ----------
CRISTALES = [hexa("E9E4F5"), hexa("B57BE0"), hexa("F2A7C8"), hexa("7FD6E6"), hexa("FFFFFF"), hexa("9A6BD6")]
ORO = [hexa("D9B24A"), hexa("F1D27A"), hexa("B88A2A"), hexa("E9E4F5")]


def catrina():
    l = Lienzo()
    velo(l, hexa("F6EEF0"), 0.8, hexa("B49AB8"))
    sombra_ojos(l, hexa("3E1660"), hexa("8B3FC2"), hexa("C9A0E8"))
    pedreria_ojos(l, CRISTALES)
    nariz(l, hexa("7A3BB0"))
    labios(l, hexa("6E2A5E"))
    costuras(l, hexa("3A1838"))
    filigrana_mejillas(l, hexa("3A1838"), hexa("8B3FC2"))
    joyas(l, (1024, 540), CRISTALES)
    joyas(l, (1024, 1560), CRISTALES, grande=14)
    corona_rosas(l, [(hexa("F08A78"), hexa("FFD2C4")), (hexa("E57FA8"), hexa("FFD0E2")),
                     (hexa("9A7AD8"), hexa("E2D4FA")), (hexa("F2A07A"), hexa("FFE0CC"))])
    huecos(l)
    return guardar(l, "textura_catrina.png")


def catrin():
    l = Lienzo()
    velo(l, hexa("F1ECE6"), 0.78, hexa("9C8A80"))
    sombra_ojos(l, hexa("3A0A14"), hexa("8E1B2E"), hexa("C2565E"), rx=195, ry=165)
    pedreria_ojos(l, ORO, rx=200, ry=170, tam=(8, 12), arco=(180, 540))
    nariz(l, hexa("5E0F1E"))
    labios(l, hexa("5A1A22"))
    costuras(l, hexa("3A1418"))
    filigrana_mejillas(l, hexa("3A1418"), hexa("C9A227"))
    joyas(l, (1024, 1560), ORO, grande=12)
    # frente: cempasúchil con hojas y puntitos dorados
    d = ImageDraw.Draw(l.img)
    for lado in (1, -1):
        hoja_suave(d, q(X(940, lado), 540), 90 * K, 34 * K, math.radians(-20 if lado == 1 else 200),
                   hexa("4E7A3A"))
        for k in range(5):
            elipse(d, q(X(880 - k * 46, lado), 600 + k * 10), 6 * K, 6 * K, fill=hexa("C9A227"))
    cempasuchil_suave(l, q(1024, 520), 70 * K)
    huecos(l)
    return guardar(l, "textura_catrin.png")


def main():
    catrin()
    ruta = catrina()
    shutil.copy(ruta, os.path.join(RAIZ, "assets", "mascara", "textura.png"))
    shutil.copy(ruta, os.path.join(RAIZ, "blender", "textura.png"))
    print("textura.png = catrina")


if __name__ == "__main__":
    main()
