#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DASHBOARD_DIR="$ROOT_DIR/uis/executive-dashboard"

API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
DASHBOARD_HOST="${DASHBOARD_HOST:-0.0.0.0}"
DASHBOARD_PORT="${DASHBOARD_PORT:-4173}"

API_LOG_FILE="${API_LOG_FILE:-/tmp/brasaland-api.log}"
DASHBOARD_LOG_FILE="${DASHBOARD_LOG_FILE:-/tmp/brasaland-dashboard.log}"

STARTED_API=0
DASHBOARD_PID=""

cleanup() {
  if [[ -n "$DASHBOARD_PID" ]] && kill -0 "$DASHBOARD_PID" >/dev/null 2>&1; then
    kill "$DASHBOARD_PID" >/dev/null 2>&1 || true
  fi

  if [[ "$STARTED_API" -eq 1 ]]; then
    PORT="$API_PORT" bash "$ROOT_DIR/scripts/stop_api_local.sh" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

if [[ ! -d "$DASHBOARD_DIR" ]]; then
  echo "No se encontro el dashboard en: $DASHBOARD_DIR"
  exit 1
fi

echo "Validando prerequisitos de entorno"
bash "$ROOT_DIR/scripts/check_env.sh"

if lsof -nP -iTCP:"$API_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "API detectada en puerto $API_PORT. Se reutilizara el proceso existente."
else
  echo "Levantando API local en background (log: $API_LOG_FILE)"
  HOST="$API_HOST" PORT="$API_PORT" bash "$ROOT_DIR/scripts/run_api_local.sh" >"$API_LOG_FILE" 2>&1 &
  STARTED_API=1
fi

for _ in {1..40}; do
  if curl -fsS "http://localhost:$API_PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if ! curl -fsS "http://localhost:$API_PORT/health" >/dev/null 2>&1; then
  echo "La API no responde en http://localhost:$API_PORT/health"
  if [[ "$STARTED_API" -eq 1 ]]; then
    echo "Ultimas lineas del log de API:"
    tail -n 40 "$API_LOG_FILE" || true
  fi
  exit 1
fi

if lsof -nP -iTCP:"$DASHBOARD_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "El puerto del dashboard $DASHBOARD_PORT ya esta en uso."
  echo "Define otro puerto con DASHBOARD_PORT, por ejemplo:"
  echo "  DASHBOARD_PORT=4174 bash scripts/run_dashboard_local.sh"
  exit 1
fi

echo "Levantando dashboard en background (log: $DASHBOARD_LOG_FILE)"
cd "$DASHBOARD_DIR"
python3 -m http.server "$DASHBOARD_PORT" --bind "$DASHBOARD_HOST" >"$DASHBOARD_LOG_FILE" 2>&1 &
DASHBOARD_PID="$!"

sleep 0.5
if ! kill -0 "$DASHBOARD_PID" >/dev/null 2>&1; then
  echo "No se pudo iniciar el servidor del dashboard."
  tail -n 40 "$DASHBOARD_LOG_FILE" || true
  exit 1
fi

echo "Dashboard listo"
echo "- API: http://localhost:$API_PORT"
echo "- UI : http://localhost:$DASHBOARD_PORT"
echo "Presiona Ctrl+C para detener dashboard y limpiar recursos iniciados por este script."

wait "$DASHBOARD_PID"
