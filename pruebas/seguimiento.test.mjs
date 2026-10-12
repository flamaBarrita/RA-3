// Prueba del ajuste de pose: se gira, escala y mueve la cara canónica con valores
// conocidos y se revisa que el seguimiento los recupere.  Uso: node pruebas/seguimiento.test.mjs
import assert from 'node:assert/strict';
import { Seguidor, FiltroUnEuro } from '../js/seguimiento.js';
import { REFERENCIA, NUM_PUNTOS } from '../js/datos-cara.js';

const ANCHO = 1280, ALTO = 720;

function cuaternion(ejeX, ejeY, ejeZ, grados) {
  const n = Math.hypot(ejeX, ejeY, ejeZ), a = (grados * Math.PI) / 360;
  return [Math.cos(a), (ejeX / n) * Math.sin(a), (ejeY / n) * Math.sin(a), (ejeZ / n) * Math.sin(a)];
}

function rotar([w, x, y, z], v) {
  const [vx, vy, vz] = v;
  const cx = y * vz - z * vy, cy = z * vx - x * vz, cz = x * vy - y * vx;
  return [vx + 2 * (w * cx + y * cz - z * cy), vy + 2 * (w * cy + z * cx - x * cz), vz + 2 * (w * cz + x * cy - y * cx)];
}

/** Puntos como los entregaría MediaPipe para una pose dada. */
function caraSintetica(q, s, t, ruido = 0) {
  const pts = [];
  for (let i = 0; i < NUM_PUNTOS; i++) {
    const r = rotar(q, [REFERENCIA[i * 3], REFERENCIA[i * 3 + 1], REFERENCIA[i * 3 + 2]]);
    const px = r[0] * s + t[0] + (Math.random() - 0.5) * ruido;
    const py = r[1] * s + t[1] + (Math.random() - 0.5) * ruido;
    const pz = r[2] * s + t[2];
    pts.push({ x: px / ANCHO, y: 1 - py / ALTO, z: -pz / ANCHO });
  }
  return pts;
}

let fallos = 0;
function caso(nombre, fn) {
  try { fn(); console.log('ok  ', nombre); } catch (e) { fallos++; console.log('FALLA', nombre, '\n', e.message); }
}

caso('recupera giro de 50° a la derecha', () => {
  const seg = new Seguidor();
  const q = cuaternion(0, 1, 0, 50);
  seg.ajustarPose(new Float32Array(caraSintetica(q, 12, [640, 360, 0]).flatMap((p) => [p.x * ANCHO, (1 - p.y) * ALTO, -p.z * ANCHO])));
  const { q: r, s, t } = seg.ajustarPose(new Float32Array(caraSintetica(q, 12, [640, 360, 0]).flatMap((p) => [p.x * ANCHO, (1 - p.y) * ALTO, -p.z * ANCHO])));
  const dot = Math.abs(q[0] * r[0] + q[1] * r[1] + q[2] * r[2] + q[3] * r[3]);
  assert.ok(dot > 0.9999, `cuaternión distinto: ${r}`);
  assert.ok(Math.abs(s - 12) < 0.01, `escala ${s}`);
  assert.ok(Math.hypot(t[0] - 640, t[1] - 360, t[2]) < 0.5, `posición ${t}`);
  assert.ok(seg.error < 0.01, `error ${seg.error}`);
});

caso('ángulos: giro, inclinación y ladeo', () => {
  for (const [eje, campo] of [[[0, 1, 0], 'giro'], [[1, 0, 0], 'inclinacion'], [[0, 0, 1], 'ladeo']]) {
    const seg = new Seguidor();
    seg.actualizar(caraSintetica(cuaternion(...eje, 35), 10, [600, 300, 0]), ANCHO, ALTO, 0);
    const a = seg.angulos();
    assert.ok(Math.abs(a[campo] - 35) < 0.5, `${campo} = ${a[campo]}`);
  }
});

caso('la salida coincide con la entrada sin ruido', () => {
  const seg = new Seguidor();
  const q = cuaternion(0.3, 1, 0.1, -40);
  const pts = caraSintetica(q, 11, [500, 400, 30]);
  const out = seg.actualizar(pts, ANCHO, ALTO, 0);
  let max = 0;
  for (let i = 0; i < NUM_PUNTOS; i++) {
    max = Math.max(max, Math.hypot(out[i * 3] - pts[i].x * ANCHO, out[i * 3 + 1] - (1 - pts[i].y) * ALTO));
  }
  assert.ok(max < 0.05, `diferencia máxima ${max}px`);
});

caso('giro rápido: menos retraso que filtrar cada punto (Actividad 2)', () => {
  // La cabeza gira de 0° a 60° en 0.3 s a 30 cuadros/s; se mide el error de la nariz.
  const seg = new Seguidor();
  const filtroViejo = new FiltroUnEuro(NUM_PUNTOS * 3, { minCorte: 1.5, beta: 10 });
  let errNuevo = 0, errViejo = 0;
  for (let k = 0; k <= 15; k++) {
    const t = k / 30;
    const ang = Math.min(60, (t / 0.3) * 60);
    const pts = caraSintetica(cuaternion(0, 1, 0, ang), 12, [640, 360, 0], 1.5);
    const out = seg.actualizar(pts, ANCHO, ALTO, t);
    const crudos = new Float32Array(pts.flatMap((p) => [p.x, p.y, p.z]));
    filtroViejo.filtrar(crudos, t);
    const real = rotar(cuaternion(0, 1, 0, ang), [REFERENCIA[3], REFERENCIA[4], REFERENCIA[5]]);
    const rx = real[0] * 12 + 640;
    errNuevo += Math.abs(out[3] - rx);
    errViejo += Math.abs(crudos[3] * ANCHO - rx);
  }
  console.log(`      error medio nariz: nuevo ${(errNuevo / 16).toFixed(2)} px, Actividad 2 ${(errViejo / 16).toFixed(2)} px`);
  assert.ok(errNuevo < errViejo, 'el seguimiento nuevo debería tener menos error');
});

caso('cara quieta: menos temblor que la Actividad 2', () => {
  const seg = new Seguidor();
  const filtroViejo = new FiltroUnEuro(NUM_PUNTOS * 3, { minCorte: 1.5, beta: 10 });
  const q = cuaternion(0, 1, 0, 20);
  let antNuevo = null, antViejo = null, tembNuevo = 0, tembViejo = 0;
  for (let k = 0; k < 60; k++) {
    const pts = caraSintetica(q, 12, [640, 360, 0], 3);
    const out = seg.actualizar(pts, ANCHO, ALTO, k / 30).slice();
    const crudos = new Float32Array(pts.flatMap((p) => [p.x * ANCHO, p.y * ALTO, p.z]));
    const norm = crudos.map((v, i) => (i % 3 === 0 ? v / ANCHO : i % 3 === 1 ? v / ALTO : v));
    filtroViejo.filtrar(norm, k / 30);
    if (k > 10) {
      for (let i = 0; i < NUM_PUNTOS; i++) {
        tembNuevo += Math.abs(out[i * 3] - antNuevo[i * 3]);
        tembViejo += Math.abs((norm[i * 3] - antViejo[i * 3]) * ANCHO);
      }
    }
    antNuevo = out;
    antViejo = norm.slice();
  }
  const n = 49 * NUM_PUNTOS;
  console.log(`      temblor medio por cuadro: nuevo ${(tembNuevo / n).toFixed(2)} px, Actividad 2 ${(tembViejo / n).toFixed(2)} px`);
  assert.ok(tembNuevo < tembViejo);
});

caso('conserva la máscara un momento al perder la cara', () => {
  const seg = new Seguidor();
  seg.actualizar(caraSintetica(cuaternion(0, 1, 0, 0), 12, [640, 360, 0]), ANCHO, ALTO, 1);
  assert.equal(seg.visibilidad(1.02), 1);
  assert.ok(seg.visibilidad(1.2) > 0 && seg.visibilidad(1.2) < 1);
  assert.equal(seg.visibilidad(2), 0);
});

if (fallos) { console.log(`${fallos} prueba(s) fallaron`); process.exit(1); }
console.log('todas las pruebas pasaron');
