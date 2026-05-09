#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$ROOT_DIR/services/brasaland-api"

REQUIRED_CMDS=(bash curl lsof)
MISSING_CMDS=()

for cmd in "${REQUIRED_CMDS[@]}"; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    MISSING_CMDS+=("$cmd")
  fi
done

if [[ ${#MISSING_CMDS[@]} -gt 0 ]]; then
  echo "Faltan comandos requeridos: ${MISSING_CMDS[*]}"
  echo "Instalalos para poder ejecutar scripts locales correctamente."
  exit 1
fi

PY_BIN=""
if [[ -x "$SERVICE_DIR/.venv/bin/python" ]]; then
  PY_BIN="$SERVICE_DIR/.venv/bin/python"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PY_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY_BIN="$(command -v python3)"
else
  echo "No se encontro Python (ni en venv ni python3 del sistema)."
  exit 1
fi

echo "Python detectado: $PY_BIN"

if ! "$PY_BIN" - <<'PY'
import importlib.util
import sys

required = ["fastapi", "uvicorn", "pydantic"]
missing = [name for name in required if importlib.util.find_spec(name) is None]

if missing:
    print("Faltan paquetes Python requeridos:", ", ".join(missing))
    sys.exit(1)

print("Dependencias Python OK: fastapi, uvicorn, pydantic")
PY
then
  echo "Tip: instala dependencias con:"
  echo "  cd services/brasaland-api && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

echo "Entorno local OK para run/restart/qa/dev_cycle"
