import * as THREE from '../vendor/three.module.min.js';

/** Formas disponibles para las partículas. */
export const FORMA = { BRILLO: 0, PETALO: 1, PAPEL: 2 };

const VERTICE = /* glsl */ `
  attribute vec3 color;
  attribute float tam;
  attribute float alfa;
  attribute float forma;
  attribute float giro;
  uniform float escala;
  varying vec3 vColor;
  varying float vAlfa;
  varying float vForma;
  varying float vGiro;
  void main() {
    vColor = color;
    vAlfa = alfa;
    vForma = forma;
    vGiro = giro;
    gl_PointSize = tam * escala;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const FRAGMENTO = /* glsl */ `
  uniform bool aditivo;
  varying vec3 vColor;
  varying float vAlfa;
  varying float vForma;
  varying float vGiro;
  void main() {
    vec2 p = gl_PointCoord - 0.5;
    float c = cos(vGiro), s = sin(vGiro);
    p = vec2(c * p.x - s * p.y, s * p.x + c * p.y);
    vec3 color = vColor;
    float a;
    if (vForma < 0.5) {
      // Brillo redondo (chispas, velas)
      float d = length(p) * 2.0;
      a = smoothstep(1.0, 0.0, d);
      a *= a;
    } else if (vForma < 1.5) {
      // Pétalo de cempasúchil: gota alargada con una vena más oscura
      vec2 q = vec2(p.x * 2.6, p.y * 2.0 + 0.1);
      float d = length(q) - 0.42 * (1.0 - 0.35 * (p.y + 0.5));
      a = 1.0 - smoothstep(-0.03, 0.03, d);
      color *= 1.0 - 0.35 * smoothstep(0.06, 0.0, abs(p.x)) * step(-0.3, p.y);
      color *= 0.8 + 0.4 * (0.5 - p.y);
    } else {
      // Papel picado: rectángulo con agujeros calados
      vec2 q = abs(p) * vec2(2.0, 2.6);
      a = 1.0 - smoothstep(0.88, 0.95, max(q.x, q.y));
      vec2 r = fract(p * vec2(4.0, 3.0)) - 0.5;
      float hueco = 1.0 - smoothstep(0.16, 0.22, length(r));
      a *= 1.0 - hueco * step(max(q.x, q.y), 0.7);
    }
    if (aditivo) gl_FragColor = vec4(color * a, a * vAlfa);
    else gl_FragColor = vec4(color, a * vAlfa);
  }
`;

/**
 * Sistema sencillo de partículas en píxeles de pantalla: brillos, pétalos de
 * cempasúchil y papel picado. Los pétalos y el papel se balancean como si
 * cayeran por el aire.
 */
export class Particulas {
  constructor({ max = 900, aditivo = false } = {}) {
    this.max = max;
    this.pos = new Float32Array(max * 3);
    this.col = new Float32Array(max * 3);
    this.tam = new Float32Array(max);
    this.alfa = new Float32Array(max);
    this.forma = new Float32Array(max);
    this.giro = new Float32Array(max);
    this.velGiro = new Float32Array(max);
    this.balanceo = new Float32Array(max);
    this.fase = new Float32Array(max);
    this.vel = new Float32Array(max * 3);
    this.vida = new Float32Array(max);
    this.vidaMax = new Float32Array(max);
    this.tamBase = new Float32Array(max);
    this.gravedad = new Float32Array(max);
    this.arrastre = new Float32Array(max);
    this.siguiente = 0;
    this.tiempo = 0;

    const geo = new THREE.BufferGeometry();
    const din = (arr, n) => new THREE.BufferAttribute(arr, n).setUsage(THREE.DynamicDrawUsage);
    geo.setAttribute('position', din(this.pos, 3));
    geo.setAttribute('color', din(this.col, 3));
    geo.setAttribute('tam', din(this.tam, 1));
    geo.setAttribute('alfa', din(this.alfa, 1));
    geo.setAttribute('forma', din(this.forma, 1));
    geo.setAttribute('giro', din(this.giro, 1));
    this.geometria = geo;

    this.material = new THREE.ShaderMaterial({
      uniforms: { escala: { value: 1 }, aditivo: { value: aditivo } },
      vertexShader: VERTICE,
      fragmentShader: FRAGMENTO,
      transparent: true,
      depthTest: false,
      depthWrite: false,
      blending: aditivo ? THREE.AdditiveBlending : THREE.NormalBlending,
    });
    this.puntos = new THREE.Points(geo, this.material);
    this.puntos.frustumCulled = false;
    this.puntos.renderOrder = 10;
  }

  /**
   * @param origen    THREE.Vector3 en píxeles
   * @param cantidad  número de partículas
   * @param o         { colores, forma, direccion {x,y}, apertura (rad), velocidad [min,max],
   *                    vida [min,max] s, tam [min,max] px, gravedad px/s², radio px,
   *                    balanceo px/s, arrastre, ancho (para emitir en una línea) }
   */
  emitir(origen, cantidad, o) {
    const dir = Math.atan2(o.direccion.y, o.direccion.x);
    for (let n = 0; n < cantidad; n++) {
      const i = this.siguiente;
      this.siguiente = (this.siguiente + 1) % this.max;
      const ang = dir + (Math.random() - 0.5) * o.apertura;
      const vel = rango(o.velocidad);
      const r = (o.radio ?? 0) * Math.sqrt(Math.random());
      const angR = Math.random() * Math.PI * 2;
      const linea = ((o.ancho ?? 0) * (Math.random() - 0.5));
      this.pos[i * 3] = origen.x + Math.cos(angR) * r + linea;
      this.pos[i * 3 + 1] = origen.y + Math.sin(angR) * r;
      this.pos[i * 3 + 2] = origen.z + 50;
      this.vel[i * 3] = Math.cos(ang) * vel;
      this.vel[i * 3 + 1] = Math.sin(ang) * vel;
      const c = o.colores[(Math.random() * o.colores.length) | 0];
      this.col[i * 3] = c.r;
      this.col[i * 3 + 1] = c.g;
      this.col[i * 3 + 2] = c.b;
      this.vidaMax[i] = this.vida[i] = rango(o.vida);
      this.tamBase[i] = rango(o.tam);
      this.gravedad[i] = o.gravedad ?? 0;
      this.forma[i] = o.forma ?? FORMA.BRILLO;
      this.giro[i] = Math.random() * Math.PI * 2;
      this.velGiro[i] = (Math.random() - 0.5) * (o.giro ?? 0);
      this.balanceo[i] = (o.balanceo ?? 0) * (0.5 + Math.random());
      this.fase[i] = Math.random() * Math.PI * 2;
      this.arrastre[i] = o.arrastre ?? 1.2;
    }
  }

  actualizar(dt) {
    this.tiempo += dt;
    for (let i = 0; i < this.max; i++) {
      if (this.vida[i] <= 0) {
        this.alfa[i] = 0;
        this.tam[i] = 0;
        continue;
      }
      this.vida[i] -= dt;
      const t = Math.max(this.vida[i] / this.vidaMax[i], 0);
      this.vel[i * 3 + 1] -= this.gravedad[i] * dt;
      const frena = Math.max(0, 1 - this.arrastre[i] * dt);
      this.vel[i * 3] *= frena;
      if (this.arrastre[i] > 2) this.vel[i * 3 + 1] *= frena;
      const vaiven = Math.sin(this.tiempo * 3 + this.fase[i]) * this.balanceo[i];
      this.pos[i * 3] += (this.vel[i * 3] + vaiven) * dt;
      this.pos[i * 3 + 1] += this.vel[i * 3 + 1] * dt;
      this.giro[i] += this.velGiro[i] * dt;
      const esFigura = this.forma[i] > 0.5;
      this.alfa[i] = esFigura ? Math.min(1, t * 4) : t;
      this.tam[i] = esFigura ? this.tamBase[i] : this.tamBase[i] * (0.4 + 0.6 * t);
    }
    const a = this.geometria.attributes;
    for (const k of ['position', 'color', 'tam', 'alfa', 'forma', 'giro']) a[k].needsUpdate = true;
  }
}

function rango([min, max]) {
  return min + Math.random() * (max - min);
}
