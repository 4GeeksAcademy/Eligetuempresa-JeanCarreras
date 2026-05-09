#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

REQUIRED_CMDS=(bash git)
MISSING_CMDS=()

for cmd in "${REQUIRED_CMDS[@]}"; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    MISSING_CMDS+=("$cmd")
  fi
done

if [[ ${#MISSING_CMDS[@]} -gt 0 ]]; then
  echo "Faltan comandos requeridos para bootstrap global: ${MISSING_CMDS[*]}"
  exit 1
fi

echo "== Bootstrap local del repositorio =="

echo "1/3 Preparando entorno de API Brasaland"
bash "$ROOT_DIR/scripts/bootstrap_api_env.sh"

echo "2/3 Verificando prerequisitos operativos"
bash "$ROOT_DIR/scripts/check_env.sh"

echo "3/3 Validando scripts clave"
for script in run_api_local.sh restart_api_local.sh run_qa_local.sh dev_cycle.sh; do
  if [[ ! -x "$ROOT_DIR/scripts/$script" ]]; then
    echo "Script no ejecutable: scripts/$script"
    exit 1
  fi
done

echo "Bootstrap global completado. Siguiente paso sugerido:"
echo "  bash scripts/run_api_local.sh"
