/**
 * Detección de gestos a partir de los "blendshapes" de MediaPipe (valores 0..1).
 *
 * Cada gesto usa:
 *  - un umbral de entrada y otro de salida (histéresis) para que no parpadee,
 *  - un tiempo mínimo sostenido para ignorar ruido,
 *  - una pausa (enfriamiento) para evitar disparos repetidos,
 *  - una línea base que se adapta a la cara de cada persona (lentes, luz,
 *    cejas naturalmente altas, etc.): el umbral nunca queda por debajo de
 *    base + margen.
 */
class Gesto {
  constructor(nombre, { valor, umbral, salida, margen, minMs, enfriamientoMs }) {
    Object.assign(this, { nombre, valor, umbral, salida, margen, minMs, enfriamientoMs });
    this.activo = false;
    this.desde = null;
    this.ultimoDisparo = -Infinity;
    this.base = null;
    this.ultimoValor = 0;
  }

  actualizar(bs, ahora) {
    const v = this.valor(bs);
    this.ultimoValor = v;
    if (this.base === null) this.base = Math.min(v, this.salida);
    let entrada = Math.min(Math.max(this.umbral, this.base + this.margen), 0.9);
    if (!this.activo && v < entrada) this.base += 0.02 * (v - this.base);
    entrada = Math.min(Math.max(this.umbral, this.base + this.margen), 0.9);

    const salida = entrada - (this.umbral - this.salida);
    const evento = { inicio: false, fin: false };

    if (!this.activo) {
      if (v > entrada) {
        this.desde ??= ahora;
        if (ahora - this.desde >= this.minMs && ahora - this.ultimoDisparo >= this.enfriamientoMs) {
          this.activo = true;
          this.ultimoDisparo = ahora;
          evento.inicio = true;
        }
      } else {
        this.desde = null;
      }
    } else if (v < salida) {
      this.activo = false;
      this.desde = null;
      evento.fin = true;
    }
    return evento;
  }

  reiniciar() {
    this.activo = false;
    this.desde = null;
  }
}

export function crearGestos() {
  return [
    new Gesto('boca', {
      valor: (bs) => bs.jawOpen ?? 0,
      umbral: 0.5,          // boca abierta > 50 %
      salida: 0.35,
      margen: 0.3,
      minMs: 80,
      enfriamientoMs: 500,
    }),
    new Gesto('parpadeo', {
      valor: (bs) => Math.min(bs.eyeBlinkLeft ?? 0, bs.eyeBlinkRight ?? 0),
      umbral: 0.5,
      salida: 0.35,
      margen: 0.3,
      minMs: 50,
      enfriamientoMs: 700,
    }),
    new Gesto('cejas', {
      valor: (bs) => Math.max(bs.browInnerUp ?? 0,
        ((bs.browOuterUpLeft ?? 0) + (bs.browOuterUpRight ?? 0)) / 2),
      umbral: 0.55,
      salida: 0.4,
      margen: 0.3,
      minMs: 120,
      enfriamientoMs: 1000,
    }),
  ];
}

/** Convierte la lista de categorías de MediaPipe en un objeto {nombre: valor}. */
export function blendshapesComoObjeto(resultado) {
  const bs = {};
  const categorias = resultado.faceBlendshapes?.[0]?.categories ?? [];
  for (const c of categorias) bs[c.categoryName] = c.score;
  return bs;
}
