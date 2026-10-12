"""Prepara el archivo de Blender para pintar la textura de la máscara.

Crea blender/mascara_dia_de_muertos.blend con:
  - la malla de la cara (blender/cara_base.obj) con su mapa UV, que es el mismo
    que usa el filtro (modelo canónico de MediaPipe + anillos de frente y sienes);
  - una imagen transparente de 2048 x 2048 (blender/textura.png) lista para
    pintar con Texture Paint, con simetría en X activada;
  - la plantilla UV como guía debajo de la pintura (no se guarda en la textura);
  - una copia de la plantilla exportada con UV Editor > Export UV Layout
    (blender/plantilla_uv_blender.png), como piden los pasos de la rúbrica.

Cómo usarlo (cualquiera de las dos):
  a) Terminal:   blender --background --python tools/preparar_blender.py
  b) Blender:    pestaña Scripting > Open > tools/preparar_blender.py > Run Script
                 (si Blender no encuentra la carpeta, escribe su ruta en CARPETA).

Si blender/textura.png ya existe (por ejemplo, ya empezaste a pintar), no se borra.
Probado con Blender 4.2; debería funcionar en 4.x y 5.x.
"""
import os

import bpy

CARPETA = ""  # ruta de la carpeta del proyecto (RA-3); vacío = se detecta sola
TAM = 2048


def carpeta_proyecto():
    candidatos = [CARPETA]
    try:
        candidatos.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except NameError:
        pass
    if bpy.data.filepath:
        candidatos.append(os.path.dirname(os.path.dirname(bpy.data.filepath)))
    for c in candidatos:
        if c and os.path.exists(os.path.join(c, "blender", "cara_base.obj")):
            return c
    raise FileNotFoundError("No encontré blender/cara_base.obj. Escribe la ruta del proyecto en CARPETA.")


def limpiar():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)


def importar_malla(raiz):
    ruta = os.path.join(raiz, "blender", "cara_base.obj")
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=ruta)
    else:  # Blender 3.x
        bpy.ops.import_scene.obj(filepath=ruta)
    obj = bpy.context.selected_objects[0]
    obj.name = "Mascara"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()
    # Simetría para pintar media cara y que se refleje en la otra mitad.
    for propiedad in ("use_mesh_mirror_x",):
        if hasattr(obj, propiedad):
            setattr(obj, propiedad, True)
    if hasattr(obj.data, "use_mirror_x"):
        obj.data.use_mirror_x = True
    return obj


def imagen_textura(raiz):
    ruta = os.path.join(raiz, "blender", "textura.png")
    if not os.path.exists(ruta):
        img = bpy.data.images.new("textura", TAM, TAM, alpha=True)
        img.generated_color = (1, 1, 1, 0)
        img.filepath_raw = ruta
        img.file_format = "PNG"
        img.save()
        bpy.data.images.remove(img)
    img = bpy.data.images.load(ruta)
    img.name = "textura"
    img.alpha_mode = "STRAIGHT"
    return img


def material(obj, textura, guia):
    mat = bpy.data.materials.new("MascaraDiaDeMuertos")
    mat.use_nodes = True
    for atributo, valor in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED")):
        if hasattr(mat, atributo):
            try:
                setattr(mat, atributo, valor)
            except TypeError:
                pass
    nodos = mat.node_tree.nodes
    enlaces = mat.node_tree.links
    nodos.clear()

    salida = nodos.new("ShaderNodeOutputMaterial")
    salida.location = (900, 0)
    bsdf = nodos.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (600, 0)
    bsdf.inputs["Roughness"].default_value = 0.6
    enlaces.new(bsdf.outputs["BSDF"], salida.inputs["Surface"])

    n_guia = nodos.new("ShaderNodeTexImage")
    n_guia.image = guia
    n_guia.label = "Guía (plantilla UV, no se pinta)"
    n_guia.location = (-500, 250)

    n_tex = nodos.new("ShaderNodeTexImage")
    n_tex.image = textura
    n_tex.label = "Textura (aquí se pinta)"
    n_tex.location = (-500, -150)

    fondo = nodos.new("ShaderNodeMix")
    fondo.data_type = "RGBA"
    fondo.label = "Fondo + guía"
    fondo.location = (-150, 250)
    fondo.inputs["A"].default_value = (0.92, 0.92, 0.92, 1)
    enlaces.new(n_guia.outputs["Alpha"], fondo.inputs["Factor"])
    enlaces.new(n_guia.outputs["Color"], fondo.inputs["B"])

    mezcla = nodos.new("ShaderNodeMix")
    mezcla.data_type = "RGBA"
    mezcla.label = "Guía debajo de la pintura"
    mezcla.location = (150, 50)
    enlaces.new(n_tex.outputs["Alpha"], mezcla.inputs["Factor"])
    enlaces.new(fondo.outputs["Result"], mezcla.inputs["A"])
    enlaces.new(n_tex.outputs["Color"], mezcla.inputs["B"])
    enlaces.new(mezcla.outputs["Result"], bsdf.inputs["Base Color"])

    # El nodo activo es el que Texture Paint usa para pintar.
    nodos.active = n_tex
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return mat


def exportar_layout_uv(raiz, obj):
    ruta = os.path.join(raiz, "blender", "plantilla_uv_blender.png")
    try:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.export_layout(filepath=ruta, size=(TAM, TAM), opacity=0.0, export_all=True)
        print("escrito", ruta)
    except Exception as e:  # en algunos modos sin ventana no está disponible
        print("No se pudo exportar el layout UV automáticamente:", e)
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")


def main():
    raiz = carpeta_proyecto()
    limpiar()
    obj = importar_malla(raiz)
    guia = bpy.data.images.load(os.path.join(raiz, "plantilla", "plantilla_uv_transparente.png"))
    guia.name = "plantilla_guia"
    textura = imagen_textura(raiz)
    material(obj, textura, guia)
    exportar_layout_uv(raiz, obj)

    escena = bpy.context.scene
    escena.tool_settings.image_paint.mode = "MATERIAL"
    camara = bpy.data.cameras.new("Camara")
    cam = bpy.data.objects.new("Camara", camara)
    escena.collection.objects.link(cam)
    cam.location = (0, -60, 0)
    cam.rotation_euler = (1.5708, 0, 0)
    camara.type = "ORTHO"
    camara.ortho_scale = 30
    escena.camera = cam
    luz = bpy.data.lights.new("Luz", "SUN")
    luz_obj = bpy.data.objects.new("Luz", luz)
    escena.collection.objects.link(luz_obj)
    luz_obj.rotation_euler = (1.2, 0, 0.3)

    bpy.ops.file.make_paths_relative()
    ruta = os.path.join(raiz, "blender", "mascara_dia_de_muertos.blend")
    bpy.ops.wm.save_as_mainfile(filepath=ruta, relative_remap=True)
    print("escrito", ruta)


main()
