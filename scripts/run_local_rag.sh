#!/usr/bin/env bash
set -euo pipefail
set +x

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$ROOT_DIR/services/brasaland-api"
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
if [[ -z "${GROQ_API_KEY:-}" ]]; then
  if [[ "${1:-}" == "--non-interactive" ]]; then
    echo "Falta GROQ_API_KEY. No se iniciaron servicios."
    exit 1
  fi
  read -r -s -p "Pega solo tu clave de Groq en este terminal (entrada oculta) y pulsa Enter: " GROQ_API_KEY
  printf '\n'
fi
if [[ -z "$GROQ_API_KEY" ]]; then
  echo "La clave de Groq esta vacia. No se iniciaron servicios."
  exit 1
fi
export GROQ_API_KEY

export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"
export DO_NOT_TRACK=1
if ! RAG_GENERATION_MODEL="$($PY_BIN - <<'PY'
import os
import sys
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
key = os.environ['GROQ_API_KEY'].strip()
if not key or any(character.isspace() for character in key) or key.startswith(('"', "'")) or key.endswith(('"', "'")):
  print('La clave tiene espacios internos o comillas. Pega solo el valor de la clave de Groq.', file=sys.stderr)
  sys.exit(1)
os.environ['GROQ_API_KEY'] = key
try:
  client = OpenAI(api_key=key, base_url='https://api.groq.com/openai/v1', timeout=30, max_retries=0)
  available = {model.id for model in client.models.list().data}
  chosen = os.environ.get('GROQ_GENERATION_MODEL', '').strip()
  if chosen and chosen not in available:
    print('GROQ_GENERATION_MODEL no esta disponible en esta cuenta. Retira esa variable para seleccion automatica.', file=sys.stderr)
    sys.exit(1)
  if not chosen:
    chosen = next((name for name in ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'openai/gpt-oss-20b'] if name in available), '')
  if not chosen:
    print('No hay un modelo de chat preferido habilitado. Selecciona GROQ_GENERATION_MODEL desde la consola de Groq.', file=sys.stderr)
    sys.exit(1)
  print(chosen)
except APITimeoutError:
  print('Groq no respondio en 30 segundos. Revisa la conexion y vuelve a intentar.', file=sys.stderr)
  sys.exit(1)
except APIConnectionError as error:
  cause = type(error.__cause__).__name__ if error.__cause__ else 'desconocida'
  print(f'No se pudo conectar con Groq (causa: {cause}). Revisa red, proxy y certificados; no implica una clave invalida.', file=sys.stderr)
  sys.exit(1)
except APIStatusError as error:
  explanations = {
    401: 'Groq rechazo la autenticacion. Usa una clave activa creada en console.groq.com, no la clave de Supabase.',
    403: 'Groq denego el acceso. Revisa permisos del proyecto y restricciones de cuenta o red.',
    429: 'Groq aplico un limite de solicitudes o cuota. Revisa los limites de la cuenta.',
  }
  print(f'HTTP {error.status_code}: {explanations.get(error.status_code, "Groq devolvio un error. Revisa el estado del servicio.")}', file=sys.stderr)
  sys.exit(1)
except Exception as error:
  print(f'Fallo al comprobar Groq ({type(error).__name__}). No se iniciaron servicios.', file=sys.stderr)
  sys.exit(1)
PY
)"; then
  exit 1
fi
export RAG_GENERATION_MODEL
GROQ_API_KEY="${GROQ_API_KEY#"${GROQ_API_KEY%%[![:space:]]*}"}"
GROQ_API_KEY="${GROQ_API_KEY%"${GROQ_API_KEY##*[![:space:]]}"}"
export GROQ_API_KEY
export GROQ_GENERATION_MODEL="$RAG_GENERATION_MODEL"

docker info >/dev/null
RUNTIME_DIR="$(mktemp -d /tmp/brasaland-rag.XXXXXX)"
PROJECT="brasaland-rag-$(date +%s)-$$"
export QDRANT_API_KEY="$($PY_BIN -c 'import secrets; print(secrets.token_hex(32))')"
export RAG_QDRANT_API_KEY="$QDRANT_API_KEY"
export BRASALAND_LOCAL_LLM_KEY="$($PY_BIN -c 'import secrets; print(secrets.token_hex(32))')"
export LLM_API_KEY="$BRASALAND_LOCAL_LLM_KEY"
export RAG_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
export BRASALAND_EMBED_CACHE="${BRASALAND_EMBED_CACHE:-/tmp/brasaland-embeddings}"
export LOCAL_LLM_PORT="${LOCAL_LLM_PORT:-8011}"
export LLM_API_BASE_URL="http://127.0.0.1:$LOCAL_LLM_PORT/v1"
export OPENAI_BASE_URL="$LLM_API_BASE_URL"
export OPENAI_API_KEY="$LLM_API_KEY"
export RAG_QDRANT_URL=http://127.0.0.1:6333

if lsof -nP -iTCP:6333 -sTCP:LISTEN >/dev/null 2>&1 || lsof -nP -iTCP:"$LOCAL_LLM_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Un puerto requerido esta ocupado. No se modificaron servicios existentes."
  exit 1
fi

LOCAL_PID=""
cleanup() {
  if [[ -n "$LOCAL_PID" ]] && kill -0 "$LOCAL_PID" >/dev/null 2>&1; then
    kill "$LOCAL_PID" >/dev/null 2>&1 || true
  fi
  docker compose -f "$ROOT_DIR/docker-compose.yml" -p "$PROJECT" down >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo "Modelo Groq verificado: $RAG_GENERATION_MODEL"
docker compose -f "$ROOT_DIR/docker-compose.yml" -p "$PROJECT" up -d qdrant
if ! curl -fsS --retry 20 --retry-connrefused --retry-delay 1 "$RAG_QDRANT_URL/readyz" >/dev/null 2>&1; then
  echo "Qdrant no estuvo listo dentro del plazo de arranque."
  exit 1
fi
bash "$ROOT_DIR/scripts/run_local_llm.sh" >"$RUNTIME_DIR/local-llm.log" 2>&1 &
LOCAL_PID="$!"
if ! curl -fsS --retry 20 --retry-connrefused --retry-delay 1 "http://127.0.0.1:$LOCAL_LLM_PORT/health" >/dev/null 2>&1; then
  echo "El servicio local no arranco. Revisa $RUNTIME_DIR/local-llm.log."
  exit 1
fi

"$PY_BIN" - <<'PY'
import json
import os
import sys
from qdrant_client import QdrantClient
client = QdrantClient(url=os.environ['RAG_QDRANT_URL'], api_key=os.environ['RAG_QDRANT_API_KEY'])
if client.get_collections().collections:
    print('La instancia no esta vacia. No se reindexo ninguna coleccion.', file=sys.stderr)
    sys.exit(1)
try:
    from data.process.rag_index import setup
    setup()
    collection = client.get_collection('brasaland_knowledge')
    if collection.points_count == 0 or collection.config.params.vectors.size != 384:
        raise ValueError('Unexpected collection')
    print(json.dumps({'collection': 'brasaland_knowledge', 'points': collection.points_count, 'dimensions': 384}))
    from data.pipelines.rag import query
    answer = query('Que advertencia debo comunicar sobre contaminacion cruzada por alergenos?')
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError('Empty answer')
    print('Consulta real RAG completada. No se afirma Recall@3 ni calidad de respuesta evaluada.')
except Exception as error:
    print(f'No se completo la indexacion o consulta RAG ({type(error).__name__}).', file=sys.stderr)
    sys.exit(1)
PY

"$PY_BIN" - "$RUNTIME_DIR" <<'PY'
import json
import os
import sys
from pathlib import Path
names = ['GROQ_API_KEY', 'GROQ_GENERATION_MODEL', 'RAG_GENERATION_MODEL', 'RAG_EMBEDDING_MODEL', 'BRASALAND_LOCAL_LLM_KEY', 'LLM_API_KEY', 'LLM_API_BASE_URL', 'OPENAI_BASE_URL', 'OPENAI_API_KEY', 'RAG_QDRANT_URL', 'RAG_QDRANT_API_KEY', 'QDRANT_API_KEY']
target = Path(sys.argv[1]) / 'environment.json'
descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, 'w') as stream:
    json.dump({name: os.environ[name] for name in names}, stream)
PY
echo "RAG de desarrollo activo. Configuracion privada conservada en $RUNTIME_DIR/environment.json."
echo "Ctrl+C detiene los servicios nuevos; no elimina el volumen de desarrollo."
wait "$LOCAL_PID"