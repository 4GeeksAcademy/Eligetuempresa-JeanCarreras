#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"

if ! command -v lsof >/dev/null 2>&1; then
  echo "lsof no esta disponible en el entorno."
  echo "No se puede resolver el PID por puerto automaticamente."
  exit 1
fi

PIDS="$(lsof -t -i TCP:"$PORT" -sTCP:LISTEN | tr '\n' ' ')"

if [[ -z "${PIDS// }" ]]; then
  echo "No hay procesos escuchando en el puerto $PORT"
  exit 0
fi

echo "Deteniendo procesos en puerto $PORT: $PIDS"
kill $PIDS

# Espera corta para verificar cierre
for _ in {1..10}; do
  REMAINING="$(lsof -t -i TCP:"$PORT" -sTCP:LISTEN 2>/dev/null | tr '\n' ' ' || true)"
  if [[ -z "${REMAINING// }" ]]; then
    echo "Puerto $PORT liberado"
    exit 0
  fi
  sleep 0.2
done

echo "Algunos procesos no cerraron a tiempo. Forzando cierre..."
kill -9 $PIDS >/dev/null 2>&1 || true

if lsof -t -i TCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "No se pudo liberar el puerto $PORT"
  exit 1
fi

echo "Puerto $PORT liberado"
