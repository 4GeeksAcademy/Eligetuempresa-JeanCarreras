#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
LOG_FILE="${LOG_FILE:-/tmp/uvicorn-dev-cycle.log}"

STARTED_BY_SCRIPT=0

cleanup() {
  if [[ "$STARTED_BY_SCRIPT" -eq 1 ]]; then
    PORT="$PORT" bash "$ROOT_DIR/scripts/stop_api_local.sh" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

echo "== Brasaland dev cycle =="

echo "Validando prerequisitos de entorno"
bash "$ROOT_DIR/scripts/check_env.sh"

echo "Asegurando puerto limpio en :$PORT"
PORT="$PORT" bash "$ROOT_DIR/scripts/stop_api_local.sh" >/dev/null 2>&1 || true

echo "Levantando API local en background (log: $LOG_FILE)"
HOST="$HOST" PORT="$PORT" bash "$ROOT_DIR/scripts/run_api_local.sh" >"$LOG_FILE" 2>&1 &
STARTED_BY_SCRIPT=1

for _ in {1..40}; do
  if curl -fsS "http://localhost:$PORT/health" >/dev/null 2>&1; then
    echo "API lista"
    break
  fi
  sleep 0.5
done

if ! curl -fsS "http://localhost:$PORT/health" >/dev/null 2>&1; then
  echo "La API no inicio a tiempo. Ultimas lineas de log:"
  tail -n 40 "$LOG_FILE" || true
  exit 1
fi

echo "Ejecutando QA local completa"
bash "$ROOT_DIR/scripts/run_qa_local.sh"

echo "Dev cycle completado correctamente"
