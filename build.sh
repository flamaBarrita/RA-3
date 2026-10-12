#!/usr/bin/env bash
# Compilación para Vercel (u otro hosting estático): arma la carpeta public/ con
# todo lo que necesita el filtro. Si el repositorio ya trae las librerías y el
# modelo, solo los copia; si no, los toma de npm / Google.
set -euo pipefail
OUT=public
rm -rf "$OUT"
mkdir -p "$OUT/vendor/mediapipe/wasm" "$OUT/modelos"
cp -r index.html css js assets "$OUT/"

# Librerías (three.js y MediaPipe)
if [ -f vendor/three.module.min.js ]; then
  cp -r vendor/. "$OUT/vendor/"
else
  cp node_modules/three/build/three.module.min.js "$OUT/vendor/"
  cp node_modules/@mediapipe/tasks-vision/vision_bundle.mjs "$OUT/vendor/mediapipe/"
  cp node_modules/@mediapipe/tasks-vision/wasm/* "$OUT/vendor/mediapipe/wasm/"
fi

# Modelo de detección facial
if [ -f modelos/face_landmarker.task ]; then
  cp modelos/face_landmarker.task "$OUT/modelos/"
else
  curl -sSfL -o "$OUT/modelos/face_landmarker.task" \
    https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
fi
echo "Listo: $(find "$OUT" -type f | wc -l) archivos en $OUT/"
