#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$ROOT_DIR/services/brasaland-api"
PORT="${LOCAL_LLM_PORT:-8010}"
PY_BIN=""

for candidate in "$SERVICE_DIR/.venv/bin/python" "$SERVICE_DIR/.venv312/bin/python" "$ROOT_DIR/.venv/bin/python"; do
  if [[ -x "$candidate" ]]; then
    PY_BIN="$candidate"
    break
  fi
done

if [[ -z "$PY_BIN" ]]; then
  echo "Prepara el entorno con bash scripts/bootstrap_api_env.sh."
  exit 1
fi
LOCAL_KEY="${BRASALAND_LOCAL_LLM_KEY:-}"
if [[ ${#LOCAL_KEY} -lt 32 ]]; then
  echo "Configura BRASALAND_LOCAL_LLM_KEY con una clave privada de al menos 32 caracteres."
  exit 1
fi

"$PY_BIN" -c "import fastembed, uvicorn"
echo "Servicio local en http://127.0.0.1:$PORT/v1 (CPU, embeddings de 384 dimensiones)"
echo "Groq requiere GROQ_API_KEY; las claves no se muestran."
cd "$SERVICE_DIR"
exec "$PY_BIN" -m uvicorn src.brasaland_api.local_llm:app --host 127.0.0.1 --port "$PORT"