"""Dibuja una textura PROVISIONAL de calavera para probar el filtro.

Sirve solo para ver que el mapeo funciona mientras se pinta la textura final en
Blender. Escribe assets/mascara/textura.png (2048 x 2048, con transparencia).
Cuando tengas tu textura, guárdala con ese mismo nombre y reemplaza este archivo.

Uso:  python3 tools/generar_datos_cara.py   (crea tools/uv_clave.json)
      python3 tools/generar_textura_provisional.py
"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFilter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAVE = json.load(open(os.path.join(RAIZ, "tools", "uv_clave.json")))
S = 4096      # se dibuja al doble y se reduce para suavizar los bordes
FINAL = 2048

OJO_DER = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
OJO_IZQ = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
LABIOS_EXT = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37,
              39, 40, 185]
LABIOS_INT = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82,
              81, 80, 191]
OVALO = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
         400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
         54, 103, 67, 109]

HUESO = (247, 242, 232, 255)
NEGRO = (22, 18, 30, 255)
CEMPASUCHIL = (255, 140, 0, 255)
AMARILLO = (255, 196, 20, 255)
ROSA = (232, 30, 120, 255)
MORADO = (110, 40, 160, 255)
TURQUESA = (0, 170, 180, 255)
VERDE = (40, 150, 70, 255)


def p(i):
    u, v = CLAVE[str(i)]
    return (u * S, (1 - v) * S)


def uv(par):
    u, v = par
    return (u * S, (1 - v) * S)


def centro(indices):
    pts = [p(i) for i in indices]
    return (sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts))


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def flor(d, c, r, colores=(CEMPASUCHIL, AMARILLO, CEMPASUCHIL), capas=3):
    """Flor de cempasúchil: capas de pétalos redondos alrededor de un centro."""
    for k in range(capas):
        rr = r * (1 - k * 0.28)
        n = 14 - k * 3
        tam = rr * 0.33
        col = colores[k % len(colores)]
        for j in range(n):
            a = 2 * math.pi * j / n + k * 0.4
            x, y = c[0] + math.cos(a) * rr * 0.68, c[1] + math.sin(a) * rr * 0.68
            d.ellipse([x - tam, y - tam, x + tam, y + tam], fill=col, outline=(200, 90, 0, 255), width=4)
    d.ellipse([c[0] - r * 0.18, c[1] - r * 0.18, c[0] + r * 0.18, c[1] + r * 0.18], fill=(150, 70, 0, 255))


def petalos_alrededor(d, c, r, n, tam, colores):
    for j in range(n):
        a = 2 * math.pi * j / n
        x, y = c[0] + math.cos(a) * r, c[1] + math.sin(a) * r
        col = colores[j % len(colores)]
        # pétalo alargado apuntando hacia afuera
        pts = []
        for t in range(16):
            b = 2 * math.pi * t / 16
            px, py = math.cos(b) * tam * 1.5, math.sin(b) * tam * 0.7
            pts.append((x + px * math.cos(a) - py * math.sin(a), y + px * math.sin(a) + py * math.cos(a)))
        d.polygon(pts, fill=col, outline=NEGRO, width=4)


def main():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 1. Base de hueso en toda la cara real.
    d.polygon([p(i) for i in OVALO], fill=HUESO)
    # Borde punteado de cempasúchil sobre el contorno.
    contorno = [p(i) for i in OVALO]
    for k in range(len(contorno)):
        a, b = contorno[k], contorno[(k + 1) % len(contorno)]
        for t in (0.0, 0.5):
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=CEMPASUCHIL)

    # 2. Corona de cempasúchil en los anillos de la frente y las sienes.
    externo = [uv(q) for q in CLAVE["externo"]]
    anillo = [uv(q) for q in CLAVE["anillo1"]]
    medio = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(anillo, externo)]
    ancho_anillo = dist(p(10), externo[0])
    for k in list(range(0, 8)) + list(range(29, 36)):
        c = medio[k]
        flor(d, c, ancho_anillo * 0.42)
    for k in (4, 32):  # hojas entre flores
        c = medio[k]
        d.ellipse([c[0] - 40, c[1] + 60, c[0] + 40, c[1] + 160], fill=VERDE)

    # 3. Cuencas de los ojos con pétalos de colores.
    for ojo, colores in ((OJO_DER, (ROSA, TURQUESA)), (OJO_IZQ, (ROSA, TURQUESA))):
        c = centro(ojo)
        r = dist(p(ojo[0]), p(ojo[8])) * 0.85
        petalos_alrededor(d, c, r * 1.05, 12, r * 0.2, colores)
        d.ellipse([c[0] - r, c[1] - r * 0.92, c[0] + r, c[1] + r * 0.92], fill=NEGRO)
        d.ellipse([c[0] - r * 0.86, c[1] - r * 0.78, c[0] + r * 0.86, c[1] + r * 0.78],
                  outline=CEMPASUCHIL, width=14)

    # 4. Nariz: corazón invertido negro.
    punta = p(4)
    ali_d, ali_i = p(98), p(327)
    w = dist(ali_d, ali_i) * 0.62
    cy = (ali_d[1] + ali_i[1]) / 2 - w * 0.25
    corazon = []
    for t in range(60):
        a = 2 * math.pi * t / 60
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        corazon.append((punta[0] + x * w / 32, cy + y * w / 32))  # +y: punta hacia arriba
    d.polygon(corazon, fill=NEGRO)

    # 5. Boca cosida: labios negros y puntadas.
    d.polygon([p(i) for i in LABIOS_EXT], fill=NEGRO)
    izq, der = p(61), p(291)
    sup, inf = p(0), p(17)
    alto = dist(sup, inf)
    d.line([izq, der], fill=NEGRO, width=10)
    for k in range(1, 12):
        t = k / 12
        x = izq[0] + (der[0] - izq[0]) * t
        y = izq[1] + (der[1] - izq[1]) * t
        largo = alto * (0.55 + 0.25 * math.sin(math.pi * t))
        d.line([(x, y - largo), (x, y + largo)], fill=NEGRO, width=12)

    # 6. Frente: flor central.
    frente = ((p(10)[0] + p(9)[0]) / 2, (p(10)[1] * 0.45 + p(9)[1] * 0.55))
    r_frente = dist(p(10), p(9)) * 0.42
    flor(d, frente, r_frente, (ROSA, CEMPASUCHIL, AMARILLO))

    # 7. Mejillas: espirales rosas.
    for i, signo in ((205, 1), (425, -1)):
        c = p(i)
        pts = []
        for t in range(140):
            a = t / 140 * 3.2 * math.pi
            rr = 6 + t * 1.2
            pts.append((c[0] + signo * math.cos(a) * rr, c[1] + math.sin(a) * rr))
        d.line(pts, fill=ROSA, width=16, joint="curve")

    # 8. Barbilla: pequeña flor.
    barb = p(152)
    sobre = ((barb[0] + p(17)[0]) / 2, (barb[1] + p(17)[1]) / 2 + 30)
    flor(d, sobre, alto * 0.6, (TURQUESA, AMARILLO), capas=2)

    # 9. Huecos transparentes de ojos y boca (por si la malla los cubre).
    mascara = Image.new("L", (S, S), 255)
    dm = ImageDraw.Draw(mascara)
    for hueco in (OJO_DER, OJO_IZQ):
        dm.polygon([p(i) for i in hueco], fill=0)
    alfa = Image.composite(img.getchannel("A"), Image.new("L", (S, S), 0), mascara)
    img.putalpha(alfa)

    # Desvanece un poco el borde exterior para que no se vea un corte duro.
    alfa = img.getchannel("A").filter(ImageFilter.GaussianBlur(3))
    img.putalpha(alfa)

    img = img.resize((FINAL, FINAL), Image.LANCZOS)
    ruta = os.path.join(RAIZ, "assets", "mascara", "textura.png")
    img.save(ruta, optimize=True)
    print("escrito", ruta)


if __name__ == "__main__":
    main()
