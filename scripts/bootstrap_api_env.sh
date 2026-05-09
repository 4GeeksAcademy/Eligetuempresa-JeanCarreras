#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$ROOT_DIR/services/brasaland-api"
VENV_DIR="${VENV_DIR:-$SERVICE_DIR/.venv}"
REQ_FILE="$SERVICE_DIR/requirements.txt"

if [[ ! -d "$SERVICE_DIR" ]]; then
  echo "No se encontro el servicio en: $SERVICE_DIR"
  exit 1
fi

if [[ ! -f "$REQ_FILE" ]]; then
  echo "No se encontro requirements.txt en: $REQ_FILE"
  exit 1
fi

SYS_PY=""
if command -v python3 >/dev/null 2>&1; then
  SYS_PY="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  SYS_PY="$(command -v python)"
else
  echo "No se encontro Python del sistema (python3/python)."
  exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Creando entorno virtual en: $VENV_DIR"
  "$SYS_PY" -m venv "$VENV_DIR"
else
  echo "Entorno virtual existente: $VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"

echo "Instalando/actualizando dependencias desde: $REQ_FILE"
"$VENV_PY" -m pip install -r "$REQ_FILE"

echo "Bootstrap completado. Puedes iniciar la API con:"
echo "  bash scripts/run_api_local.sh"
