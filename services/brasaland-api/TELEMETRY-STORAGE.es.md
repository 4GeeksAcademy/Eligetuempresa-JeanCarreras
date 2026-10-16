# Almacenamiento de telemetria

## Despliegue

1. En el SQL Editor del proyecto Supabase ejecuta [migrations/001_telemetry_events.sql](migrations/001_telemetry_events.sql). Ejecutala una sola vez; no elimina ni sustituye tablas existentes.
2. Configura en el entorno privado del backend `SUPABASE_URL=https://<proyecto>.supabase.co` y `SUPABASE_SERVICE_ROLE_KEY`. No uses la clave anonima. No publiques secretos en Git, capturas, frontend ni PR.
3. Instala `requirements.txt` y ejecuta desde la raiz `bash scripts/run_api_local.sh`. La ruta sigue siendo `POST /telemetry/events`. El frontend y `NEXT_PUBLIC_TELEMETRY_ENDPOINT` permanecen intactos.

La clave primaria `event_id` deduplica reintentos. Los tres indices analiticos son B-tree en `timestamp` y `event_type`, y GIN en `tags`. RLS esta habilitado, sin politicas para clientes; solo `service_role` tiene INSERT/SELECT. No hay rutas ni permisos UPDATE/DELETE/TRUNCATE para los roles de aplicacion. El propietario administrativo de la base sigue pudiendo administrar la tabla.

## Mapeo

| Envelope | Columna |
| --- | --- |
| `eventId` | `event_id` UUID |
| `timestamp` | `timestamp` TIMESTAMPTZ, instante original |
| `event_type` | `event_type` TEXT |
| `sessionId`, `userId` | `session_id`, `user_id`, admiten NULL |
| `schemaVersion`, `requestId` | `schema_version`, `request_id` |
| `properties` | `tags` JSONB, objeto validado completo |
| Servicio receptor | `service`, `TELEMETRY_SERVICE` o `brasaland-api` |
| Hora de almacenamiento | `received_at`, reloj de la base |

El envelope no contiene `service`: esta columna identifica al receptor, no pretende inferir el productor. Las dimensiones `store_id`, `country`, `timezone`, `currency`, `sku` y las demas claves se conservan en `tags` cuando el evento las permite. No se anaden propiedades fuera de las allowlists. `TelemetryEvent` y el catalogo no cambian.

## Prueba manual de aceptacion parcial

Con la tabla y la API configuradas, envia este lote sintetico (no acredita movimientos reales). Usa un UUID nuevo si repites la prueba:

```bash
curl --fail-with-body http://localhost:8000/telemetry/events \
  -H 'Content-Type: application/json' \
  --data '{"events":[{"eventId":"3cb9d6df-5e60-4d65-b214-7488e48b2410","timestamp":"2026-10-16T12:00:00Z","sessionId":null,"userId":null,"event_type":"auth_login_failed","schemaVersion":"1.0.0","requestId":"manual-verification","properties":{"failure_code":"invalid_credentials","auth_method":"password","source_class":"web"}},{"event_type":"unknown_event"},null]}'
```

Resultado esperado en la primera ejecucion, no evidencia de una ejecucion remota:

```json
{"received": 3, "stored": 1, "rejected": 2}
```

En un reintento del mismo lote, `stored` es 0 y `rejected` es 3: un duplicado es una entrada no insertada, no un UPDATE. El bulk usa un unico POST a PostgREST con `ON CONFLICT DO NOTHING` y retorna solo los IDs insertados para contar filas reales. Si Supabase falla o no esta configurado, responde 503, nunca un exito simulado. Los detalles de errores y payloads rechazados no se registran.

## Verificacion directa en Supabase

```sql
SELECT event_id, event_type, timestamp, service, tags
FROM public.telemetry_events
ORDER BY received_at DESC
LIMIT 20;

SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'telemetry_events';

SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public' AND table_name = 'telemetry_events'
ORDER BY grantee, privilege_type;
```

Comprueba que los eventos de negocio preservan sus IDs operacionales, local, pais, SKU y cantidades, y que los tecnicos respetan sus allowlists sin credenciales ni PII. `timestamp` es el instante del evento, no `received_at`.

## Evidencia y limites de esta entrega

Las pruebas automatizadas usan respuestas HTTP simuladas de Supabase y verifican aceptacion parcial, una unica insercion por lote, mapeo de entradas/salidas/login fallido, duplicados y fallos de almacenamiento. No prueban que una tabla remota exista.

No hay credenciales Supabase disponibles en el entorno de implementacion: queda pendiente ejecutar la migracion, verificar persistencia real y adjuntar una captura con al menos cinco filas reales (incluido evento tecnico y de negocio). No se deben presentar los datos de pruebas como movimientos reales.

El plan vigente documenta `inventory_outbound_order_submitted` como capacidad futura: no hay flujo de orden de salida implementado. Completar esa parte del E2E exige dicho flujo, fuera de este cambio de ingesta; no se modifica el frontend ni se inventa una salida. Registra entradas reales y un fallo de login en el backoffice disponible, comprueba su envio en Network y consulta la tabla. Si faltan productores, documenta la falta de cobertura sin equipararla a cero actividad.

## Descripcion del PR

Titulo: `feat: telemetry event storage`

- Sustituye el stub por validacion individual con `TelemetryEvent.model_validate` y bulk insert en Supabase.
- Anade migracion append-only e indices de timestamp, tipo y tags.
- Confirma expresamente: **el frontend no cambio ni una linea**; la URL y el contrato de envio permanecen iguales.
- Adjunta el JSON observado de un lote mixto y la captura de al menos cinco eventos reales. Pendientes hasta verificar el entorno Supabase; no usar el resultado esperado anterior como evidencia observada.