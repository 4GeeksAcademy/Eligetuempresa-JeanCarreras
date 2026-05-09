#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8000}"
API_WAS_RUNNING=0

if lsof -t -i TCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
	API_WAS_RUNNING=1
fi

cleanup() {
	if [[ "$API_WAS_RUNNING" -eq 0 ]]; then
		PORT="$PORT" bash "$ROOT_DIR/scripts/stop_api_local.sh" >/dev/null 2>&1 || true
	fi
}

trap cleanup EXIT

echo "== Brasaland local QA =="
echo "1/3 smoke"
bash "$ROOT_DIR/workflows/scripts/smoke_api.sh"

echo "2/3 integration"
bash "$ROOT_DIR/workflows/scripts/integration_api.sh"

echo "3/3 integration-data"
bash "$ROOT_DIR/workflows/scripts/integration_data_api.sh"

echo "QA local completado correctamente"
