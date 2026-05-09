#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$ROOT_DIR/services/brasaland-api"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

if [[ ! -d "$SERVICE_DIR" ]]; then
  echo "No se encontro el servicio en: $SERVICE_DIR"
  exit 1
fi

if [[ "${SKIP_PREFLIGHT:-0}" != "1" ]]; then
  echo "Validando prerequisitos de entorno"
  bash "$ROOT_DIR/scripts/check_env.sh"
fi

PY_BIN=""
if [[ -x "$SERVICE_DIR/.venv/bin/python" ]]; then
  PY_BIN="$SERVICE_DIR/.venv/bin/python"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PY_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY_BIN="$(command -v python3)"
else
  echo "No se encontro un interprete Python."
  echo "Tip: crea un entorno virtual en $SERVICE_DIR/.venv o $ROOT_DIR/.venv e instala requirements."
  exit 1
fi

if [[ "$PY_BIN" == *"python3"* ]]; then
  echo "Usando python del sistema: $PY_BIN"
  echo "Recomendado: usar un entorno virtual con requirements instalados."
fi

echo "Levantando Brasaland API en http://$HOST:$PORT"
cd "$SERVICE_DIR"
exec "$PY_BIN" -m uvicorn app.main:app --host "$HOST" --port "$PORT"
