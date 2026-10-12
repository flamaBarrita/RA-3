/** Graba el lienzo (con el audio del filtro) y descarga el video al terminar. */
export class Grabador {
  constructor(lienzo, obtenerAudio) {
    this.lienzo = lienzo;
    this.obtenerAudio = obtenerAudio;
    this.grabadora = null;
    this.partes = [];
  }

  get disponible() {
    return typeof MediaRecorder !== 'undefined' && !!this.lienzo.captureStream;
  }

  get grabando() {
    return this.grabadora?.state === 'recording';
  }

  iniciar() {
    const flujo = this.lienzo.captureStream(30);
    const audio = this.obtenerAudio();
    if (audio) for (const pista of audio.getAudioTracks()) flujo.addTrack(pista);

    const tipos = ['video/mp4;codecs=avc1', 'video/mp4', 'video/webm;codecs=vp9,opus', 'video/webm'];
    const tipo = tipos.find((t) => MediaRecorder.isTypeSupported(t)) ?? '';
    this.grabadora = new MediaRecorder(flujo, tipo ? { mimeType: tipo, videoBitsPerSecond: 6e6 } : undefined);
    this.partes = [];
    this.grabadora.ondataavailable = (e) => e.data.size && this.partes.push(e.data);
    this.grabadora.onstop = () => this.descargar();
    this.grabadora.start(500);
  }

  detener() {
    if (this.grabando) this.grabadora.stop();
  }

  descargar() {
    const tipo = this.grabadora.mimeType || 'video/webm';
    const blob = new Blob(this.partes, { type: tipo });
    const enlace = document.createElement('a');
    enlace.href = URL.createObjectURL(blob);
    enlace.download = `mascara-dia-de-muertos-${Date.now()}.${tipo.includes('mp4') ? 'mp4' : 'webm'}`;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    setTimeout(() => URL.revokeObjectURL(enlace.href), 10000);
  }
}
