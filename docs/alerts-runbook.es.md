# Runbook operativo de alertas de inactividad (Brasaland)

## Objetivo

Estandarizar la respuesta operativa ante alertas de inactividad por local para reducir tiempo de atencion y evitar perdida de ventas.

## Alcance

- Mercados: Colombia y Florida.
- Roles: operaciones (ejecucion), ejecutiva (visibilidad), admin (gobernanza).
- Estado de alerta soportado por API: `new`, `acknowledged`, `resolved`.

## Definiciones

- `warning`: inactividad mayor al umbral configurado.
- `critical`: inactividad mayor a 2x el umbral.
- SLA objetivo de resolucion: 30 minutos desde `acknowledged` a `resolved`.

## Flujo operativo

1. Detectar:
- Revisar `GET /api/v1/alerts/inactivity` y priorizar `critical`.

2. Acknowledge:
- Registrar responsable y nota inicial con:
- `POST /api/v1/alerts/inactivity/actions` (`status=acknowledged`).

3. Diagnosticar:
- Verificar POS, conectividad, staffing, flujo en caja y apertura de turnos.

4. Resolver:
- Cuando el local retome operacion, registrar:
- `POST /api/v1/alerts/inactivity/actions` (`status=resolved`) con nota de causa/accion.

5. Revisar cumplimiento:
- Consultar `GET /api/v1/alerts/inactivity/sla` para seguimiento de SLA.

## Tiempos objetivo

- `critical`: acknowledge en <= 5 minutos.
- `warning`: acknowledge en <= 15 minutos.
- `critical`/`warning`: resolucion en <= 30 minutos desde acknowledge.

## Ejemplos cURL

```bash
curl -sS -X POST "http://localhost:8000/api/v1/alerts/inactivity/actions" \
  -H "Content-Type: application/json" \
  -H "X-API-Role: operations" \
  -H "X-API-Token: brasaland-operations-token" \
  -d '{
    "store_id":"med-001",
    "status":"acknowledged",
    "owner":"ops-on-duty",
    "note":"Investigando POS y conectividad"
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
    "note":"Caja restablecida y ventas normalizadas"
  }'
```

## Escalacion

1. Si `critical` supera 15 minutos sin acknowledge:
- Escalar a supervisor regional.

2. Si `critical` supera 30 minutos sin resolucion:
- Escalar a gerencia de operaciones y soporte tecnico.

## Criterios de cierre diario

- Todas las alertas `critical` del dia en `resolved` o con plan de accion documentado.
- Reporte de SLA diario revisado por operaciones.
