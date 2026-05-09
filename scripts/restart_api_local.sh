#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "Validando prerequisitos de entorno"
bash "$ROOT_DIR/scripts/check_env.sh"

# Try to stop current listener (idempotent if no process is running)
PORT="$PORT" bash "$ROOT_DIR/scripts/stop_api_local.sh"

# Start API again in foreground
HOST="$HOST" PORT="$PORT" exec bash "$ROOT_DIR/scripts/run_api_local.sh"
