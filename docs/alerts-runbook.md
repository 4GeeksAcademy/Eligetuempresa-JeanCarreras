# Inactivity Alerts Operations Runbook (Brasaland)

## Objective

Standardize operational response to store inactivity alerts to reduce response time and prevent revenue loss.

## Scope

- Markets: Colombia and Florida.
- Roles: operations (execution), executive (visibility), admin (governance).
- Alert states supported by API: `new`, `acknowledged`, `resolved`.

## Definitions

- `warning`: inactivity above configured threshold.
- `critical`: inactivity above 2x threshold.
- Resolution SLA target: 30 minutes from `acknowledged` to `resolved`.

## Operational flow

1. Detect:
- Review `GET /api/v1/alerts/inactivity` and prioritize `critical`.

2. Acknowledge:
- Register owner and initial note with:
- `POST /api/v1/alerts/inactivity/actions` (`status=acknowledged`).

3. Diagnose:
- Check POS, connectivity, staffing, checkout flow, and shift readiness.

4. Resolve:
- Once operations normalize, register:
- `POST /api/v1/alerts/inactivity/actions` (`status=resolved`) with root cause/action note.

5. Track compliance:
- Use `GET /api/v1/alerts/inactivity/sla` for SLA follow-up.

## Target times

- `critical`: acknowledge in <= 5 minutes.
- `warning`: acknowledge in <= 15 minutes.
- `critical`/`warning`: resolve in <= 30 minutes from acknowledge.

## cURL examples

```bash
curl -sS -X POST "http://localhost:8000/api/v1/alerts/inactivity/actions" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{
    "store_id":"med-001",
    "status":"acknowledged",
    "owner":"ops-on-duty",
    "note":"Investigating POS and connectivity"
  }'
```

```bash
curl -sS -X POST "http://localhost:8000/api/v1/alerts/inactivity/actions" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{
    "store_id":"med-001",
    "status":"resolved",
    "owner":"ops-on-duty",
    "note":"Checkout restored and sales normalized"
  }'
```

## Escalation

1. If a `critical` alert exceeds 15 minutes without acknowledge:
- Escalate to regional supervisor.

2. If a `critical` alert exceeds 30 minutes without resolution:
- Escalate to operations management and technical support.

## Daily closure criteria

- All daily `critical` alerts are `resolved` or have a documented action plan.
- Daily SLA report reviewed by operations.
