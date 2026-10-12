"""Genera los datos de la malla de la máscara a partir del modelo canónico de MediaPipe.

Salidas:
  js/datos-cara.js                      triángulos, UVs, anillos extra y la cara de
                                        referencia que usa el seguimiento
  blender/cara_base.obj                 la misma malla (con UVs) para pintarla en Blender
  plantilla/plantilla_uv.png            guía para pintar la textura (fondo blanco)
  plantilla/plantilla_uv_transparente.png  la misma guía sin fondo, para usarla como
                                        capa en Krita / Photoshop / Procreate
  tools/uv_clave.json                   puntos clave en UV (para la textura provisional)

La malla de MediaPipe solo llega a la frente y al contorno de la cara, así que
se agregan dos anillos alrededor del óvalo para cubrir también la parte de arriba
de la frente y las sienes (por ejemplo, para una corona de cempasúchil).

Los triángulos que tapan los ojos y el interior de la boca se quitan: así esas
zonas quedan siempre transparentes y la boca se ve abierta de verdad.

Uso:  python3 tools/generar_datos_cara.py
"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBJ = os.path.join(RAIZ, "tools", "canonical_face_model.obj")

# Contorno de la cara de MediaPipe (FACEMESH_FACE_OVAL), en orden.
OVALO = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
         400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
         54, 103, 67, 109]

# Anillos extra: k = cuánto se separa del centro del óvalo, atras = cuánto se
# hunde hacia la nuca (proporcional al alto de la cara), k_uv = separación en UV.
ANILLOS = [
    {"k": 0.10, "atras": 0.05, "k_uv": 0.13},
    {"k": 0.22, "atras": 0.15, "k_uv": 0.28},
]

OJO_DER = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
OJO_IZQ = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
LABIOS_EXT = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37,
              39, 40, 185]
LABIOS_INT = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82,
              81, 80, 191]
CEJA_DER = [70, 63, 105, 66, 107]
CEJA_IZQ = [300, 293, 334, 296, 336]


def leer_obj():
    verts, uvs, caras = [], [], []
    for linea in open(OBJ):
        p = linea.split()
        if not p:
            continue
        if p[0] == "v":
            verts.append(tuple(map(float, p[1:4])))
        elif p[0] == "vt":
            uvs.append(tuple(map(float, p[1:3])))
        elif p[0] == "f":
            caras.append([tuple(int(x) - 1 for x in c.split("/")[:2]) for c in p[1:]])
    # En este modelo cada vértice tiene una sola UV: se reordenan por vértice.
    uv_vert = [None] * len(verts)
    tris = []
    for cara in caras:
        for v, t in cara:
            uv_vert[v] = uvs[t]
        tris.append([v for v, _ in cara])
    return verts, uv_vert, tris


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def mul(a, s):
    return tuple(x * s for x in a)


def norm(a):
    return math.sqrt(sum(x * x for x in a))


def promedio(puntos):
    return mul(tuple(map(sum, zip(*puntos))), 1 / len(puntos))


def main():
    verts, uvs, tris = leer_obj()
    n = len(verts)
    referencia = [tuple(v) for v in verts]

    # Quita los triángulos que cubren los ojos y la boca (todos sus vértices están
    # en el contorno interior del ojo o de los labios).
    huecos = [set(OJO_DER), set(OJO_IZQ), set(LABIOS_INT)]
    antes = len(tris)
    tris = [t for t in tris if not any(all(i in h for i in t) for h in huecos)]
    print(f"triángulos de ojos y boca quitados: {antes - len(tris)}")

    # Anillos en 3D (misma regla que js/malla-mascara.js, para la vista en Blender).
    centro = promedio([verts[i] for i in OVALO])
    alto = norm(sub(verts[10], verts[152]))
    frente = (0.0, 0.0, 1.0)  # en el modelo canónico la cara mira hacia +z
    uv_centro = promedio([uvs[i] for i in OVALO])
    for anillo in ANILLOS:
        for i in OVALO:
            d = sub(verts[i], centro)
            verts.append(add(add(verts[i], mul(d, anillo["k"])), mul(frente, -alto * anillo["atras"])))
            uvs.append(add(uvs[i], mul(sub(uvs[i], uv_centro), anillo["k_uv"])))

    m = len(OVALO)
    for a in range(len(ANILLOS)):
        interior = OVALO if a == 0 else [n + (a - 1) * m + j for j in range(m)]
        exterior = [n + a * m + j for j in range(m)]
        for j in range(m):
            i0, i1 = interior[j], interior[(j + 1) % m]
            e0, e1 = exterior[j], exterior[(j + 1) % m]
            tris.append([i0, e0, i1])
            tris.append([i1, e0, e1])

    # Reescala las UVs para que todo quepa en [0.02, 0.98] sin deformar.
    us = [u for u, _ in uvs]
    vs = [v for _, v in uvs]
    escala = 0.96 / max(max(us) - min(us), max(vs) - min(vs))
    cu, cv = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
    uvs = [(0.5 + (u - cu) * escala, 0.5 + (v - cv) * escala) for u, v in uvs]

    escribir_js(n, uvs, tris, referencia)
    escribir_obj(verts, uvs, tris)
    dibujar_plantilla(uvs, tris, n)


# Puntos que casi no se mueven con los gestos (frente, puente y base de la nariz,
# pómulos, sienes). Con ellos se calcula la posición y el giro de la cabeza.
ESTABLES = [10, 151, 9, 8, 168, 6, 197, 195, 5, 4, 1, 19, 94, 2, 98, 327, 64, 294,
            109, 67, 103, 54, 21, 338, 297, 332, 284, 251, 108, 69, 104, 68, 337, 299,
            333, 298, 127, 234, 356, 454, 116, 117, 118, 345, 346, 347, 123, 352, 50, 280,
            36, 266, 203, 423, 129, 358, 49, 279, 48, 278, 219, 439, 193, 417, 122, 351,
            6, 413, 189, 245, 465, 188, 412, 174, 399, 236, 456]


def escribir_js(n, uvs, tris, referencia):
    ruta = os.path.join(RAIZ, "js", "datos-cara.js")
    uv_plano = [round(c, 5) for uv in uvs for c in uv]
    tri_plano = [i for t in tris for i in t]
    with open(ruta, "w") as f:
        f.write("// Archivo generado por tools/generar_datos_cara.py. No editar a mano.\n")
        f.write("// Basado en el modelo canónico de MediaPipe Face Mesh (Apache 2.0).\n\n")
        f.write(f"export const NUM_PUNTOS = {n};\n")
        f.write(f"export const OVALO = {json.dumps(OVALO)};\n")
        f.write(f"export const ANILLOS = {json.dumps(ANILLOS)};\n")
        f.write(f"export const UVS = new Float32Array({json.dumps(uv_plano)});\n")
        f.write(f"export const TRIANGULOS = new Uint16Array({json.dumps(tri_plano)});\n")
        ref_plano = [round(c, 4) for v in referencia for c in v]
        f.write("// Cara canónica de MediaPipe (cm, y hacia arriba, z hacia la cámara).\n")
        f.write(f"export const REFERENCIA = new Float32Array({json.dumps(ref_plano)});\n")
        f.write(f"export const ESTABLES = {json.dumps(sorted(set(ESTABLES)))};\n")
    print("escrito", ruta)


def escribir_obj(verts, uvs, tris):
    ruta = os.path.join(RAIZ, "blender", "cara_base.obj")
    with open(ruta, "w") as f:
        f.write("# Malla base de la máscara (cara canónica de MediaPipe + 2 anillos extra).\n")
        f.write("# Pinta la textura sobre estas UVs; no muevas los vértices ni las UVs.\n")
        f.write("o CaraBase\n")
        for v in verts:
            f.write("v %.6f %.6f %.6f\n" % v)
        for uv in uvs:
            f.write("vt %.6f %.6f\n" % uv)
        for t in tris:
            f.write("f " + " ".join(f"{i + 1}/{i + 1}" for i in t) + "\n")
    print("escrito", ruta)


def dibujar_plantilla(uvs, tris, n):
    tam = 2048
    guia = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    d = ImageDraw.Draw(guia)

    def px(i):
        u, v = uvs[i]
        return (u * tam, (1 - v) * tam)

    # Eje de simetría: diseña media cara y refléjala.
    d.line([(tam / 2, 0), (tam / 2, tam)], fill=(150, 150, 150, 200), width=2)
    for t in tris:
        color = (150, 150, 165, 255) if max(t) < n else (120, 175, 225, 255)
        d.polygon([px(i) for i in t], outline=color)
    for hueco in (OJO_DER, OJO_IZQ, LABIOS_INT):
        d.polygon([px(i) for i in hueco], fill=(230, 40, 40, 70), outline=(220, 30, 30, 255), width=5)
    d.line([px(i) for i in LABIOS_EXT + LABIOS_EXT[:1]], fill=(230, 120, 0, 255), width=4)
    for ceja in (CEJA_DER, CEJA_IZQ):
        d.line([px(i) for i in ceja], fill=(130, 60, 210, 255), width=6)
    d.line([px(i) for i in OVALO + OVALO[:1]], fill=(0, 140, 70, 255), width=5)
    externo = list(range(len(uvs) - len(OVALO), len(uvs)))
    d.line([px(i) for i in externo + externo[:1]], fill=(0, 90, 210, 255), width=5)
    for i in (1, 10, 152, 168):
        x, y = px(i)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(0, 0, 0, 255))

    os.makedirs(os.path.join(RAIZ, "plantilla"), exist_ok=True)
    guia.save(os.path.join(RAIZ, "plantilla", "plantilla_uv_transparente.png"))

    img = Image.new("RGBA", (tam, tam), (255, 255, 255, 255))
    img.alpha_composite(guia)
    d = ImageDraw.Draw(img)
    try:
        fuente = ImageFont.truetype("DejaVuSans.ttf", 30)
    except OSError:
        fuente = ImageFont.load_default()
    textos = [
        "Rojo: ojos y boca interior -> déjalos TRANSPARENTES",
        "Naranja: labios   Morado: cejas   Puntos: nariz, frente, entrecejo, barbilla",
        "Verde: borde real de la cara   Azul: borde de los anillos extra (frente/sienes)",
        "Gris: eje de simetría. La cara se ve como si la persona te mirara de frente.",
    ]
    for k, texto in enumerate(textos):
        d.text((30, tam - 190 + 44 * k), texto, fill=(40, 40, 40, 255), font=fuente)
    ruta = os.path.join(RAIZ, "plantilla", "plantilla_uv.png")
    img.save(ruta)
    print("escrito", ruta)

    # Exporta los puntos clave en UV para el generador del placeholder.
    clave = {i: uvs[i] for i in set(OJO_DER + OJO_IZQ + LABIOS_EXT + LABIOS_INT + CEJA_DER
                                    + CEJA_IZQ + OVALO + [1, 4, 6, 9, 168, 2, 98, 327, 50, 280,
                                                          205, 425, 234, 454, 21, 251, 54, 284,
                                                          127, 356, 162, 389])}
    clave["externo"] = [uvs[i] for i in externo]
    clave["anillo1"] = [uvs[i] for i in range(n, n + len(OVALO))]
    with open(os.path.join(RAIZ, "tools", "uv_clave.json"), "w") as f:
        json.dump(clave, f)


if __name__ == "__main__":
    main()
