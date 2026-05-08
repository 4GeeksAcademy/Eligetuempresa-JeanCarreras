#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_DIR="$ROOT_DIR/workflows/output"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H-%M-%SZ")"
OUTPUT_FILE="$OUTPUT_DIR/weekly-report-$TIMESTAMP.md"

mkdir -p "$OUTPUT_DIR"

python3 "$ROOT_DIR/workflows/scripts/weekly_executive_report.py" \
  --api-base "${API_BASE:-http://localhost:8000}" \
  --currency "${CURRENCY:-USD}" \
  --output "$OUTPUT_FILE"

echo "Reporte generado en: $OUTPUT_FILE"

if [[ "${ENABLE_REPORT_DISPATCH:-0}" == "1" ]]; then
  python3 "$ROOT_DIR/workflows/scripts/send_weekly_report.py" \
    --report-path "$OUTPUT_FILE" \
    --title "Brasaland - Reporte Ejecutivo Semanal"
fi
