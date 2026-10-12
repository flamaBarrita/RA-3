import * as THREE from '../vendor/three.module.min.js';
import { NUM_PUNTOS, OVALO, ANILLOS, UVS, TRIANGULOS } from './datos-cara.js';
import { Seguidor } from './seguimiento.js';

const _centro = new THREE.Vector3();
const _frente = new THREE.Vector3();
const _arriba = new THREE.Vector3();
const _tmp = new THREE.Vector3();
const _f = [0, 0, 0];

/**
 * Malla de la máscara: los 468 puntos de MediaPipe (con el mapa UV de su modelo
 * canónico) más dos anillos alrededor del contorno para la frente y las sienes.
 * Los ojos y el interior de la boca no tienen triángulos, así que siempre se ven
 * los ojos y la boca reales de la persona.
 *
 * Las coordenadas están en píxeles de la cámara y ya vienen en espejo (selfie).
 */
export class MallaMascara {
  constructor(material) {
    this.total = NUM_PUNTOS + OVALO.length * ANILLOS.length;
    this.posiciones = new Float32Array(this.total * 3);
    this.seguidor = new Seguidor();

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(this.posiciones, 3).setUsage(THREE.DynamicDrawUsage));
    geo.setAttribute('uv', new THREE.BufferAttribute(UVS, 2));
    geo.setIndex(new THREE.BufferAttribute(TRIANGULOS, 1));
    this.geometria = geo;
    this.material = material;

    this.malla = new THREE.Mesh(geo, material);
    this.malla.frustumCulled = false;
    this.malla.visible = false;

    this.altoCara = 1;
    this.ancho = 1;
  }

  /** Nuevo cuadro con cara detectada. */
  actualizar(puntos, ancho, alto, t) {
    this.ancho = ancho;
    this.colocar(this.seguidor.actualizar(puntos, ancho, alto, t));
  }

  /** Cuadro sin cara: mantiene la última pose y la desvanece. Devuelve si sigue visible. */
  sinCara(t) {
    const vis = this.seguidor.visibilidad(t);
    this.material.opacity = vis;
    if (vis <= 0) this.ocultar();
    return vis > 0;
  }

  colocar(s) {
    const p = this.posiciones;
    for (let i = 0; i < NUM_PUNTOS; i++) {
      p[i * 3] = this.ancho - s[i * 3];        // espejo horizontal
      p[i * 3 + 1] = s[i * 3 + 1];
      p[i * 3 + 2] = s[i * 3 + 2];
    }

    // Centro del contorno, tamaño y hacia dónde mira la cara (de la pose rígida).
    _centro.set(0, 0, 0);
    for (const i of OVALO) _centro.add(this.punto(i, _tmp));
    _centro.divideScalar(OVALO.length);
    this.altoCara = _arriba.subVectors(this.punto(10, _arriba), this.punto(152, _tmp)).length();
    this.seguidor.frente(_f);
    _frente.set(-_f[0], _f[1], _f[2]);

    // Anillos de la frente y las sienes (misma regla que tools/generar_datos_cara.py).
    let k = NUM_PUNTOS;
    for (const anillo of ANILLOS) {
      for (const i of OVALO) {
        this.punto(i, _tmp);
        p[k * 3] = _tmp.x + (_tmp.x - _centro.x) * anillo.k - _frente.x * this.altoCara * anillo.atras;
        p[k * 3 + 1] = _tmp.y + (_tmp.y - _centro.y) * anillo.k - _frente.y * this.altoCara * anillo.atras;
        p[k * 3 + 2] = _tmp.z + (_tmp.z - _centro.z) * anillo.k - _frente.z * this.altoCara * anillo.atras;
        k++;
      }
    }

    this.geometria.attributes.position.needsUpdate = true;
    this.geometria.computeVertexNormals();
    this.material.opacity = 1;
    this.malla.visible = true;
  }

  ocultar() {
    this.malla.visible = false;
    this.seguidor.reiniciar();
  }

  /** Vector hacia el frente de la cara, en el espacio de la pantalla (con espejo). */
  frente(destino = new THREE.Vector3()) {
    return destino.copy(_frente);
  }

  /** Posición (en píxeles) de un punto de MediaPipe. */
  punto(i, destino = new THREE.Vector3()) {
    return destino.fromArray(this.posiciones, i * 3);
  }

  /** Punto medio entre varios puntos. */
  medio(indices, destino = new THREE.Vector3()) {
    destino.set(0, 0, 0);
    for (const i of indices) destino.add(this.punto(i, _tmp));
    return destino.divideScalar(indices.length);
  }
}
