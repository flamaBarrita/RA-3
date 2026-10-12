/**
 * Sonidos del filtro. Por defecto se sintetizan con Web Audio (no necesitan
 * archivos); si assets/mascara/mascara.json trae rutas en "sonidos", se usan esos
 * archivos en su lugar.
 *
 * Los navegadores no dejan reproducir audio hasta que la persona toca la
 * pantalla una vez, así que el contexto se crea en el primer toque.
 */
export class Sonido {
  constructor() {
    this.ctx = null;
    this.salida = null;     // nodo final (también se usa para grabar el audio)
    this.archivos = {};
    this.buffers = {};
    this.alActivar = null;
  }

  configurar(rutasPorGesto, base) {
    for (const [gesto, ruta] of Object.entries(rutasPorGesto ?? {})) {
      if (ruta) this.archivos[gesto] = base + ruta;
    }
  }

  get activo() {
    return this.ctx?.state === 'running';
  }

  activar() {
    if (!this.ctx) {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
      this.salida = this.ctx.createGain();
      this.salida.gain.value = 0.8;
      this.salida.connect(this.ctx.destination);
      this.grabacion = this.ctx.createMediaStreamDestination?.();
      if (this.grabacion) this.salida.connect(this.grabacion);
      this.cargarArchivos();
    }
    if (this.ctx.state !== 'running') this.ctx.resume();
    this.alActivar?.();
  }

  async cargarArchivos() {
    for (const [gesto, url] of Object.entries(this.archivos)) {
      try {
        const datos = await (await fetch(url)).arrayBuffer();
        this.buffers[gesto] = await this.ctx.decodeAudioData(datos);
      } catch (e) {
        console.warn('No se pudo cargar el sonido', url, e);
      }
    }
  }

  reproducir(gesto) {
    if (!this.activo) return;
    if (this.buffers[gesto]) {
      const fuente = this.ctx.createBufferSource();
      fuente.buffer = this.buffers[gesto];
      fuente.connect(this.salida);
      fuente.start();
      return;
    }
    if (gesto === 'boca') this.soplo();
    else if (gesto === 'cejas') this.campana();
    else if (gesto === 'parpadeo') this.destello();
  }

  envolvente(ganancia, t, ataque, pico, duracion) {
    ganancia.gain.setValueAtTime(0.0001, t);
    ganancia.gain.exponentialRampToValueAtTime(pico, t + ataque);
    ganancia.gain.exponentialRampToValueAtTime(0.0001, t + duracion);
  }

  /** Soplo de viento con campanitas para los pétalos de cempasúchil. */
  soplo() {
    const ctx = this.ctx;
    const t = ctx.currentTime;
    const dur = 1.2;

    const ruido = ctx.createBufferSource();
    const buf = ctx.createBuffer(1, ctx.sampleRate * dur, ctx.sampleRate);
    const datos = buf.getChannelData(0);
    for (let i = 0; i < datos.length; i++) datos[i] = Math.random() * 2 - 1;
    ruido.buffer = buf;
    const filtro = ctx.createBiquadFilter();
    filtro.type = 'bandpass';
    filtro.Q.value = 0.8;
    filtro.frequency.setValueAtTime(500, t);
    filtro.frequency.exponentialRampToValueAtTime(1800, t + dur * 0.6);
    const gRuido = ctx.createGain();
    this.envolvente(gRuido, t, 0.25, 0.25, dur);
    ruido.connect(filtro).connect(gRuido).connect(this.salida);
    ruido.start(t);
    ruido.stop(t + dur);

    [1047, 1319, 1568, 2093].forEach((f, k) => {
      const osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.value = f;
      const g = ctx.createGain();
      const t0 = t + 0.1 + k * 0.09;
      this.envolvente(g, t0, 0.01, 0.12, 0.9);
      osc.connect(g).connect(this.salida);
      osc.start(t0);
      osc.stop(t0 + 1);
    });
  }

  /** Campanas para el papel picado (cejas). */
  campana() {
    const ctx = this.ctx;
    const t = ctx.currentTime;
    [880, 1320, 1760, 2640].forEach((f, k) => {
      const osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.value = f;
      const g = ctx.createGain();
      this.envolvente(g, t + k * 0.04, 0.01, 0.25 / (k + 1), 1.2);
      osc.connect(g).connect(this.salida);
      osc.start(t + k * 0.04);
      osc.stop(t + 1.4);
    });
  }

  /** Destello corto para el cambio de color (parpadeo). */
  destello() {
    const ctx = this.ctx;
    const t = ctx.currentTime;
    const osc = ctx.createOscillator();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(1200, t);
    osc.frequency.exponentialRampToValueAtTime(2400, t + 0.12);
    const g = ctx.createGain();
    this.envolvente(g, t, 0.01, 0.15, 0.18);
    osc.connect(g).connect(this.salida);
    osc.start(t);
    osc.stop(t + 0.2);
  }
}
