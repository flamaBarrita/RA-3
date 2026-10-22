# Diseño de las texturas de catrín y catrina (Actividad 3)

Necesito que pintes en Blender las texturas finales de una máscara de Día de Muertos para un filtro de realidad aumentada en web. El filtro ya está hecho (repo https://github.com/flamaBarrita/RA-3). Solo faltan las texturas PNG que se pegan sobre la malla de la cara. No cambies nada más del proyecto.

## 1. Qué hay que entregar

- **Dos PNG RGBA de 2048 × 2048** (8 bits, con transparencia, colores sRGB), catrina y catrín, en `RA-3/assets/mascara/` (ver sección 4). La de la catrina también se guarda como `textura.png`, que reemplaza a la textura provisional.
- Guarda también el `.blend` con la textura empaquetada o enlazada en `RA-3/blender/mascara_dia_de_muertos.blend`.
- Al final dame unas vistas renderizadas de la malla con la textura: de frente, girada 30° y girada 60°.

## 2. Preparar la escena

1. Si la carpeta RA-3 no está en mi computadora, clónala (`git clone https://github.com/flamaBarrita/RA-3`) o descárgala en ZIP desde GitHub. Pregúntame dónde está antes de buscar por todo el disco.
2. Abre `RA-3/blender/mascara_dia_de_muertos.blend`. Si falla, ejecuta el script `RA-3/tools/preparar_blender.py`, que lo vuelve a crear.
3. Qué trae el .blend:
   - El objeto **`Mascara`**: 540 vértices. Los 0 a 467 son exactamente los 468 puntos del modelo canónico de MediaPipe Face Mesh, con su mapa UV. Los 468 a 539 son dos anillos extra alrededor del contorno, para la frente alta y las sienes.
   - El material **`MascaraDiaDeMuertos`** tiene dos imágenes. `textura` (archivo `blender/textura.png`, transparente) es la que hay que pintar. `plantilla_guia` (`plantilla/plantilla_uv_transparente.png`) es solo una guía visual y no debe quedar dentro de la textura.
   - La simetría de malla en X ya está activada.
4. **Reglas fijas:** no muevas vértices, no cambies las UVs, no agregues islas UV y no cambies la topología. La app usa exactamente estas UVs. Hay una sola isla UV, así que no hay costuras.

## 3. Cómo leer el mapa UV

- La imagen muestra la cara como si la persona te mirara de frente. Su ojo derecho queda a la **izquierda** de la imagen.
- El eje de simetría es la columna x = 1024.
- **Ojos y boca interior no tienen triángulos** (son huecos en la malla). Igual deben quedar con **alfa = 0** en la textura.
- Coordenadas en píxeles de la imagen de 2048 × 2048, con el origen **arriba a la izquierda** (en `image.pixels` de Blender el origen está abajo: fila = 2047 − y):

| Punto (índice MediaPipe) | x, y |
| --- | --- |
| Ojo derecho de la persona: centro / esquina ext. (33) / esquina int. (133) / párpado arriba (159) / abajo (145) | (784, 791) / (681, 787) / (898, 805) / (780, 755) / (780, 826) |
| Ojo izquierdo: centro / ext. (263) / int. (362) / arriba (386) / abajo (374) | (1264, 791) / (1367, 787) / (1150, 805) / (1268, 755) / (1268, 826) |
| Entrecejo (168) / frente media (9) / borde superior de la cara (10) | (1024, 749) / (1024, 622) / (1024, 368) |
| Punta de la nariz (1) / dorso (4) / alas (98, 327) | (1024, 1055) / (1024, 1023) / (903, 1115), (1144, 1115) |
| Comisuras (61, 291) / labio superior (0) / labio inferior (17) | (840, 1285), (1208, 1285) / (1024, 1219) / (1024, 1350) |
| Barbilla (152) | (1024, 1690) |
| Mejillas (205, 425) | (743, 1091), (1305, 1091) |
| Cejas: ext./int. derecha (70, 107), ext./int. izquierda (300, 336) | (602, 668), (933, 609), (1446, 668), (1115, 609) |
| Sienes (234, 454) | (256, 951), (1792, 951) |
| Contorno real de la cara (óvalo) | x 256–1792, y 368–1690 |
| Borde exterior de los anillos extra | x 41–2007, y 178–1870 |

- Contornos para los huecos, como listas de índices de vértice (sus UVs se leen de la malla):
  - Ojo derecho: 33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246
  - Ojo izquierdo: 263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466
  - Boca interior: 78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191
  - Labios por fuera: 61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185
  - Óvalo de la cara: 10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109
- Para tener coordenadas exactas, lee la UV de cada vértice desde la malla (`mesh.loops[i].vertex_index` y `mesh.uv_layers.active.data[i].uv`; píxel x = u·2048, y desde arriba = (1 − v)·2048) y compárala con la tabla.

## 4. Diseño: catrín y catrina tradicionales (dos texturas)

Haz **dos texturas** con el mismo mapa UV, inspiradas en el maquillaje clásico de catrín y catrina mexicanos: calavera de azúcar pintada con detalle fino, rosas rojas, filigrana negra y dientes de esqueleto. Debe tratarse con respeto, como homenaje a quienes ya partieron. Nada de sangre, grietas, heridas ni estilo de terror.

- `assets/mascara/textura_catrina.png`
- `assets/mascara/textura_catrin.png`
- Copia la de la **catrina** también como `assets/mascara/textura.png`, que es la que carga el filtro.

Las coordenadas que siguen son píxeles de la tabla de la sección 3.

### Elementos que comparten

1. **Base de la cara.** Dentro del óvalo, color hueso cálido `#F4EBDD`.
   - Hacia el contorno pasa a un sombreado ocre/durazno `#E8B98A`, en una franja de unos 120 px hacia adentro desde el óvalo.
   - En las sienes y bajo los pómulos, el sombreado se oscurece a `#C98A5E`, como hueso envejecido.
   - El centro de la cara (frente, nariz y barbilla) queda claro.
2. **Contorno negro.** Desde el borde del óvalo hacia afuera, todo es negro `#0E0B10`, como el maquillaje de las fotos, donde el cuello, las orejas y el nacimiento del pelo van pintados de negro.
   - En los anillos extra, el negro va de alfa 1 junto al óvalo a alfa 0 en el borde exterior de los anillos (degradado suave).
   - Excepción: la corona de flores de la catrina (más abajo).
3. **Hundimiento de mejillas.** Debajo de cada pómulo, una mancha diagonal gris oscuro `#2A2328` con bordes difuminados (unos 40 px de difuminado).
   - Va desde cerca de la sien, alrededor de (330, 1100) y su reflejo (1718, 1100), hasta unos 60 px por fuera de cada comisura, en (780, 1300) y (1268, 1300).
   - Ancho de unos 70 px en la parte más gruesa.
4. **Cuencas de los ojos.**
   - Una forma redondeada y un poco más ancha que alta alrededor de cada hueco del ojo: unos 300 × 250 px, centrada en (784, 780) y en (1264, 780).
   - Relleno con degradado radial: rojo vino `#7A0F1E` en el centro, negro `#140A0E` en la orilla.
   - Borde negro de 10 px, y sobre él un filo de festón (medias lunas pequeñas hacia afuera, de 18 px cada una).
   - El hueco del ojo dentro de la cuenca queda **transparente**.
5. **Nariz.** Cavidad nasal de calavera: un corazón invertido (punta hacia arriba) negro `#0E0B10`.
   - Cubre las alas de la nariz, de (903, 1115) a (1144, 1115), con la punta en (1024, 1010).
   - Lleva un brillo rojo oscuro `#5A0A14` en el centro y un contorno con 3 o 4 curvitas de filigrana a cada lado.
6. **Dientes de esqueleto** (lo más importante del look).
   - Dos filas de dientes pintados sobre la boca, en una sonrisa ancha que va de (760, 1285) a (1288, 1285), más allá de las comisuras. La línea de mordida es la línea de la boca, en y = 1285.
   - Fila de arriba: de y = 1205 a y = 1285. Fila de abajo: de y = 1285 a y = 1375.
   - Cada fila tiene unos 16 dientes rectangulares con esquinas redondeadas, color marfil `#F7F1E3`. Los del centro miden unos 30 px de ancho y se van haciendo más angostos hacia los lados.
   - Cada diente lleva contorno negro de 4 px y un pequeño sombreado gris `#BDB3A6` en la base.
   - Entre diente y diente, separaciones negras de 5 px.
   - Arriba de la fila superior y abajo de la inferior, una línea de "encía y hueso" negra de 8 px que sigue la curva de la sonrisa. En los extremos, cerca de (760, 1285) y (1288, 1285), se curva hacia arriba hasta el pómulo, como la mandíbula de una calavera.
   - El interior de la boca (hueco) queda **transparente**: al abrir la boca se ve la boca real entre los dientes pintados.
   - Labios: no se pintan de color. Quedan cubiertos por los dientes.
7. **Filigrana.**
   - Volutas finas y espirales en negro, de 4 a 6 px, en las sienes, sobre las cejas y alrededor de las cuencas.
   - Hojitas verdes `#2E7D32` / `#4CAF50` entre las volutas.
   - Puntitos blancos `#FFFFFF` de 6 px, como perlas, en hilera alrededor de la parte de abajo de cada cuenca: unos 12 puntos por ojo.
8. **Simetría.** Todo es simétrico respecto a x = 1024, salvo lo que se indica como asimétrico.

### Catrín (`textura_catrin.png`)

- **Frente:** una cruz latina roja `#C8102E` al centro, sobre x = 1024, de la frente media (1024, 622) hacia arriba hasta y ≈ 470. Mide unos 70 × 110 px, con contorno negro de 4 px y puntas terminadas en forma de flor de lis pequeña.
- **Alrededor de la cruz:** volutas negras y doradas `#C9A227` que se abren hacia ambos lados, siguiendo la línea de las cejas, con 2 hojitas verdes por lado.
- **Cejas:** sobre cada ceja, una línea de filigrana roja y verde que sigue los puntos (602, 668) → (933, 609) y su reflejo.
- **Pómulos:** una espiral verde y dorada en cada pómulo, en (560, 960) y (1488, 960), de unos 80 px de diámetro.
- **Barbilla:** una rosa roja `#C8102E` de unos 120 px, con pétalos en espiral, sombras `#7A0F1E` y brillos `#E84A5F`, centrada en (1024, 1560). Lleva dos hojas verdes a los lados y dos cempasúchiles pequeños `#FF8C00` / `#FFC414` de unos 45 px, uno a cada lado.
- **Tono general:** más cálido (base con más ocre) y sobrio, en rojo, negro, dorado y verde.

### Catrina (`textura_catrina.png`)

- **Base:** un poco más blanca, `#F8F3EA`, con sombreado durazno más suave.
- **Frente:** una rosa roja grande `#C8102E` de unos 160 px, centrada en (1024, 520), con pétalos en espiral y sombras `#7A0F1E`. A cada lado van dos rosas más pequeñas de unos 70 px y hojas verdes. Alrededor, filigrana negra y puntitos rojos.
- **Alrededor de los ojos:** en lugar de festón negro, un festón de **pétalos rojos** `#D7263D` con borde negro alrededor de cada cuenca: 10 pétalos por ojo, con la punta hacia afuera.
- **Mejilla derecha de la persona** (lado izquierdo de la imagen, cerca de (620, 1080)): un ramito de 2 rosas rojas con hojas, de unos 150 px en total. Es el detalle **asimétrico**. En la otra mejilla solo va filigrana fina.
- **Debajo de cada ojo:** 3 gotitas turquesa `#00A6A6` con brillo blanco, como lágrimas de adorno (no tristes), en fila hacia el pómulo.
- **Barbilla:** un corazón rojo pequeño de unos 60 px con filigrana negra a los lados, en (1024, 1580).
- **Corona de flores** en los anillos extra, de sien a sien, pasando por arriba de la frente:
  - Rosas rojas `#C8102E` de 90 a 120 px, alternadas con claveles blancos `#FFFFFF` (pétalos con orillas dentadas y sombras `#DDD6CC`).
  - Ramitos de nube (flor de gypsophila): racimos de puntitos blancos de 5 a 8 px.
  - Cuatro cempasúchiles `#FF8C00` / `#FFC414` de unos 70 px entre las rosas, dos por lado, como toque de la flor de muerto.
  - Hojas verdes oscuras.
  - Las flores se concentran arriba y a los lados de la frente, más tupidas junto a las sienes, como en un tocado.
  - Debajo y entre las flores, el anillo va negro (como el pelo). Hacia el borde exterior queda transparente.
- **Tono general:** más vivo, en rojo, blanco, negro, verde y toques turquesa.

### Detalles técnicos del diseño

- Contornos negros de 4 a 10 px en todo, como en las fotos. El detalle muy fino (menos de 3 px) no se va a ver en el teléfono.
- Las rosas se dibujan como varias capas de pétalos en espiral (de 5 a 7 capas, de oscuro afuera a claro adentro), no como círculos planos.
- Nada de texto, logos ni marcas en la textura.

## 5. Calidad (rúbrica de la actividad)

- Que quede alineada con ojos, nariz, boca y contorno, y que se deforme con los gestos.
- Diseño propio con elementos del Día de Muertos: calavera, flores (rosas, claveles, cempasúchil) y filigrana tradicional.
- Buena resolución, sin costuras ni pixelado visibles. Ojos y boca interior transparentes.
- Colores saturados y contornos definidos (de 4 a 10 px), porque el detalle fino se pierde en la cámara del teléfono.
- Simétrica: diseña media cara y refléjala sobre x = 1024, salvo detalles a propósito.
- Bordes suavizados (antialiasing): dibuja al doble (4096) y reduce, o usa bordes suaves.

## 6. Cómo hacerlo

Te recomiendo **generar la textura con Python dentro de Blender** en lugar de simular trazos de pincel. Dibuja figuras (círculos, polígonos, curvas, flores) en un arreglo numpy de 2048 × 2048 × 4 usando las coordenadas UV leídas de la malla, y escríbelo con `image.pixels.foreach_set(...)`.

1. Dibuja por capas: base y sombreado, contorno negro, hundimiento de mejillas, cuencas, nariz, dientes, filigrana, flores y corona. Haz una función por elemento, para poder generar las dos variantes (catrín y catrina) con el mismo código.
2. Al final pon alfa = 0 dentro de los contornos de ambos ojos y de la boca interior.
3. Guarda `textura_catrina.png` y `textura_catrin.png` en `RA-3/assets/mascara/`, y copia la de la catrina como `textura.png` (`image.filepath_raw`, `file_format='PNG'`, `image.save()`). Cuida que la guía `plantilla_guia` **no** quede dentro de la textura.
4. Renderiza las dos variantes para revisar (Cycles en CPU sirve) con la cámara ortográfica de la escena: de frente, con el objeto girado 30° y con el objeto girado 60° en Z. Para el render conecta la textura directo al Base Color o apaga la guía. Luego regresa el objeto a su rotación original.
5. Verifica y repórtame:
   - tamaño 2048 × 2048 y modo RGBA;
   - alfa = 0 en (784, 791), (1264, 791) y (1024, 1285);
   - alfa = 1 en la frente (1024, 622) y en las mejillas;
   - no quedaron líneas de la plantilla en la textura.
6. Muéstrame los renders. Si te pido cambios, ajusta el código y vuelve a guardar.

Si prefieres que yo pinte a mano después, deja la textura en la imagen `textura` del material (nodo activo) y cambia al modo Texture Paint, para que pueda retocarla con el pincel.

## 7. Al terminar

Dime las rutas exactas de los PNG guardados. Para probarlo en la computadora: en la carpeta RA-3 ejecuta `python3 -m http.server 8000` y abre http://localhost:8000 (la cámara solo funciona en localhost o https). Con `?debug` se ve el giro de la cabeza.
