#!/usr/bin/env bash
set -euo pipefail

APP_BASE_URL="${APP_BASE_URL:-http://localhost:3000}"
API_BASE_URL="${API_BASE_URL:-https://playground.4geeks.com/tracker/api/v1}"
TMP_PREFIX="smoke-tpt-$(date +%s)"
TMP_CANDIDATE_ID=""

parse_json_field() {
  local field="$1"
  python -c "import json,sys; data=json.load(sys.stdin); print(data.get('${field}',''))"
}

cleanup() {
  if [[ -n "${TMP_CANDIDATE_ID}" ]]; then
    curl -sS -X DELETE "${API_BASE_URL}/records/${TMP_CANDIDATE_ID}" >/dev/null || true
  fi
}

trap cleanup EXIT

echo "[smoke] App base: ${APP_BASE_URL}"
echo "[smoke] API base: ${API_BASE_URL}"

status_root=$(curl -s -o /tmp/tpt_smoke_root.html -w "%{http_code}" "${APP_BASE_URL}/")
if [[ "${status_root}" != "200" ]]; then
  echo "[smoke] FAIL / status=${status_root}"
  exit 1
fi

echo "[smoke] OK /"

candidate_id=$(curl -sS "${API_BASE_URL}/records?page=1&limit=1" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p' | head -n1)
if [[ -z "${candidate_id}" ]]; then
  echo "[smoke] FAIL no candidate id from API"
  exit 1
fi

status_detail=$(curl -s -o /tmp/tpt_smoke_detail.html -w "%{http_code}" "${APP_BASE_URL}/candidates/${candidate_id}")
if [[ "${status_detail}" != "200" ]]; then
  echo "[smoke] FAIL /candidates/${candidate_id} status=${status_detail}"
  exit 1
fi

echo "[smoke] OK /candidates/${candidate_id}"

create_payload=$(cat <<JSON
{
  "full_name": "${TMP_PREFIX} Candidate",
  "email": "${TMP_PREFIX}@example.com",
  "phone": "+57 3000000000",
  "position": "QA Analyst",
  "linkedin_url": null,
  "cv_url": null,
  "experience_years": 2
}
JSON
)

create_response=$(curl -sS -X POST "${API_BASE_URL}/records" -H "Content-Type: application/json" -d "${create_payload}")
TMP_CANDIDATE_ID=$(printf "%s" "${create_response}" | parse_json_field "id")
if [[ -z "${TMP_CANDIDATE_ID}" ]]; then
  echo "[smoke] FAIL create record did not return id"
  exit 1
fi

echo "[smoke] OK create /records id=${TMP_CANDIDATE_ID}"

patch_payload='{"status":"in_progress","stage":"review"}'
patch_status=$(curl -s -o /tmp/tpt_smoke_patch.json -w "%{http_code}" -X PATCH "${API_BASE_URL}/records/${TMP_CANDIDATE_ID}" -H "Content-Type: application/json" -d "${patch_payload}")
if [[ "${patch_status}" != "200" ]]; then
  echo "[smoke] FAIL patch record status=${patch_status}"
  exit 1
fi

echo "[smoke] OK patch /records/:id"

put_payload=$(cat <<JSON
{
  "full_name": "${TMP_PREFIX} Candidate Updated",
  "email": "${TMP_PREFIX}@example.com",
  "phone": "+57 3111111111",
  "position": "QA Analyst Senior",
  "linkedin_url": null,
  "cv_url": null,
  "experience_years": 3
}
JSON
)

put_status=$(curl -s -o /tmp/tpt_smoke_put.json -w "%{http_code}" -X PUT "${API_BASE_URL}/records/${TMP_CANDIDATE_ID}" -H "Content-Type: application/json" -d "${put_payload}")
if [[ "${put_status}" != "200" ]]; then
  echo "[smoke] FAIL put record status=${put_status}"
  exit 1
fi

echo "[smoke] OK put /records/:id"

note_payload='{"content":"Smoke note"}'
note_response=$(curl -sS -X POST "${API_BASE_URL}/records/${TMP_CANDIDATE_ID}/notes" -H "Content-Type: application/json" -d "${note_payload}")
note_id=$(printf "%s" "${note_response}" | parse_json_field "id")
if [[ -z "${note_id}" ]]; then
  echo "[smoke] FAIL create note did not return id"
  exit 1
fi

echo "[smoke] OK post /records/:id/notes note=${note_id}"

notes_status=$(curl -s -o /tmp/tpt_smoke_notes.json -w "%{http_code}" "${API_BASE_URL}/records/${TMP_CANDIDATE_ID}/notes")
if [[ "${notes_status}" != "200" ]]; then
  echo "[smoke] FAIL get notes status=${notes_status}"
  exit 1
fi

echo "[smoke] OK get /records/:id/notes"

delete_note_status=$(curl -s -o /tmp/tpt_smoke_delete_note.txt -w "%{http_code}" -X DELETE "${API_BASE_URL}/records/${TMP_CANDIDATE_ID}/notes/${note_id}")
if [[ "${delete_note_status}" != "204" ]]; then
  echo "[smoke] FAIL delete note status=${delete_note_status}"
  exit 1
fi

echo "[smoke] OK delete /records/:id/notes/:note_id"

delete_record_status=$(curl -s -o /tmp/tpt_smoke_delete_record.txt -w "%{http_code}" -X DELETE "${API_BASE_URL}/records/${TMP_CANDIDATE_ID}")
if [[ "${delete_record_status}" != "204" ]]; then
  echo "[smoke] FAIL delete record status=${delete_record_status}"
  exit 1
fi

TMP_CANDIDATE_ID=""
echo "[smoke] OK delete /records/:id"
echo "[smoke] PASS"
