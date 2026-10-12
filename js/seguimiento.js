import { NUM_PUNTOS, REFERENCIA, ESTABLES } from './datos-cara.js';

/**
 * Seguimiento de la cabeza (mejora frente a la Actividad 2).
 *
 * En la Actividad 2 se suavizaba cada uno de los 468 puntos por separado. Al
 * girar la cabeza rápido, cada punto se retrasaba distinto y la máscara se
 * "resbalaba" o se deformaba. Aquí el movimiento se separa en dos partes:
 *
 *  1. Pose rígida (posición, giro y tamaño de la cabeza). Se calcula cada cuadro
 *     ajustando la cara canónica de MediaPipe a los puntos estables (frente,
 *     nariz, pómulos, sienes) con el método de Horn (cuaterniones). Se suaviza
 *     con un filtro "one euro" muy ágil y una pequeña predicción, así sigue
 *     los giros sin retraso.
 *  2. Expresión (boca, ojos, cejas): los puntos se pasan al sistema de la cara
 *     ("cara quieta, mirando al frente") y ahí se suavizan aparte. Como el giro
 *     ya no les afecta, se puede quitar el temblor sin frenar los gestos.
 *
 * Al final se vuelven a juntar: punto = posición + tamaño · giro · expresión.
 * Si MediaPipe pierde la cara unos cuadros, se conserva la última pose.
 */

/** Filtro "one euro" para un vector de n valores. */
export class FiltroUnEuro {
  constructor(n, { minCorte = 1.5, beta = 10, dCorte = 1 } = {}) {
    this.x = new Float32Array(n);
    this.dx = new Float32Array(n);
    this.minCorte = minCorte;
    this.beta = beta;
    this.dCorte = dCorte;
    this.ultimoT = null;
  }

  static alfa(corte, dt) {
    const tau = 1 / (2 * Math.PI * corte);
    return 1 / (1 + tau / dt);
  }

  reiniciar() {
    this.ultimoT = null;
  }

  filtrar(valores, t) {
    if (this.ultimoT === null || t - this.ultimoT > 0.5) {
      this.x.set(valores);
      this.dx.fill(0);
      this.ultimoT = t;
      return;
    }
    const dt = Math.max(t - this.ultimoT, 1e-3);
    this.ultimoT = t;
    const aD = FiltroUnEuro.alfa(this.dCorte, dt);
    for (let i = 0; i < valores.length; i++) {
      const dx = (valores[i] - this.x[i]) / dt;
      this.dx[i] += aD * (dx - this.dx[i]);
      const a = FiltroUnEuro.alfa(this.minCorte + this.beta * Math.abs(this.dx[i]), dt);
      this.x[i] += a * (valores[i] - this.x[i]);
      valores[i] = this.x[i];
    }
  }
}

// Ajustes del seguimiento (se pueden cambiar con ?suave=1 para comparar).
export const AJUSTES = {
  pose: { minCorte: 1.2, beta: 6 },        // giro y posición: ágil
  expresion: { minCorte: 1.0, beta: 0.25 }, // gestos: más suave (unidades de cm)
  prediccion: 0.016,                         // s que se adelanta la posición
  retencion: 0.35,                           // s que se conserva la máscara sin cara
};

export class Seguidor {
  constructor(ajustes = AJUSTES) {
    this.ajustes = ajustes;
    this.salida = new Float32Array(NUM_PUNTOS * 3);   // píxeles, sin espejo
    this.local = new Float32Array(NUM_PUNTOS * 3);    // expresión en cm
    this.crudos = new Float32Array(NUM_PUNTOS * 3);
    this.filtroExpresion = new FiltroUnEuro(NUM_PUNTOS * 3, ajustes.expresion);
    this.filtroPose = new FiltroUnEuro(8, ajustes.pose);
    this.vectorPose = new Float32Array(8);
    this.q = [1, 0, 0, 0];       // giro (w, x, y, z) de la cara canónica a la cámara
    this.escala = 1;              // píxeles por cm
    this.t = [0, 0, 0];           // posición del origen de la cara (píxeles)
    this.ultimaCara = -Infinity;
    this.hayPose = false;
    this.error = 0;               // error medio del ajuste (px), para depurar

    // Centro de los puntos estables de la referencia.
    this.refCentro = [0, 0, 0];
    for (const i of ESTABLES) for (let k = 0; k < 3; k++) this.refCentro[k] += REFERENCIA[i * 3 + k];
    for (let k = 0; k < 3; k++) this.refCentro[k] /= ESTABLES.length;
    this.refEscala2 = 0;
    for (const i of ESTABLES) {
      for (let k = 0; k < 3; k++) this.refEscala2 += (REFERENCIA[i * 3 + k] - this.refCentro[k]) ** 2;
    }
  }

  /**
   * @param puntos  faceLandmarks[0] de MediaPipe (x, y en 0..1, z con escala de x)
   * @returns los 468 puntos filtrados en píxeles (x a la derecha, y hacia arriba, sin espejo)
   */
  actualizar(puntos, ancho, alto, tiempo) {
    const c = this.crudos;
    for (let i = 0; i < NUM_PUNTOS; i++) {
      c[i * 3] = puntos[i].x * ancho;
      c[i * 3 + 1] = (1 - puntos[i].y) * alto;
      c[i * 3 + 2] = -puntos[i].z * ancho;
    }

    // 1. Pose rígida medida en este cuadro.
    const { q, s, t } = this.ajustarPose(c);

    // 2. Expresión: puntos llevados al sistema de la cara canónica.
    const L = this.local;
    const [w, x, y, z] = q;
    for (let i = 0; i < NUM_PUNTOS; i++) {
      const px = (c[i * 3] - t[0]) / s;
      const py = (c[i * 3 + 1] - t[1]) / s;
      const pz = (c[i * 3 + 2] - t[2]) / s;
      rotar(w, -x, -y, -z, px, py, pz, L, i * 3);
    }
    this.filtroExpresion.filtrar(L, tiempo);

    // 3. Suavizado de la pose (en unidades relativas al ancho de la imagen).
    if (this.hayPose && dot4(q, this.q) < 0) for (let k = 0; k < 4; k++) q[k] = -q[k];
    const v = this.vectorPose;
    v[0] = t[0] / ancho; v[1] = t[1] / ancho; v[2] = t[2] / ancho;
    v[3] = (s * 18) / ancho;   // alto aproximado de la cara
    v[4] = q[0]; v[5] = q[1]; v[6] = q[2]; v[7] = q[3];
    this.filtroPose.filtrar(v, tiempo);
    const lead = this.ajustes.prediccion;
    const d = this.filtroPose.dx;
    this.t = [(v[0] + d[0] * lead) * ancho, (v[1] + d[1] * lead) * ancho, (v[2] + d[2] * lead) * ancho];
    this.escala = (v[3] * ancho) / 18;
    const n = Math.hypot(v[4], v[5], v[6], v[7]) || 1;
    this.q = [v[4] / n, v[5] / n, v[6] / n, v[7] / n];
    this.hayPose = true;
    this.ultimaCara = tiempo;

    this.reconstruir();
    return this.salida;
  }

  /** Recalcula la salida con la pose y la expresión actuales. */
  reconstruir() {
    const [w, x, y, z] = this.q;
    const s = this.escala;
    const out = this.salida;
    const L = this.local;
    for (let i = 0; i < NUM_PUNTOS; i++) {
      rotar(w, x, y, z, L[i * 3], L[i * 3 + 1], L[i * 3 + 2], out, i * 3);
      out[i * 3] = out[i * 3] * s + this.t[0];
      out[i * 3 + 1] = out[i * 3 + 1] * s + this.t[1];
      out[i * 3 + 2] = out[i * 3 + 2] * s + this.t[2];
    }
  }

  /** Cuánto debe verse la máscara (1 = cara detectada, baja a 0 al perderla). */
  visibilidad(tiempo) {
    if (!this.hayPose) return 0;
    const sin = tiempo - this.ultimaCara;
    if (sin <= 0.05) return 1;
    return Math.max(0, 1 - (sin - 0.05) / this.ajustes.retencion);
  }

  reiniciar() {
    this.hayPose = false;
    this.filtroExpresion.reiniciar();
    this.filtroPose.reiniciar();
  }

  /** Vector "hacia el frente" de la cara (en píxeles, sin espejo). */
  frente(destino = [0, 0, 0]) {
    const [w, x, y, z] = this.q;
    rotar(w, x, y, z, 0, 0, 1, destino, 0);
    return destino;
  }

  /** Ángulos aproximados en grados: giro (izq/der), inclinación (arriba/abajo), ladeo. */
  angulos() {
    const [w, x, y, z] = this.q;
    const giro = Math.asin(Math.max(-1, Math.min(1, 2 * (w * y - z * x))));
    const inclinacion = Math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y));
    const ladeo = Math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z));
    const g = 180 / Math.PI;
    return { giro: giro * g, inclinacion: inclinacion * g, ladeo: ladeo * g };
  }

  /** Ajuste de semejanza (giro + tamaño + posición) con el método de Horn. */
  ajustarPose(c) {
    const pc = [0, 0, 0];
    for (const i of ESTABLES) for (let k = 0; k < 3; k++) pc[k] += c[i * 3 + k];
    for (let k = 0; k < 3; k++) pc[k] /= ESTABLES.length;
    const rc = this.refCentro;

    // S[a][b] = Σ ref'_a · obs'_b
    let sxx = 0, sxy = 0, sxz = 0, syx = 0, syy = 0, syz = 0, szx = 0, szy = 0, szz = 0;
    for (const i of ESTABLES) {
      const ax = REFERENCIA[i * 3] - rc[0], ay = REFERENCIA[i * 3 + 1] - rc[1], az = REFERENCIA[i * 3 + 2] - rc[2];
      const bx = c[i * 3] - pc[0], by = c[i * 3 + 1] - pc[1], bz = c[i * 3 + 2] - pc[2];
      sxx += ax * bx; sxy += ax * by; sxz += ax * bz;
      syx += ay * bx; syy += ay * by; syz += ay * bz;
      szx += az * bx; szy += az * by; szz += az * bz;
    }
    const N = [
      [sxx + syy + szz, syz - szy, szx - sxz, sxy - syx],
      [syz - szy, sxx - syy - szz, sxy + syx, szx + sxz],
      [szx - sxz, sxy + syx, -sxx + syy - szz, syz + szy],
      [sxy - syx, szx + sxz, syz + szy, -sxx - syy + szz],
    ];
    const q = vectorPropioMayor(N);
    const [w, x, y, z] = q;

    // Escala: Σ obs'·R·ref' / Σ |ref'|²
    let num = 0;
    let err = 0;
    const r = [0, 0, 0];
    for (const i of ESTABLES) {
      rotar(w, x, y, z, REFERENCIA[i * 3] - rc[0], REFERENCIA[i * 3 + 1] - rc[1], REFERENCIA[i * 3 + 2] - rc[2], r, 0);
      num += r[0] * (c[i * 3] - pc[0]) + r[1] * (c[i * 3 + 1] - pc[1]) + r[2] * (c[i * 3 + 2] - pc[2]);
    }
    const s = num / this.refEscala2;
    rotar(w, x, y, z, rc[0], rc[1], rc[2], r, 0);
    const t = [pc[0] - s * r[0], pc[1] - s * r[1], pc[2] - s * r[2]];

    for (const i of ESTABLES) {
      rotar(w, x, y, z, REFERENCIA[i * 3], REFERENCIA[i * 3 + 1], REFERENCIA[i * 3 + 2], r, 0);
      err += Math.hypot(r[0] * s + t[0] - c[i * 3], r[1] * s + t[1] - c[i * 3 + 1], r[2] * s + t[2] - c[i * 3 + 2]);
    }
    this.error = err / ESTABLES.length;
    return { q, s, t };
  }
}

/** Rota (vx, vy, vz) con el cuaternión (w, x, y, z) y lo escribe en out[o..o+2]. */
function rotar(w, x, y, z, vx, vy, vz, out, o) {
  // v' = v + 2w(q×v) + 2 q×(q×v)
  const cx = y * vz - z * vy;
  const cy = z * vx - x * vz;
  const cz = x * vy - y * vx;
  out[o] = vx + 2 * (w * cx + y * cz - z * cy);
  out[o + 1] = vy + 2 * (w * cy + z * cx - x * cz);
  out[o + 2] = vz + 2 * (w * cz + x * cy - y * cx);
}

function dot4(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
}

/** Vector propio del mayor valor propio de una matriz simétrica 4x4 (método de Jacobi). */
function vectorPropioMayor(A) {
  const a = A.map((f) => f.slice());
  const v = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]];
  for (let barrido = 0; barrido < 12; barrido++) {
    let fuera = 0;
    for (let p = 0; p < 3; p++) for (let q = p + 1; q < 4; q++) fuera += a[p][q] * a[p][q];
    if (fuera < 1e-18) break;
    for (let p = 0; p < 3; p++) {
      for (let q = p + 1; q < 4; q++) {
        if (Math.abs(a[p][q]) < 1e-30) continue;
        const theta = (a[q][q] - a[p][p]) / (2 * a[p][q]);
        const t = Math.sign(theta || 1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
        const cs = 1 / Math.sqrt(t * t + 1);
        const sn = t * cs;
        for (let k = 0; k < 4; k++) {
          const akp = a[k][p], akq = a[k][q];
          a[k][p] = cs * akp - sn * akq;
          a[k][q] = sn * akp + cs * akq;
        }
        for (let k = 0; k < 4; k++) {
          const apk = a[p][k], aqk = a[q][k];
          a[p][k] = cs * apk - sn * aqk;
          a[q][k] = sn * apk + cs * aqk;
        }
        for (let k = 0; k < 4; k++) {
          const vkp = v[k][p], vkq = v[k][q];
          v[k][p] = cs * vkp - sn * vkq;
          v[k][q] = sn * vkp + cs * vkq;
        }
      }
    }
  }
  let mejor = 0;
  for (let k = 1; k < 4; k++) if (a[k][k] > a[mejor][mejor]) mejor = k;
  const q = [v[0][mejor], v[1][mejor], v[2][mejor], v[3][mejor]];
  if (q[0] < 0) for (let k = 0; k < 4; k++) q[k] = -q[k];
  return q;
}
