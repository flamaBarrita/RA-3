"""Dibuja las texturas de catrín y catrina (maquillaje tradicional de Día de Muertos).

Sigue el diseño de docs/DISENO_CATRINES.md sobre el mapa UV de la malla
(blender/cara_base.obj). Escribe en assets/mascara/:
  textura_catrina.png, textura_catrin.png  (2048 x 2048, RGBA)
  textura.png                              (copia de la catrina, la que carga el filtro)

Uso:  python3 tools/generar_texturas_catrines.py      (requiere Pillow y numpy)
"""
import math
import os
import shutil

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL = 2048
K = 2                    # se dibuja al doble y se reduce para suavizar bordes
S = FINAL * K

OJO_DER = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
OJO_IZQ = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
BOCA_INT = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82,
            81, 80, 191]
OVALO = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
         400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
         54, 103, 67, 109]


def hexa(c, a=255):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


NEGRO = hexa("0E0B10")
HUESO = hexa("F0E4CF")
OCRE = hexa("E8B98A")
OCRE_OSCURO = hexa("C98A5E")
GRIS_MEJILLA = hexa("2A2328")
VINO = hexa("7A0F1E")
NEGRO_CUENCA = hexa("140A0E")
ROJO = hexa("C8102E")
ROJO_OSCURO = hexa("7A0F1E")
ROJO_BRILLO = hexa("E84A5F")
ROJO_PETALO = hexa("D7263D")
MARFIL = hexa("F7F1E3")
GRIS_DIENTE = hexa("BDB3A6")
VERDE = hexa("2E7D32")
VERDE_CLARO = hexa("4CAF50")
DORADO = hexa("C9A227")
BLANCO = hexa("FFFFFF")
GRIS_CLAVEL = hexa("DDD6CC")
TURQUESA = hexa("00A6A6")
CEMPA = hexa("FF8C00")
CEMPA_CLARO = hexa("FFC414")


# ---------- malla y coordenadas ----------
def leer_uvs():
    uvs = []
    for linea in open(os.path.join(RAIZ, "blender", "cara_base.obj")):
        if linea.startswith("vt "):
            u, v = map(float, linea.split()[1:3])
            uvs.append((u * S, (1 - v) * S))
    return uvs


UV = leer_uvs()
N_CARA = 468
ANILLO1 = list(range(N_CARA, N_CARA + len(OVALO)))
EXTERNO = list(range(N_CARA + len(OVALO), N_CARA + 2 * len(OVALO)))


def p(i):
    return UV[i]


def q(x, y):
    """Coordenadas de la tabla (px de 2048) a px de dibujo."""
    return (x * K, y * K)


def esp(x, y):
    """Reflejo sobre el eje de simetría (x = 1024)."""
    return (FINAL - x, y)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


# ---------- herramientas de dibujo ----------
class Lienzo:
    def __init__(self):
        self.img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    def capa(self):
        return Image.new("RGBA", (S, S), (0, 0, 0, 0))

    def pegar(self, capa, opacidad=1.0):
        if opacidad < 1:
            a = capa.getchannel("A").point(lambda v: int(v * opacidad))
            capa.putalpha(a)
        self.img.alpha_composite(capa)


def poligono_suave(d, pts, fill=None, outline=None, width=1):
    d.polygon(pts, fill=fill)
    if outline:
        d.line(pts + pts[:1], fill=outline, width=width, joint="curve")


def elipse(d, c, rx, ry, **kw):
    d.ellipse([c[0] - rx, c[1] - ry, c[0] + rx, c[1] + ry], **kw)


def hoja(d, c, largo, ancho, ang, color=VERDE, borde=NEGRO):
    pts = []
    for t in range(25):
        s = t / 24
        x = (s - 0.5) * largo
        y = math.sin(math.pi * s) * ancho / 2
        pts.append((x, y))
    pts = pts + [(x, -y) for x, y in reversed(pts[1:-1])]
    ca, sa = math.cos(ang), math.sin(ang)
    pts = [(c[0] + x * ca - y * sa, c[1] + x * sa + y * ca) for x, y in pts]
    d.polygon(pts, fill=color, outline=borde, width=3 * K)
    a = (c[0] - largo * 0.45 * ca, c[1] - largo * 0.45 * sa)
    b = (c[0] + largo * 0.4 * ca, c[1] + largo * 0.4 * sa)
    d.line([a, b], fill=hexa("1B5E20"), width=2 * K)


def espiral(d, c, r, vueltas, color, ancho, sentido=1, ang0=0.0):
    pts = []
    n = int(60 * vueltas)
    for t in range(n + 1):
        s = t / n
        a = ang0 + sentido * s * vueltas * 2 * math.pi
        rr = r * (0.12 + 0.88 * s)
        pts.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
    d.line(pts, fill=color, width=ancho, joint="curve")
    return pts[-1]


def voluta(d, inicio, fin, curva, color, ancho, rizo=0.35, sentido=1):
    """Línea curva de inicio a fin que termina en un rizo (filigrana)."""
    (x0, y0), (x1, y1) = inicio, fin
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0), (x1 - x0)
    ctrl = (mx + nx * curva, my + ny * curva)
    pts = []
    for t in range(41):
        s = t / 40
        x = (1 - s) ** 2 * x0 + 2 * (1 - s) * s * ctrl[0] + s * s * x1
        y = (1 - s) ** 2 * y0 + 2 * (1 - s) * s * ctrl[1] + s * s * y1
        pts.append((x, y))
    d.line(pts, fill=color, width=ancho, joint="curve")
    largo = math.hypot(x1 - x0, y1 - y0)
    ang = math.atan2(y1 - ctrl[1], x1 - ctrl[0])
    r = largo * rizo * 0.5
    # el rizo arranca en el final de la curva y se enrolla hacia adentro
    cx = x1 + math.cos(ang + sentido * math.pi / 2) * r
    cy = y1 + math.sin(ang + sentido * math.pi / 2) * r
    a0 = math.atan2(y1 - cy, x1 - cx)
    pts = []
    for t in range(50):
        s = t / 49
        a = a0 + sentido * s * 1.6 * math.pi
        rr = r * (1 - 0.7 * s)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    d.line(pts, fill=color, width=ancho, joint="curve")


def corazon(d, c, w, fill, punta_arriba=False, outline=None, width=0):
    pts = []
    for t in range(80):
        a = 2 * math.pi * t / 80
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        y = y if punta_arriba else -y
        pts.append((c[0] + x * w / 32, c[1] + y * w / 32))
    d.polygon(pts, fill=fill)
    if outline:
        d.line(pts + pts[:1], fill=outline, width=width, joint="curve")


def rosa(lienzo, c, r, ang=0.0):
    """Rosa vista de frente: pétalos en espiral, de oscuro afuera a claro adentro."""
    capa = lienzo.capa()
    d = ImageDraw.Draw(capa)
    elipse(d, c, r, r, fill=ROJO_OSCURO, outline=NEGRO, width=4 * K)
    capas = 6
    for j in range(capas):
        t = j / (capas - 1)
        rr = r * (0.95 - 0.78 * t)
        n = 5 if j < 3 else 4
        color = lerp(ROJO_OSCURO, ROJO_BRILLO, t ** 0.8)
        color = tuple(int(v) for v in color)
        for k in range(n):
            a = ang + 2 * math.pi * k / n + j * 0.7
            cx = c[0] + math.cos(a) * rr * 0.35
            cy = c[1] + math.sin(a) * rr * 0.35
            # pétalo: medio disco que abraza el centro
            caja = [cx - rr * 0.7, cy - rr * 0.7, cx + rr * 0.7, cy + rr * 0.7]
            ini = math.degrees(a) - 70
            d.pieslice(caja, ini, ini + 140, fill=color)
            d.arc(caja, ini, ini + 140, fill=ROJO_OSCURO, width=max(2, int(r * 0.05)))
    espiral(d, c, r * 0.22, 1.3, ROJO_OSCURO, max(3, int(r * 0.06)), ang0=ang)
    lienzo.pegar(capa)


def clavel(lienzo, c, r, ang=0.0):
    capa = lienzo.capa()
    d = ImageDraw.Draw(capa)
    for j, (rr, col) in enumerate([(1.0, GRIS_CLAVEL), (0.82, BLANCO), (0.6, GRIS_CLAVEL),
                                    (0.45, BLANCO), (0.25, GRIS_CLAVEL)]):
        pts = []
        dientes = 28
        for t in range(dientes * 2):
            a = ang + j * 0.3 + math.pi * t / dientes
            radio = r * rr * (1.0 if t % 2 == 0 else 0.86)
            pts.append((c[0] + math.cos(a) * radio, c[1] + math.sin(a) * radio))
        d.polygon(pts, fill=col, outline=hexa("A89F94") if j == 0 else None,
                  width=2 * K if j == 0 else 0)
    lienzo.pegar(capa)


def nube(d, c, r, n=14):
    rnd = np.random.default_rng(int(c[0] * 7 + c[1]))
    for _ in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        rr = r * math.sqrt(rnd.uniform(0, 1))
        x, y = c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr
        s = rnd.uniform(5, 8) * K / 2
        d.line([(c[0], c[1]), (x, y)], fill=hexa("6B8E5A"), width=K)
        elipse(d, (x, y), s, s, fill=BLANCO, outline=GRIS_CLAVEL, width=1)


def cempasuchil(d, c, r):
    for k, col in enumerate((CEMPA, CEMPA_CLARO, CEMPA)):
        rr = r * (1 - k * 0.28)
        n = 13 - k * 3
        tam = rr * 0.34
        for j in range(n):
            a = 2 * math.pi * j / n + k * 0.4
            x, y = c[0] + math.cos(a) * rr * 0.66, c[1] + math.sin(a) * rr * 0.66
            elipse(d, (x, y), tam, tam, fill=col, outline=hexa("B85C00"), width=2 * K)
    elipse(d, c, r * 0.16, r * 0.16, fill=hexa("8A4500"))


def mascara_poligono(pts, desenfoque=0):
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    if desenfoque:
        m = m.filter(ImageFilter.GaussianBlur(desenfoque))
    return m


def capa_color(color, alfa):
    capa = Image.new("RGBA", (S, S), color[:3] + (0,))
    capa.putalpha(alfa)
    return capa


# ---------- elementos comunes ----------
def base(l, color_base, intensidad_ocre, opacidad=None):
    """Base de la calavera. opacidad < 1 deja ver más el tono de la piel."""
    capa = Lienzo()
    _base(capa, color_base, intensidad_ocre)
    l.pegar(capa.img, OPACIDAD_BASE if opacidad is None else opacidad)


def _base(l, color_base, intensidad_ocre):
    # llega hasta el borde de la cara y se desvanece suave, sin línea dura
    # en la frente sube más (hasta el nacimiento del pelo) para que no se vea cortada
    borde = []
    for o, a, e in zip(OVALO, ANILLO1, EXTERNO):
        w = min(1.0, max(0.0, (700 * K - p(o)[1]) / (330 * K)))
        t = 0.28 + 0.42 * w
        borde.append(lerp(p(o), p(a), t * 2) if t <= 0.5 else lerp(p(a), p(e), (t - 0.5) * 2))
    m = mascara_poligono(borde, 34 * K)
    l.pegar(capa_color(color_base, m))
    # franja de sombreado ocre hacia el contorno (~120 px)
    interior = m.filter(ImageFilter.GaussianBlur(110 * K))
    banda = ImageChops.subtract(m, interior).point(lambda v: min(255, int(v * 2.2 * intensidad_ocre)))
    l.pegar(capa_color(OCRE, banda))
    # sienes y bajo los pómulos, más oscuro
    sombra = Image.new("L", (S, S), 0)
    ds = ImageDraw.Draw(sombra)
    for x, y in ((330, 880), (420, 1250)):
        for cx in (x, FINAL - x):
            elipse(ds, q(cx, y), 120 * K, 170 * K, fill=255)
    sombra = ImageChops.multiply(sombra.filter(ImageFilter.GaussianBlur(60 * K)), m)
    sombra = sombra.point(lambda v: int(v * 0.55 * intensidad_ocre))
    l.pegar(capa_color(OCRE_OSCURO, sombra))
    # grano de pintura: variaciones suaves de tono para que no se vea plano
    rnd = np.random.default_rng(7)
    ruido = rnd.normal(0, 1, (S // 16, S // 16)).astype(np.float32)
    ruido = Image.fromarray(((ruido * 0.5 + 0.5).clip(0, 1) * 255).astype(np.uint8))
    ruido = ruido.resize((S, S), Image.BICUBIC).filter(ImageFilter.GaussianBlur(6 * K))
    fino = rnd.normal(0, 1, (S // 2, S // 2)).astype(np.float32)
    fino = Image.fromarray(((fino * 0.5 + 0.5).clip(0, 1) * 255).astype(np.uint8)).resize((S, S))
    for capa_ruido, fuerza, col in ((ruido, 0.10, hexa("B89A78")), (fino, 0.05, hexa("9C8A74"))):
        a = ImageChops.multiply(capa_ruido, m).point(lambda v, f=fuerza: int(v * f))
        l.pegar(capa_color(col, a))


def contorno_negro(l, hueco_corona=None):
    """Negro desde el óvalo hacia afuera, desvaneciéndose en los anillos."""
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    oval = [p(i) for i in OVALO]
    a1 = [p(i) for i in ANILLO1]
    ex = [p(i) for i in EXTERNO]
    pasos = 24
    for k in range(pasos, -1, -1):
        t = k / pasos
        if t <= 0.5:
            pts = [lerp(o, a, t * 2) for o, a in zip(oval, a1)]
        else:
            pts = [lerp(a, e, (t - 0.5) * 2) for a, e in zip(a1, ex)]
        alfa = 1 - (t ** 1.6)
        d.polygon(pts, fill=NEGRO[:3] + (int(255 * alfa),))
    # se quita lo que cae dentro del óvalo (para no tapar la cara)
    m = mascara_poligono(oval)
    a = ImageChops.subtract(capa.getchannel("A"), m)
    capa.putalpha(a)
    l.pegar(capa)
    # borde negro definido sobre el óvalo
    d = ImageDraw.Draw(l.img)
    d.line(oval + oval[:1], fill=NEGRO[:3] + (200,), width=5 * K, joint="curve")


def mejillas_hundidas(l, fuerza=0.4):
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    for lado in (1, -1):
        def X(x):
            return x if lado == 1 else FINAL - x
        pts = [q(X(330), 1010), q(X(450), 1100), q(X(580), 1180), q(X(700), 1235)]
        d.line(pts, fill=GRIS_MEJILLA, width=60 * K, joint="curve")
        elipse(d, q(X(330), 1010), 28 * K, 28 * K, fill=GRIS_MEJILLA)
    capa = capa.filter(ImageFilter.GaussianBlur(26 * K))
    l.pegar(capa, fuerza)


OPACIDAD_BASE = 0.95   # base con color; deja ver apenas la piel

CUENCA_RX, CUENCA_RY = 140, 116   # tamaño de las cuencas (px de 2048)
CUENCA_Y = 784


def cuencas(l, festonear, color_feston=NEGRO):
    """Cuencas con profundidad: casi negras junto al ojo y rojo vino hacia la
    orilla, con un contorno fino y delineado en el ojo real."""
    for cx, ojo, signo in ((784, OJO_DER, -1), (1264, OJO_IZQ, 1)):
        c = q(cx, CUENCA_Y)
        rx, ry = CUENCA_RX * K, CUENCA_RY * K
        yy, xx = np.mgrid[0:2 * ry, 0:2 * rx]
        dist = np.sqrt(((xx - rx) / rx) ** 2 + ((yy - ry) / ry) ** 2)
        t = np.clip(dist, 0, 1)
        humo = np.array(hexa("1A0C10")[:3], np.float32)
        vino = np.array(VINO[:3], np.float32)
        rosado = np.array(hexa("A8323F")[:3], np.float32)
        a = np.clip((t - 0.4) / 0.38, 0, 1)[..., None]
        b = np.clip((t - 0.75) / 0.25, 0, 1)[..., None]
        col = humo * (1 - a) + vino * a
        col = col * (1 - b) + rosado * b
        # sombra interior en la orilla para que se vea hundida
        orilla = np.clip((t - 0.9) / 0.1, 0, 1)[..., None]
        col = col * (1 - 0.35 * orilla)
        alfa = np.clip((1 - t) * 40, 0, 1) * 255
        bloque = np.dstack([col.clip(0, 255).astype(np.uint8), alfa.astype(np.uint8)])
        capa = l.capa()
        capa.paste(Image.fromarray(bloque, "RGBA"), (int(c[0] - rx), int(c[1] - ry)))
        d = ImageDraw.Draw(capa)
        if festonear:
            n = 24
            for k in range(n):
                ang = 2 * math.pi * k / n
                x = c[0] + math.cos(ang) * (rx + 6 * K)
                y = c[1] + math.sin(ang) * (ry + 6 * K)
                elipse(d, (x, y), 15 * K, 15 * K, fill=color_feston)
        elipse(d, c, rx, ry, outline=NEGRO, width=6 * K)
        # delineado del ojo con una pequeña cola hacia afuera
        contorno = [p(i) for i in ojo]
        d.line(contorno + contorno[:1], fill=NEGRO, width=6 * K, joint="curve")
        # brillo suave arriba, como en el maquillaje con sombra
        brillo = l.capa()
        db = ImageDraw.Draw(brillo)
        elipse(db, (c[0], c[1] - ry * 0.62), rx * 0.42, ry * 0.12, fill=(255, 210, 210, 70))
        brillo = brillo.filter(ImageFilter.GaussianBlur(8 * K))
        capa.alpha_composite(brillo)
        l.pegar(capa)


def petalos_cuencas(l):
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    for cx in (784, 1264):
        c = q(cx, CUENCA_Y)
        rx, ry = CUENCA_RX * K, CUENCA_RY * K
        n = 10
        for k in range(n):
            a = 2 * math.pi * k / n + math.pi / n
            bx = c[0] + math.cos(a) * rx * 0.98
            by = c[1] + math.sin(a) * ry * 0.98
            largo, ancho = 78 * K, 48 * K
            pts = []
            for t in range(31):
                s = t / 30
                x = s * largo
                y = math.sin(math.pi * s) ** 0.8 * ancho / 2 * (1 - 0.5 * s)
                pts.append((x, y))
            pts = pts + [(x, -y) for x, y in reversed(pts[1:-1])]
            ang = math.atan2(math.sin(a) * rx, math.cos(a) * ry)
            ca, sa = math.cos(ang), math.sin(ang)
            pts = [(bx + x * ca - y * sa, by + x * sa + y * ca) for x, y in pts]
            d.polygon(pts, fill=ROJO_PETALO, outline=NEGRO, width=4 * K)
            d.line([(bx, by), (bx + largo * 0.6 * ca, by + largo * 0.6 * sa)], fill=ROJO_OSCURO, width=3 * K)
    l.pegar(capa)


def perlas_cuencas(l):
    d = ImageDraw.Draw(l.img)
    for cx in (784, 1264):
        c = q(cx, CUENCA_Y)
        rx, ry = (CUENCA_RX + 30) * K, (CUENCA_RY + 30) * K
        for k in range(12):
            a = math.radians(20 + k * (140 / 11))
            x, y = c[0] + math.cos(a) * rx, c[1] + math.sin(a) * ry
            elipse(d, (x, y), 6 * K, 6 * K, fill=BLANCO, outline=NEGRO, width=K)


def nariz(l):
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    c = q(1024, 1072)
    w = (1144 - 903) * K * 0.95
    corazon(d, c, w, NEGRO, punta_arriba=True)
    corazon(d, (c[0], c[1] + 10 * K), w * 0.45, hexa("5A0A14"), punta_arriba=True)
    for lado in (1, -1):
        base_x = c[0] + lado * w * 0.48
        for k in range(3):
            ini = (base_x, c[1] + (k - 1) * 28 * K)
            fin = (base_x + lado * 55 * K, c[1] + (k - 1) * 40 * K - 20 * K)
            voluta(d, ini, fin, 0.25 * lado, NEGRO, 4 * K, rizo=0.4, sentido=lado)
    l.pegar(capa)


def dientes(l):
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    x0, x1, ym = 760, 1288, 1285

    def mordida(x):
        s = (x - 1024) / (x1 - 1024)
        return ym - 30 * s * s

    def alto_sup(x):
        s = abs((x - 1024) / (x1 - 1024))
        return 80 * (1 - 0.45 * s * s)

    def alto_inf(x):
        s = abs((x - 1024) / (x1 - 1024))
        return 90 * (1 - 0.5 * s * s)

    # fondo negro de la boca (separaciones entre dientes)
    xs = np.linspace(x0, x1, 60)
    arriba = [q(x, mordida(x) - alto_sup(x) - 6) for x in xs]
    abajo = [q(x, mordida(x) + alto_inf(x) + 6) for x in reversed(xs)]
    d.polygon(arriba + abajo, fill=NEGRO)

    # anchos: más anchos al centro
    n = 16
    pesos = [1 - 0.55 * abs((k + 0.5) / n * 2 - 1) ** 1.5 for k in range(n)]
    total = sum(pesos)
    hueco = 5
    x = x0
    for k, w in enumerate(pesos):
        ancho = (x1 - x0) * w / total
        xa, xb = x + hueco / 2, x + ancho - hueco / 2
        xc = (xa + xb) / 2
        yb = mordida(xc)
        for arriba_fila, alto in ((True, alto_sup(xc)), (False, alto_inf(xc))):
            if arriba_fila:
                caja = [q(xa, yb - alto)[0], q(xa, yb - alto)[1], q(xb, yb - 3)[0], q(xb, yb - 3)[1]]
            else:
                caja = [q(xa, yb + 3)[0], q(xa, yb + 3)[1], q(xb, yb + alto)[0], q(xb, yb + alto)[1]]
            radio = min(ancho * 0.35, 10) * K
            d.rounded_rectangle(caja, radius=radio, fill=MARFIL, outline=NEGRO, width=4 * K)
            # sombreado gris en la base del diente (junto a la encía)
            if arriba_fila:
                sb = [caja[0] + 4 * K, caja[1] + 4 * K, caja[2] - 4 * K, caja[1] + 16 * K]
            else:
                sb = [caja[0] + 4 * K, caja[3] - 16 * K, caja[2] - 4 * K, caja[3] - 4 * K]
            d.rounded_rectangle(sb, radius=radio * 0.6, fill=GRIS_DIENTE)
        x += ancho

    # línea de encía y hueso, y mandíbula que sube al pómulo
    sup = [q(x, mordida(x) - alto_sup(x) - 8) for x in xs]
    inf = [q(x, mordida(x) + alto_inf(x) + 8) for x in xs]
    d.line(sup, fill=NEGRO, width=8 * K, joint="curve")
    d.line(inf, fill=NEGRO, width=8 * K, joint="curve")
    for lado in (1, -1):
        xe = x1 if lado == 1 else x0
        ye = mordida(xe)
        pts = []
        for t in range(30):
            s = t / 29
            px = xe + lado * (70 * math.sin(s * math.pi / 2))
            py = ye - 210 * s
            pts.append(q(px, py))
        d.line(pts, fill=NEGRO, width=8 * K, joint="curve")
        # pequeños rayados de los dientes de atrás sobre la mejilla
        for k in range(3):
            s = (k + 1) / 4
            xx = xe + lado * (70 * math.sin(s * math.pi / 2))
            yy = ye - 210 * s
            d.line([q(xx, yy), q(xx - lado * 30, yy + 4)], fill=NEGRO, width=5 * K)
    l.pegar(capa)


def filigrana_comun(l, color_voluta=NEGRO):
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    for lado in (1, -1):
        def Q(x, y):
            return q(x if lado == 1 else FINAL - x, y)
        s = lado
        # sienes
        voluta(d, Q(520, 700), Q(380, 860), -0.35 * s, color_voluta, 5 * K, sentido=-s)
        voluta(d, Q(440, 760), Q(360, 1000), 0.3 * s, color_voluta, 4 * K, sentido=s)
        espiral(d, Q(400, 640), 32 * K, 1.4, color_voluta, 5 * K, sentido=s)
        hoja(d, Q(470, 700), 46 * K, 20 * K, math.radians(-30 if lado == 1 else 210), VERDE_CLARO)
        hoja(d, Q(390, 920), 40 * K, 18 * K, math.radians(70 if lado == 1 else 110), VERDE)
        # alrededor de la cuenca, por arriba
        voluta(d, Q(650, 655), Q(560, 730), 0.3 * s, color_voluta, 4 * K, sentido=s)
        # bajo la cuenca, hacia el pómulo
        voluta(d, Q(700, 925), Q(560, 1000), -0.3 * s, color_voluta, 4 * K, sentido=-s)
        hoja(d, Q(640, 960), 36 * K, 16 * K, math.radians(20 if lado == 1 else 160), VERDE_CLARO)
    l.pegar(capa)


def huecos(l):
    m = Image.new("L", (S, S), 255)
    dm = ImageDraw.Draw(m)
    for hueco in (OJO_DER, OJO_IZQ, BOCA_INT):
        dm.polygon([p(i) for i in hueco], fill=0)
    alfa = ImageChops.multiply(l.img.getchannel("A"), m)
    l.img.putalpha(alfa)


def guardar(l, nombre):
    img = l.img.resize((FINAL, FINAL), Image.LANCZOS)
    ruta = os.path.join(RAIZ, "assets", "mascara", nombre)
    img.save(ruta, optimize=True)
    print("escrito", ruta)
    return ruta


# ---------- variantes ----------
def catrin():
    """Catrín: cuencas negras con rojo abajo, cruz negra con hojas verdes en la
    frente, nariz de corazón rojo con puntitos, dientes grandes y mejillas
    oscuras con filigrana roja y verde. Sin flores."""
    l = Lienzo()
    base(l, hexa("D4C8B6"), 0.8, opacidad=0.93)
    mejillas_hundidas(l, 0.35)
    cuencas_catrin(l)
    frente_catrin(l)
    mejillas_catrin(l)
    nariz_catrin(l)
    dientes(l)
    barbilla_catrin(l)
    huecos(l)
    return guardar(l, "textura_catrin.png")


def cuencas_catrin(l):
    """Cuencas redondeadas en forma de gota hacia la sien: negras junto al ojo,
    vino y rojo hacia abajo, con orilla roja fina y brillos."""
    for lado in (1, -1):
        cx, cy, rx, ry = (792 if lado == 1 else FINAL - 792), 795, 178, 140

        def forma(extra=0):
            pts = []
            for t in range(180):
                a = 2 * math.pi * t / 180
                c, s_ = math.cos(a), math.sin(a)
                ancho = (rx + extra) * (1.12 if c * lado < 0 else 0.95)   # más larga hacia la sien
                alto = (ry + extra) * (0.82 if s_ < 0 else 1.0)            # arriba sigue la ceja
                y = s_ * alto - (abs(c) ** 3) * 18 * (1 if c * lado < 0 else 0)  # la punta sube a la sien
                pts.append(q(cx + c * ancho, cy + y))
            return pts

        # orilla roja fina por fuera
        capa = l.capa()
        ImageDraw.Draw(capa).polygon(forma(16), fill=hexa("B0142C"))
        capa.putalpha(ImageChops.subtract(capa.getchannel("A"), mascara_poligono(forma(8))))
        l.pegar(capa.filter(ImageFilter.GaussianBlur(1 * K)))
        # relleno: negro arriba que baja a vino y rojo, con borde suave
        m = mascara_poligono(forma(), 4 * K)
        yy = np.arange(S, dtype=np.float32)[:, None] / K
        t = np.clip((yy - (cy - 10)) / (ry + 10), 0, 1) ** 1.4
        negro = np.array(hexa("120A0E")[:3], np.float32)
        vino = np.array(hexa("6E0E1E")[:3], np.float32)
        rojo = np.array(hexa("C8203A")[:3], np.float32)
        col = np.where(t[..., None] < 0.55, negro + (vino - negro) * (t[..., None] / 0.55),
                       vino + (rojo - vino) * ((t[..., None] - 0.55) / 0.45))
        col = np.repeat(np.broadcast_to(col, (S, 1, 3)), S, axis=1)
        capa = Image.fromarray(col.astype(np.uint8), "RGB").convert("RGBA")
        capa.putalpha(m)
        l.pegar(capa)
        # brillos: arco blanco abajo y gotita en la sien
        d = ImageDraw.Draw(l.img)
        caja = [q(cx - rx * 0.8, cy - ry * 0.7)[0], q(cx - rx * 0.8, cy - ry * 0.7)[1],
                q(cx + rx * 0.8, cy + ry * 0.85)[0], q(cx + rx * 0.8, cy + ry * 0.85)[1]]
        d.arc(caja, 60 if lado == 1 else 70, 110 if lado == 1 else 120, fill=(255, 255, 255, 200), width=5 * K)
        punta = (cx - lado * rx * 1.0, cy + ry * 0.25)
        elipse(d, q(*punta), 6 * K, 6 * K, fill=BLANCO)
        # puntitos blancos bajo la cuenca
        for k in range(5):
            a = math.radians(55 + k * 18)
            x = cx + math.cos(a) * (rx + 38) * (-lado if k < 0 else 1) * 0.95
            elipse(d, q(cx + (x - cx) * lado, cy + math.sin(a) * (ry + 34)), 5 * K, 5 * K, fill=BLANCO)


def frente_catrin(l):
    d = ImageDraw.Draw(l.img)
    # cruz negra con rombo rojo al centro
    cx, cy = 1024, 500
    d.polygon([q(cx - 14, cy - 80), q(cx + 14, cy - 80), q(cx + 14, cy - 16), q(cx + 60, cy - 16),
               q(cx + 60, cy + 14), q(cx + 14, cy + 14), q(cx + 14, cy + 90), q(cx - 14, cy + 90),
               q(cx - 14, cy + 14), q(cx - 60, cy + 14), q(cx - 60, cy - 16), q(cx - 14, cy - 16)],
              fill=NEGRO)
    for px, py in ((cx, cy - 86), (cx, cy + 96), (cx - 66, cy - 1), (cx + 66, cy - 1)):
        d.polygon([q(px, py - 14), q(px + 12, py), q(px, py + 14), q(px - 12, py)], fill=NEGRO)
    d.polygon([q(cx, cy - 26), q(cx + 18, cy - 1), q(cx, cy + 24), q(cx - 18, cy - 1)], fill=ROJO)
    # hojitas verdes bajo la cruz, entre las cejas
    for ang, dx in ((90, 0), (120, -26), (60, 26)):
        hoja(d, q(cx + dx, cy + 150), 60 * K, 22 * K, math.radians(ang), VERDE_CLARO, borde=VERDE)
    # abanico de hojas verdes sobre cada ceja, como en la foto
    for lado in (1, -1):
        for fila, (radio, n, largo, color) in enumerate(((250, 7, 66, VERDE_CLARO), (318, 8, 58, VERDE))):
            for k in range(n):
                a = math.radians(200 + (330 - 200) * k / (n - 1))
                x = 790 + math.cos(a) * radio * 1.05
                y = 800 + math.sin(a) * radio * 0.95
                if lado == -1:
                    x = FINAL - x
                ang = math.atan2(math.sin(a), math.cos(a) * lado)
                hoja(d, q(x, y), largo * K, 22 * K, ang, color, borde=hexa("1B5E20"))
        # puntitos rojos y blancos en la sien
        for k in range(4):
            x = 560 - k * 30
            elipse(d, q(x if lado == 1 else FINAL - x, 600 + k * 34), 8 * K, 8 * K,
                   fill=ROJO if k % 2 == 0 else BLANCO)


def mejillas_catrin(l):
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    for lado in (1, -1):
        def Q(x, y):
            return q(x if lado == 1 else FINAL - x, y)
        # sombra negra que baja junto a la boca, con una franja roja adentro
        # curva suave (Bézier) más gruesa al centro, como en la foto
        p0, p1, p2, p3 = (730, 1030), (590, 1120), (600, 1330), (800, 1385)
        for k in range(121):
            t = k / 120
            x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0]
            y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1]
            r = 10 + 34 * math.sin(math.pi * t) ** 0.8
            elipse(d, Q(x, y), r * K, r * K, fill=NEGRO)
            if 0.2 < t < 0.8:
                rr = r * 0.4
                elipse(d, Q(x + 6, y), rr * K, rr * K, fill=hexa("8E1B2E"))
    l.pegar(capa.filter(ImageFilter.GaussianBlur(2 * K)))
    d = ImageDraw.Draw(l.img)
    for lado in (1, -1):
        def Q(x, y):
            return q(x if lado == 1 else FINAL - x, y)
        # filigrana roja y verde en el pómulo
        espiral(d, Q(520, 1010), 36 * K, 1.5, ROJO, 7 * K, sentido=lado)
        voluta(d, Q(560, 980), Q(760, 1000), -0.3 * lado, ROJO, 6 * K, sentido=-lado)
        hoja(d, Q(470, 1080), 64 * K, 22 * K, math.radians(110 if lado == 1 else 70), VERDE_CLARO, borde=VERDE)
        hoja(d, Q(520, 1130), 56 * K, 20 * K, math.radians(80 if lado == 1 else 100), VERDE, borde=hexa("1B5E20"))
        for k in range(3):
            elipse(d, Q(600 + k * 40, 1050 + k * 6), 7 * K, 7 * K, fill=BLANCO)
        # rayitas verdes y rojas hacia la mandíbula
        for k in range(3):
            y = 1300 + k * 50
            d.line([Q(520 - k * 10, y), Q(470 - k * 14, y + 30)], fill=VERDE_CLARO if k % 2 else ROJO, width=7 * K)


def nariz_catrin(l):
    d = ImageDraw.Draw(l.img)
    c = q(1024, 1050)
    w = 230 * K
    corazon(d, c, w, NEGRO, punta_arriba=True)
    corazon(d, (c[0], c[1] + 6 * K), w * 0.82, ROJO, punta_arriba=True)
    corazon(d, (c[0], c[1] + 22 * K), w * 0.36, hexa("5A0A14"), punta_arriba=True)
    # puntitos blancos siguiendo el borde
    for k in range(9):
        t = k / 8
        for lado in (1, -1):
            x = 1024 + lado * (8 + 70 * t)
            y = 975 + 95 * t
            elipse(d, q(x, y), 5 * K, 5 * K, fill=BLANCO)


def barbilla_catrin(l):
    d = ImageDraw.Draw(l.img)
    cx, cy = 1024, 1585
    for ang, largo in ((-90, 100), (-130, 80), (-50, 80)):
        hoja(d, q(cx + math.cos(math.radians(ang)) * 30, cy + math.sin(math.radians(ang)) * 30), largo * K,
             36 * K, math.radians(ang), ROJO, borde=hexa("7A0F1E"))
    elipse(d, q(cx, cy), 16 * K, 16 * K, fill=ROJO_OSCURO)
    for lado in (1, -1):
        voluta(d, q(cx + lado * 30, cy + 10), q(cx + lado * 140, cy - 20), 0.3 * lado, ROJO, 6 * K,
               sentido=-lado)
        hoja(d, q(cx + lado * 120, cy + 30), 56 * K, 20 * K, math.radians(0 if lado == 1 else 180),
             VERDE_CLARO, borde=VERDE)


def catrina():
    l = Lienzo()
    base(l, hexa("DCCDB6"), 1.0)
    mejillas_hundidas(l)
    filigrana_comun(l)
    cuencas(l, festonear=False)
    petalos_cuencas(l)
    nariz(l)
    dientes(l)

    # lágrimas turquesa bajo cada ojo
    d = ImageDraw.Draw(l.img)
    for lado in (1, -1):
        for k in range(3):
            x = 700 - k * 34 if lado == 1 else FINAL - (700 - k * 34)
            y = 960 + k * 30
            c = q(x, y)
            r = (14 - k * 2) * K
            d.polygon([(c[0], c[1] - r * 2.1), (c[0] - r * 0.9, c[1] - r * 0.3), (c[0] + r * 0.9, c[1] - r * 0.3)],
                      fill=TURQUESA)
            elipse(d, c, r, r, fill=TURQUESA, outline=NEGRO, width=2 * K)
            elipse(d, (c[0] - r * 0.35, c[1] - r * 0.35), r * 0.3, r * 0.3, fill=BLANCO)

    # frente: rosa grande, dos rositas por lado, hojas, filigrana y puntitos rojos
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    for lado in (1, -1):
        def Q(x, y):
            return q(x if lado == 1 else FINAL - x, y)
        voluta(d, Q(930, 560), Q(720, 590), 0.25 * lado, NEGRO, 5 * K, sentido=-lado)
        voluta(d, Q(900, 470), Q(760, 430), -0.3 * lado, NEGRO, 4 * K, sentido=lado)
        hoja(d, Q(880, 470), 70 * K, 30 * K, math.radians(-15 if lado == 1 else 195))
        hoja(d, Q(905, 590), 60 * K, 26 * K, math.radians(25 if lado == 1 else 155), VERDE_CLARO)
        for k in range(5):
            elipse(d, Q(700 + k * 40, 640 - 6 * k), 6 * K, 6 * K, fill=ROJO)
        # cejas: filigrana roja fina
        ceja = [Q(602, 640), Q(700, 600), Q(820, 580), Q(933, 585)]
        d.line(ceja, fill=NEGRO, width=5 * K, joint="curve")
        for pt in ceja:
            elipse(d, pt, 6 * K, 6 * K, fill=ROJO)
    l.pegar(capa)
    for lado in (1, -1):
        x1, x2 = (918, 840) if lado == 1 else (FINAL - 918, FINAL - 840)
        rosa(l, q(x1, 540), 35 * K, ang=0.5 * lado)
        rosa(l, q(x2, 470), 30 * K, ang=1.2 * lado)
    rosa(l, q(1024, 520), 80 * K)

    # mejilla derecha de la persona (izquierda de la imagen): ramito de dos rosas
    capa = l.capa()
    d = ImageDraw.Draw(capa)
    hoja(d, q(560, 1130), 70 * K, 28 * K, math.radians(140))
    hoja(d, q(690, 1140), 64 * K, 26 * K, math.radians(30), VERDE_CLARO)
    hoja(d, q(620, 1010), 54 * K, 22 * K, math.radians(-80))
    l.pegar(capa)
    rosa(l, q(595, 1070), 42 * K, ang=0.3)
    rosa(l, q(660, 1110), 34 * K, ang=1.4)
    # la otra mejilla: filigrana fina
    d = ImageDraw.Draw(l.img)
    espiral(d, q(1450, 1090), 34 * K, 1.5, NEGRO, 4 * K, sentido=-1)
    hoja(d, q(1400, 1050), 36 * K, 15 * K, math.radians(200), VERDE_CLARO)

    # barbilla: corazón rojo con filigrana
    corazon(d, q(1024, 1580), 60 * K, ROJO, outline=NEGRO, width=4 * K)
    for lado in (1, -1):
        voluta(d, q(1024 + lado * 40, 1580), q(1024 + lado * 120, 1560), 0.3 * lado, NEGRO, 4 * K,
               sentido=-lado)

    corona(l)
    huecos(l)
    return guardar(l, "textura_catrina.png")


def corona(l):
    """Tocado de rosas, claveles, nube y cempasúchil sobre los anillos de arriba."""
    a1 = [p(i) for i in ANILLO1]
    ex = [p(i) for i in EXTERNO]
    oval = [p(i) for i in OVALO]
    # puntos del arco: en el óvalo los índices 0..7 y 29..35 son la parte de arriba
    arco = list(range(29, 36)) + list(range(0, 9))

    def en_anillo(k, t):
        o, a, e = oval[k], a1[k], ex[k]
        if t <= 0.5:
            return lerp(o, a, t * 2)
        return lerp(a, e, (t - 0.5) * 2)

    d = ImageDraw.Draw(l.img)
    for j, k in enumerate(arco):
        c = en_anillo(k, 0.35)
        ang = math.atan2(c[1] - S / 2, c[0] - S / 2)
        hoja(d, en_anillo(k, 0.62), 70 * K, 28 * K, ang + 0.6 * (1 if j % 2 else -1))
    for j, k in enumerate(arco):
        c = en_anillo(k, 0.5)
        nube(d, c, 40 * K, 12)
    flores = []
    for j, k in enumerate(arco):
        c = en_anillo(k, 0.42)
        lateral = j < 3 or j > len(arco) - 4
        tipo = "rosa" if j % 2 == 0 else "clavel"
        if j in (2, len(arco) - 3, 5, len(arco) - 6):
            tipo = "cempa"
        r = (78 if lateral else 64) * K
        flores.append((tipo, c, r, j))
    for tipo, c, r, j in flores:
        if tipo == "rosa":
            rosa(l, c, r, ang=j * 0.9)
        elif tipo == "clavel":
            clavel(l, c, r * 0.9, ang=j * 0.5)
        else:
            cempasuchil(ImageDraw.Draw(l.img), c, r * 0.75)
    d = ImageDraw.Draw(l.img)
    for j, k in enumerate(arco[:-1]):
        c = lerp(en_anillo(k, 0.3), en_anillo(arco[j + 1], 0.3), 0.5)
        nube(d, c, 26 * K, 8)


def main():
    catrin()
    ruta = catrina()
    shutil.copy(ruta, os.path.join(RAIZ, "assets", "mascara", "textura.png"))
    print("textura.png = catrina")


if __name__ == "__main__":
    main()
