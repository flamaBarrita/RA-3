import * as THREE from '../vendor/three.module.min.js';
import { FaceLandmarker, FilesetResolver } from '../vendor/mediapipe/vision_bundle.mjs';
import { MallaMascara } from './malla-mascara.js';
import { crearGestos, blendshapesComoObjeto } from './gestos.js';
import { Particulas, FORMA } from './particulas.js';
import { Sonido } from './sonido.js';
import { Grabador } from './grabador.js';

const RUTA_MODELO = 'modelos/face_landmarker.task';
const RUTA_WASM = 'vendor/mediapipe/wasm';
const RUTA_CONFIG = 'assets/mascara/mascara.json';

const parametros = new URLSearchParams(location.search);
const DEPURAR = parametros.has('debug');
// En modo ?debug las teclas 1, 2 y 3 simulan boca, parpadeo y cejas para probar sin gestos.
const SIMULADO = { jawOpen: false, eyeBlinkLeft: false, browInnerUp: false };
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

const material = new THREE.MeshStandardMaterial({
  transparent: true,
  alphaTest: 0.03,
  side: THREE.DoubleSide,
  roughness: 0.6,
  metalness: 0.0,
  emissive: new THREE.Color(0xffffff),
  emissiveIntensity: 0,
});
const mascara = new MallaMascara(material);
escena.add(mascara.malla);

escena.add(new THREE.AmbientLight(0xffffff, 1.9));
const luz = new THREE.DirectionalLight(0xffffff, 1.3);
luz.position.set(0.3, 0.6, 1);
escena.add(luz);

const figuras = new Particulas({ max: 700 });             // pétalos y papel picado
const brillos = new Particulas({ max: 400, aditivo: true }); // chispas de vela
escena.add(figuras.puntos, brillos.puntos);

const gestos = crearGestos();
const sonido = new Sonido();
const grabador = new Grabador(lienzo, () => sonido.grabacion?.stream);
let config = {};

// ---------- Efectos de cada gesto ----------
const color = (lista) => lista.map((c) => new THREE.Color(c));
const COLORES_PETALO = color([0xff8c00, 0xffa000, 0xffb300, 0xff6f00, 0xffc107]);
const COLORES_PAPEL = color([0xe91e78, 0x7b1fa2, 0xff8c00, 0x00a5b4, 0x43a047, 0xffd600]);
const COLORES_VELA = color([0xffb74d, 0xffe082, 0xff8f00]);
// Cada parpadeo cambia el color de la máscara (se pueden cambiar en mascara.json).
let PALETAS = color(['#ffffff', '#ffd2a0', '#ffb3dc', '#d8c2ff', '#a8f0f0']);
const efecto = { brillo: 0, paleta: 0, tinte: new THREE.Color(1, 1, 1) };
const _p = new THREE.Vector3();
const _q = new THREE.Vector3();

function emitirPetalos(cantidad, fuerza = 1) {
  const s = mascara.altoCara;
  mascara.medio([13, 14], _p);
  figuras.emitir(_p, cantidad, {
    forma: FORMA.PETALO,
    colores: COLORES_PETALO,
    direccion: { x: 0, y: 1 },
    apertura: 2.2,
    velocidad: [s * 0.5 * fuerza, s * 1.3 * fuerza],
    vida: [1.4, 2.4],
    tam: [s * 0.09, s * 0.15],
    gravedad: s * 0.9,
    arrastre: 2.5,
    balanceo: s * 0.25,
    giro: 6,
    radio: s * 0.04,
  });
}

function lluviaPapelPicado() {
  const s = mascara.altoCara;
  mascara.punto(10, _p);
  _p.y += s * 0.55;
  figuras.emitir(_p, 70, {
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

function velasEnOjos() {
  const s = mascara.altoCara;
  for (const ojo of [[33, 133], [263, 362]]) {
    mascara.medio(ojo, _q);
    brillos.emitir(_q, 24, {
      colores: COLORES_VELA,
      direccion: { x: 0, y: 1 },
      apertura: 1.4,
      velocidad: [s * 0.15, s * 0.5],
      vida: [0.4, 0.9],
      tam: [s * 0.03, s * 0.08],
      gravedad: -s * 0.4,
      radio: s * 0.05,
    });
  }
}

const alIniciar = {
  boca() {
    emitirPetalos(45, 1.2);
    efecto.brillo = Math.max(efecto.brillo, 0.5);
  },
  cejas() {
    lluviaPapelPicado();
    efecto.brillo = Math.max(efecto.brillo, 0.4);
  },
  parpadeo() {
    efecto.paleta = (efecto.paleta + 1) % PALETAS.length;
    velasEnOjos();
    efecto.brillo = Math.max(efecto.brillo, 0.6);
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
  }
  const boca = gestos[0];
  if (boca.activo) emitirPetalos(Math.random() < 30 * dt ? 2 : 0);
}

function actualizarEfectos(dt) {
  efecto.brillo = Math.max(0, efecto.brillo - dt * 1.5);
  efecto.tinte.lerp(PALETAS[efecto.paleta], Math.min(1, dt * 6));
  material.color.copy(efecto.tinte);
  material.emissive.copy(efecto.tinte);
  material.emissiveIntensity = (config.brillo ?? 0.06) + efecto.brillo * 0.5;
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
  brillos.material.uniforms.escala.value = escala;
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

  actualizarEfectos(dt);
  figuras.actualizar(dt);
  brillos.actualizar(dt);
  renderer.render(escena, camara);
}

function simular(bs) {
  for (const [nombre, activo] of Object.entries(SIMULADO)) {
    if (!activo) continue;
    bs[nombre] = 0.95;
    if (nombre === 'eyeBlinkLeft') bs.eyeBlinkRight = 0.95;
  }
}

if (DEPURAR) {
  $('depuracion').classList.remove('oculto');
  const teclas = { 1: 'jawOpen', 2: 'eyeBlinkLeft', 3: 'browInnerUp' };
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

async function cargarMascara() {
  config = await (await fetch(RUTA_CONFIG)).json();
  if (Array.isArray(config.paletas) && config.paletas.length) PALETAS = color(config.paletas);
  const base = RUTA_CONFIG.slice(0, RUTA_CONFIG.lastIndexOf('/') + 1);
  let tex;
  try {
    tex = await new THREE.TextureLoader().loadAsync(base + config.textura);
  } catch {
    throw Object.assign(new Error('sin-textura'), {
      mensaje: `No encontré la textura de la máscara (assets/mascara/${config.textura}).`,
    });
  }
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
  material.map = tex;
  material.emissiveMap = tex;
  material.needsUpdate = true;
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
      material.map ? null : cargarMascara(),
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
