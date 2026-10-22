import * as THREE from '../vendor/three.module.min.js';

/**
 * Material de "maquillaje": en lugar de pegar la textura como una calcomanía
 * plana, la pinta encima de la piel real.
 *
 *  - Toma la luz de la cara directamente del video (sombras de la nariz, ojeras,
 *    mejillas, luz de la ventana...) y oscurece o aclara la pintura igual.
 *  - Los tonos claros (la base hueso) dejan pasar un poco la piel, como la
 *    pintura facial de verdad.
 *
 * Ajustes en assets/mascara/mascara.json ("acabado") o en la dirección:
 *   ?acabado=plano      calcomanía plana, como antes (para comparar)
 */
const VERTICE = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const FRAGMENTO = /* glsl */ `
  uniform sampler2D mapa;
  uniform sampler2D video;
  uniform vec2 tamBuffer;
  uniform float opacidad;
  uniform float luzMedia;
  uniform float luzPiel;
  uniform float pielEnBlanco;
  uniform float contraste;
  uniform float detalle;
  uniform float radio;
  varying vec2 vUv;

  float lumVideo(vec2 s) {
    vec3 c = texture2D(video, vec2(1.0 - s.x, s.y)).rgb;
    return dot(c, vec3(0.2126, 0.7152, 0.0722));
  }

  void main() {
    vec4 pintura = texture2D(mapa, vUv);
    if (pintura.a < 0.02) discard;

    // Piel que está justo debajo de este píxel (el video se ve en espejo).
    vec2 s = gl_FragCoord.xy / tamBuffer;
    vec3 piel = texture2D(video, vec2(1.0 - s.x, s.y)).rgb;
    float lum = dot(piel, vec3(0.2126, 0.7152, 0.0722));

    // Luz suave (promedio alrededor del píxel): sombras grandes de la cara,
    // sin copiar los dientes, cejas o arrugas de debajo.
    vec2 r = vec2(radio, radio * tamBuffer.x / tamBuffer.y);
    float suave = lum;
    for (int k = 0; k < 8; k++) {
      float a = float(k) * 0.7854;
      vec2 d = vec2(cos(a), sin(a)) * r;
      suave += lumVideo(s + d) + lumVideo(s + d * 0.5);
    }
    suave /= 17.0;
    float l = mix(suave, lum, detalle);

    // Luz de la piel relativa a la luz media de la cara.
    float luz = clamp(l / max(luzMedia, 0.01), 0.3, 1.12);
    luz = pow(luz, contraste);
    vec3 color = pintura.rgb * mix(1.0, luz, luzPiel);

    // En los tonos claros se transparenta un poco la piel.
    float claro = smoothstep(0.45, 0.85, dot(pintura.rgb, vec3(0.3333)));
    float alfa = pintura.a * opacidad * (1.0 - pielEnBlanco * claro);
    // un toque del color de la piel sobre la base, como pintura sobre la cara
    color = mix(color, color * (0.8 + 0.4 * piel / max(lum, 0.01)), 0.2 * claro * luzPiel);

    gl_FragColor = vec4(color, alfa);
    #include <colorspace_fragment>
  }
`;

export const ACABADOS = {
  maquillaje: { luzPiel: 0.9, pielEnBlanco: 0.1, contraste: 0.9, detalle: 0.2, opacidad: 0.97 },
  plano: { luzPiel: 0, pielEnBlanco: 0, contraste: 1, detalle: 0, opacidad: 1 },
};

export function crearMaterialMaquillaje(texturaVideo) {
  const material = new THREE.ShaderMaterial({
    uniforms: {
      mapa: { value: null },
      video: { value: texturaVideo },
      tamBuffer: { value: new THREE.Vector2(1, 1) },
      opacidad: { value: 1 },
      luzMedia: { value: 0.35 },
      luzPiel: { value: ACABADOS.maquillaje.luzPiel },
      pielEnBlanco: { value: ACABADOS.maquillaje.pielEnBlanco },
      contraste: { value: ACABADOS.maquillaje.contraste },
      detalle: { value: ACABADOS.maquillaje.detalle },
      radio: { value: 0.012 },
    },
    vertexShader: VERTICE,
    fragmentShader: FRAGMENTO,
    transparent: true,
    side: THREE.DoubleSide,
  });
  material.opacidadBase = ACABADOS.maquillaje.opacidad;
  return material;
}

/** Aplica un acabado ("maquillaje", "plano") con ajustes opcionales encima. */
export function aplicarAcabado(material, nombre = 'maquillaje', ajustes = {}) {
  const a = { ...(ACABADOS[nombre] ?? ACABADOS.maquillaje), ...ajustes };
  material.uniforms.luzPiel.value = a.luzPiel;
  material.uniforms.pielEnBlanco.value = a.pielEnBlanco;
  material.uniforms.contraste.value = a.contraste;
  material.uniforms.detalle.value = a.detalle;
  material.opacidadBase = a.opacidad;
}

/**
 * Mide la luz media de la cara en el video (lineal, 0..1) usando una imagen
 * pequeña. Se usa como referencia para saber qué partes están en sombra.
 */
export class MedidorLuz {
  constructor(video) {
    this.video = video;
    this.lienzo = document.createElement('canvas');
    this.lienzo.width = 64;
    this.lienzo.height = 36;
    this.ctx = this.lienzo.getContext('2d', { willReadFrequently: true });
    this.valor = 0.35;
    this.cuadro = 0;
  }

  /** caja = {x0, y0, x1, y1} de la cara en píxeles del video (sin espejo, y hacia abajo). */
  actualizar(caja) {
    if (this.cuadro++ % 5 !== 0) return this.valor;
    const { video, ctx, lienzo } = this;
    const W = lienzo.width;
    const H = lienzo.height;
    try {
      ctx.drawImage(video, 0, 0, W, H);
    } catch {
      return this.valor;
    }
    const sx = W / video.videoWidth;
    const sy = H / video.videoHeight;
    // parte central de la cara (sin pelo ni fondo)
    const cx = (caja.x0 + caja.x1) / 2;
    const cy = (caja.y0 + caja.y1) / 2;
    const w = (caja.x1 - caja.x0) * 0.3;
    const h = (caja.y1 - caja.y0) * 0.3;
    const x0 = Math.max(0, Math.floor((cx - w) * sx));
    const x1 = Math.min(W, Math.ceil((cx + w) * sx));
    const y0 = Math.max(0, Math.floor((cy - h) * sy));
    const y1 = Math.min(H, Math.ceil((cy + h) * sy));
    if (x1 <= x0 || y1 <= y0) return this.valor;
    const datos = ctx.getImageData(x0, y0, x1 - x0, y1 - y0).data;
    let suma = 0;
    for (let i = 0; i < datos.length; i += 4) {
      suma += 0.2126 * lineal(datos[i]) + 0.7152 * lineal(datos[i + 1]) + 0.0722 * lineal(datos[i + 2]);
    }
    const medida = suma / (datos.length / 4);
    this.valor += (medida - this.valor) * 0.3;
    return this.valor;
  }
}

function lineal(v) {
  const c = v / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}
