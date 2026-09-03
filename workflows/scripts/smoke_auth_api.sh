#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
EMAIL="auth-smoke-$(date +%s)@example.com"
PASSWORD="smoke-password-123"

echo "== Smoke Auth API Brasaland =="

created_status=$(curl -sS -o /tmp/brasaland-auth-create.json -w "%{http_code}" \
  -X POST "$API_BASE/users" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"name\":\"Auth Smoke\",\"phone\":\"+57 3000000000\",\"address\":\"Medellin\"}")
test "$created_status" = "201"

token=$(curl -fsS -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=$EMAIL" \
  --data-urlencode "password=$PASSWORD" \
  | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
test -n "$token"

me_body=$(curl -fsS -H "Authorization: Bearer $token" "$API_BASE/auth/me")
grep -q "\"email\":\"$EMAIL\"" <<<"$me_body"

updated_body=$(curl -fsS -X PUT "$API_BASE/profiles/me" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $token" \
  -d '{"name":"Auth Smoke","phone":"+57 3010000000","address":"Bogota"}')
grep -q '"address":"Bogota"' <<<"$updated_body"

unauthorized_status=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/auth/me")
test "$unauthorized_status" = "401"

invalid_token_status=$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer invalid.token.value" "$API_BASE/auth/me")
test "$invalid_token_status" = "401"

echo "[smoke] PASS auth registration, login, profile and invalid-token rejection"