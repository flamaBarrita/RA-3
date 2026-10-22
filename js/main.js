import * as THREE from '../vendor/three.module.min.js';
import { FaceLandmarker, FilesetResolver } from '../vendor/mediapipe/vision_bundle.mjs';
import { MallaMascara } from './malla-mascara.js';
import { crearGestos, blendshapesComoObjeto } from './gestos.js';
import { Particulas, FORMA } from './particulas.js';
import { crearMaterialMaquillaje, aplicarAcabado, MedidorLuz } from './material-maquillaje.js';
import { Sonido } from './sonido.js';
import { Grabador } from './grabador.js';

const RUTA_MODELO = 'modelos/face_landmarker.task';
const RUTA_WASM = 'vendor/mediapipe/wasm';
const RUTA_CONFIG = 'assets/mascara/mascara.json';

const parametros = new URLSearchParams(location.search);
const DEPURAR = parametros.has('debug');
// En modo ?debug la tecla 3 simula levantar las cejas para probar sin gestos.
const SIMULADO = { browInnerUp: false };
if (parametros.has('limpio')) document.body.classList.add('limpio');

const $ = (id) => document.getElementById(id);
const video = $('video');
const lienzo = $('lienzo');

// ---------- Escena ----------
const renderer = new THREE.WebGLRenderer({ canvas: lienzo, antialias: true, preserveDrawingBuffer: DEPURAR });
const escena = new THREE.Scene();
const camara = new THREE.OrthographicCamera(0, 1, 1, 0, -10000, 10000);

const texturaVideo = new THREE.VideoTexture(video);
texturaVideo.colorSpace = THREE.SRGBColorSpace;
texturaVideo.repeat.x = -1;   // espejo, como una cámara selfie
texturaVideo.offset.x = 1;
const fondo = new THREE.Mesh(
  new THREE.PlaneGeometry(1, 1),
  new THREE.MeshBasicMaterial({ map: texturaVideo, depthWrite: false }),
);
fondo.position.z = -9000;
fondo.renderOrder = -1;
escena.add(fondo);

// La máscara se pinta sobre la piel real (ver js/material-maquillaje.js).
const material = crearMaterialMaquillaje(texturaVideo);
const mascara = new MallaMascara(material);
escena.add(mascara.malla);
const medidorLuz = new MedidorLuz(video);
const _tam = new THREE.Vector2();

const figuras = new Particulas({ max: 700 });   // papel picado
escena.add(figuras.puntos);

// Único efecto: levantar las cejas hace caer papel picado.
const gestos = crearGestos().filter((g) => g.nombre === 'cejas');
const sonido = new Sonido();
const grabador = new Grabador(lienzo, () => sonido.grabacion?.stream);
let config = {};

// ---------- Efecto: papel picado ----------
const color = (lista) => lista.map((c) => new THREE.Color(c));
const COLORES_PAPEL = color([0xe91e78, 0x7b1fa2, 0xff8c00, 0x00a5b4, 0x43a047, 0xffd600]);
const _p = new THREE.Vector3();

function lluviaPapelPicado(cantidad = 70) {
  const s = mascara.altoCara;
  mascara.punto(10, _p);
  _p.y = Math.min(_p.y + s * 0.55, alto - s * 0.05);
  figuras.emitir(_p, cantidad, {
    forma: FORMA.PAPEL,
    colores: COLORES_PAPEL,
    direccion: { x: 0, y: -1 },
    apertura: 0.8,
    velocidad: [s * 0.1, s * 0.4],
    vida: [1.8, 2.8],
    tam: [s * 0.1, s * 0.16],
    gravedad: s * 0.35,
    arrastre: 2.2,
    balanceo: s * 0.35,
    giro: 5,
    ancho: s * 1.8,
  });
}

const alIniciar = {
  cejas() {
    lluviaPapelPicado();
  },
};

const iconos = Object.fromEntries([...document.querySelectorAll('.gesto')].map((e) => [e.dataset.gesto, e]));

function procesarGestos(bs, ahora, dt) {
  for (const g of gestos) {
    const ev = g.actualizar(bs, ahora);
    if (ev.inicio) {
      alIniciar[g.nombre]();
      sonido.reproducir(g.nombre);
    }
    iconos[g.nombre]?.classList.toggle('activo', g.activo);
    // mientras las cejas sigan arriba, sigue cayendo papel picado
    if (g.activo && Math.random() < 20 * dt) lluviaPapelPicado(3);
  }
}

function actualizarMaquillaje() {
  renderer.getDrawingBufferSize(_tam);
  material.uniforms.tamBuffer.value.copy(_tam);
  material.uniforms.opacidad.value = material.opacidadBase * (material.opacity ?? 1);
  if (!mascara.malla.visible) return;
  // caja de la cara en píxeles del video (sin espejo, y hacia abajo)
  const s = mascara.seguidor.salida;
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (let i = 0; i < s.length; i += 3) {
    x0 = Math.min(x0, s[i]); x1 = Math.max(x1, s[i]);
    y0 = Math.min(y0, alto - s[i + 1]); y1 = Math.max(y1, alto - s[i + 1]);
  }
  material.uniforms.luzMedia.value = medidorLuz.actualizar({ x0, y0, x1, y1 });
}

// ---------- Tamaño ----------
let ancho = 0;
let alto = 0;

function ajustarTamano() {
  ancho = video.videoWidth;
  alto = video.videoHeight;
  if (!ancho || !alto) return;
  camara.left = 0;
  camara.right = ancho;
  camara.top = alto;
  camara.bottom = 0;
  camara.updateProjectionMatrix();
  fondo.scale.set(ancho, alto, 1);
  fondo.position.set(ancho / 2, alto / 2, -9000);
  const cubrir = Math.max(innerWidth / ancho, innerHeight / alto);
  const escala = THREE.MathUtils.clamp(cubrir * devicePixelRatio, 1, 2);
  renderer.setPixelRatio(escala);
  renderer.setSize(ancho, alto, false);
  figuras.material.uniforms.escala.value = escala;
}

// ---------- Bucle principal ----------
let detector = null;
let ultimoTiempoVideo = -1;
let ultimoCuadro = performance.now();
const medidor = { cuadros: 0, desde: performance.now(), fps: 0, deteccionMs: 0 };

function bucle() {
  requestAnimationFrame(bucle);
  const ahora = performance.now();
  const dt = Math.min((ahora - ultimoCuadro) / 1000, 0.1);
  ultimoCuadro = ahora;

  if (video.videoWidth !== ancho || video.videoHeight !== alto) ajustarTamano();

  if (video.readyState >= 2 && video.currentTime !== ultimoTiempoVideo) {
    ultimoTiempoVideo = video.currentTime;
    const t0 = performance.now();
    const res = detector.detectForVideo(video, ahora);
    medidor.deteccionMs += (performance.now() - t0 - medidor.deteccionMs) * 0.1;
    medidor.cuadros++;
    if (res.faceLandmarks?.length) {
      mascara.actualizar(res.faceLandmarks[0], ancho, alto, ahora / 1000);
      const bs = blendshapesComoObjeto(res);
      if (DEPURAR) simular(bs);
      procesarGestos(bs, ahora, dt);
      if (DEPURAR) mostrarDepuracion(bs);
    } else if (!mascara.sinCara(ahora / 1000)) {
      for (const g of gestos) g.reiniciar();
      for (const e of Object.values(iconos)) e.classList.remove('activo');
    }
    $('aviso-cara').classList.toggle('oculto', mascara.malla.visible);
  }

  if (ahora - medidor.desde > 1000) {
    medidor.fps = (medidor.cuadros * 1000) / (ahora - medidor.desde);
    medidor.cuadros = 0;
    medidor.desde = ahora;
  }

  actualizarMaquillaje();
  figuras.actualizar(dt);
  renderer.render(escena, camara);
}

function simular(bs) {
  for (const [nombre, activo] of Object.entries(SIMULADO)) {
    if (!activo) continue;
    bs[nombre] = 0.95;
  }
}

if (DEPURAR) {
  $('depuracion').classList.remove('oculto');
  const teclas = { 3: 'browInnerUp' };
  addEventListener('keydown', (e) => { if (teclas[e.key]) SIMULADO[teclas[e.key]] = true; });
  addEventListener('keyup', (e) => { if (teclas[e.key]) SIMULADO[teclas[e.key]] = false; });
}

function mostrarDepuracion(bs) {
  const lineas = gestos.map((g) => {
    const barra = '█'.repeat(Math.round(g.ultimoValor * 20)).padEnd(20, '·');
    return `${g.nombre.padEnd(9)} ${barra} ${g.ultimoValor.toFixed(2)} base ${g.base.toFixed(2)}${g.activo ? ' ●' : ''}`;
  });
  const a = mascara.seguidor.angulos();
  lineas.push(`giro ${a.giro.toFixed(0)}°  inclinación ${a.inclinacion.toFixed(0)}°  ladeo ${a.ladeo.toFixed(0)}°`);
  lineas.push(`ajuste ${mascara.seguidor.error.toFixed(1)} px  detección ${medidor.deteccionMs.toFixed(0)} ms  ${medidor.fps.toFixed(0)} fps  ${ancho}x${alto}`);
  $('depuracion').textContent = lineas.join('\n');
}

// ---------- Arranque ----------
async function abrirCamara() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw Object.assign(new Error('sin-camara'), {
      mensaje: window.isSecureContext
        ? 'Este navegador no permite usar la cámara.'
        : 'La cámara solo funciona si la página se abre con https:// (o en localhost).',
    });
  }
  const flujo = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } },
  });
  video.srcObject = flujo;
  await video.play();
  if (!video.videoWidth) await new Promise((r) => video.addEventListener('loadedmetadata', r, { once: true }));
}

async function crearDetector() {
  const archivos = await FilesetResolver.forVisionTasks(RUTA_WASM);
  // Umbrales de presencia y seguimiento más bajos que en la Actividad 2 (0.5):
  // MediaPipe sigue la cara aunque esté muy girada en lugar de soltarla y
  // volver a buscarla desde cero.
  const opciones = (delegate) => ({
    baseOptions: { modelAssetPath: RUTA_MODELO, delegate },
    runningMode: 'VIDEO',
    numFaces: 1,
    outputFaceBlendshapes: true,
    minFaceDetectionConfidence: 0.5,
    minFacePresenceConfidence: 0.35,
    minTrackingConfidence: 0.35,
  });
  try {
    return await FaceLandmarker.createFromOptions(archivos, opciones('GPU'));
  } catch (e) {
    console.warn('GPU no disponible, se usa CPU', e);
    return FaceLandmarker.createFromOptions(archivos, opciones('CPU'));
  }
}

const texturas = {};
let mascaraActual = null;

async function cargarTextura(ruta) {
  let tex;
  try {
    tex = await new THREE.TextureLoader().loadAsync(ruta);
  } catch {
    throw Object.assign(new Error('sin-textura'), {
      mensaje: `No encontré la textura de la máscara (${ruta}).`,
    });
  }
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
  return tex;
}

/** Cambia entre catrín y catrina (botones de abajo, o ?mascara=catrin). */
function ponerMascara(nombre) {
  if (!texturas[nombre]) return;
  mascaraActual = nombre;
  material.uniforms.mapa.value = texturas[nombre];
  for (const b of document.querySelectorAll('#selector button')) {
    b.setAttribute('aria-pressed', String(b.dataset.mascara === nombre));
  }
  try { localStorage.setItem('mascara', nombre); } catch {}
}

function leerPreferencia() {
  try { return localStorage.getItem('mascara'); } catch { return null; }
}

for (const b of document.querySelectorAll('#selector button')) {
  b.addEventListener('click', (e) => {
    e.stopPropagation();
    ponerMascara(b.dataset.mascara);
  });
}

async function cargarMascara() {
  config = await (await fetch(RUTA_CONFIG)).json();
  const acabado = parametros.get('acabado') ?? config.acabado ?? 'maquillaje';
  aplicarAcabado(material, acabado, acabado === (config.acabado ?? 'maquillaje') ? config.ajustesAcabado : {});
  const base = RUTA_CONFIG.slice(0, RUTA_CONFIG.lastIndexOf('/') + 1);
  const lista = config.mascaras ?? { mascara: config.textura };
  const nombres = Object.keys(lista);
  let elegida = parametros.get('mascara') ?? leerPreferencia() ?? config.inicial;
  if (!lista[elegida]) elegida = nombres[0];
  texturas[elegida] = await cargarTextura(base + lista[elegida]);
  ponerMascara(elegida);
  // las demás se cargan en segundo plano para cambiar al instante
  for (const n of nombres) if (!texturas[n]) cargarTextura(base + lista[n]).then((t) => (texturas[n] = t), () => {});
  $('selector').hidden = nombres.length < 2;
  sonido.configurar(config.sonidos, base);
}

function mensajeError(e) {
  if (e.mensaje) return e.mensaje;
  if (e.name === 'NotAllowedError') return 'Necesito permiso para usar la cámara. Actívalo en el candado de la barra de direcciones y vuelve a intentar.';
  if (e.name === 'NotFoundError' || e.name === 'OverconstrainedError') return 'No encontré una cámara frontal en este dispositivo.';
  if (e.name === 'NotReadableError') return 'La cámara está ocupada por otra aplicación. Ciérrala y vuelve a intentar.';
  return 'Algo falló al iniciar el filtro: ' + (e.message || e);
}

let enMarcha = false;

async function iniciar() {
  $('error').classList.add('oculto');
  $('cargando').classList.remove('oculto');
  try {
    const [, det] = await Promise.all([
      abrirCamara(),
      detector ?? crearDetector(),
      material.uniforms.mapa.value ? null : cargarMascara(),
    ]);
    detector = det;
    ajustarTamano();
    $('cargando').classList.add('oculto');
    if (!sonido.activo) $('aviso-sonido').classList.remove('oculto');
    if (!enMarcha) {
      enMarcha = true;
      bucle();
    }
  } catch (e) {
    console.error(e);
    $('cargando').classList.add('oculto');
    $('error-texto').textContent = mensajeError(e);
    $('error').classList.remove('oculto');
  }
}

sonido.alActivar = () => $('aviso-sonido').classList.add('oculto');
for (const evento of ['pointerdown', 'keydown']) addEventListener(evento, () => sonido.activar());
addEventListener('resize', ajustarTamano);
$('reintentar').addEventListener('click', iniciar);

const botonGrabar = $('grabar');
if (!grabador.disponible) botonGrabar.hidden = true;
botonGrabar.addEventListener('click', () => {
  if (grabador.grabando) grabador.detener();
  else grabador.iniciar();
  botonGrabar.classList.toggle('grabando', grabador.grabando);
});

iniciar();
