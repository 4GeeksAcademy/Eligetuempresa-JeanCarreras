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

## Evidencia real del 16 de octubre de 2026

Tras configurar las credenciales privadas y crear la tabla, se ejecuto el backoffice intacto contra la API local conectada a Supabase remoto. Se verificaron **27 filas**: 26 eventos validos emitidos por el frontend y una medicion real de `/health` enviada en el lote manual. La recepcion de desarrollo registrada desde el formulario corresponde a `receipt_id=9`, `med-001`, `CHICKEN`, `0.1 kg`, moneda `COP`; no se presenta como una compra de produccion del restaurante.

- [Captura de filas consultadas en Supabase](evidence/telemetry/supabase-events.png): ocho filas visibles, incluidas negocio y tecnico, con `event_type`, `timestamp`, `service` y `tags`. Es una vista generada desde una consulta REST real, **no una captura de Supabase Studio**.
- [Captura del formulario tras registrar la recepcion](evidence/telemetry/backoffice-receipt.png).
- [Respuesta observada del lote mixto](evidence/telemetry/mixed-batch-response.json): `{"received": 3, "stored": 1, "rejected": 2}`. El reintento devolvio `{"received": 3, "stored": 0, "rejected": 3}`.
- [Filas leidas directamente de Supabase](evidence/telemetry/supabase-events.json) y [registro del recorrido](evidence/telemetry/verification.json). Se compararon tipo, instante y tags de cada evento valido observado en la red con su fila persistida.
- [Permisos observados](evidence/telemetry/permissions.json): PATCH y DELETE rechazados con HTTP 403 / PostgreSQL 42501, usando un UUID inexistente previamente comprobado. Ninguna fila fue actualizada o eliminada. OpenAPI anunciaba ambos metodos, por lo que no se uso su mera presencia como prueba de permisos efectivos.

Las pruebas unitarias con respuestas simuladas siguen siendo independientes de esta evidencia remota. Las claves y la URL privada del proyecto no se incluyen en los artefactos.

### Reproducir el E2E

Instala Playwright en el entorno de verificacion (`python -m pip install playwright` y `python -m playwright install --with-deps chromium`). Con la API en `http://localhost:8000` y la carpeta `uis/` servida en `http://localhost:4173`, ejecuta desde este servicio:

```bash
python scripts/verify_telemetry_e2e.py --allow-local-receipt
```

La opcion confirma que se creara **una recepcion adicional de 0.1 kg** en la base local de desarrollo y que sus eventos se guardaran en Supabase. El script solo admite una API local para estas escrituras. El resto de lecturas y capturas no requiere cambios al frontend. No ejecutes pruebas sobre datos operacionales de produccion.

### Limites y hallazgos preexistentes

- El plan vigente documenta `inventory_outbound_order_submitted` como capacidad futura: no hay flujo de orden de salida implementado. Esa parte del E2E sigue pendiente; no se invento una salida ni se modifico el frontend.
- `navigation_section_viewed` y `frontend_page_load_recorded` del frontend actual usan `client_platform=desktop`, pero el catalogo permite `web`, `mobile_web` o `desktop_app`. Esos eventos se rechazan correctamente por item y los demas del lote se guardan. El registro incluye estos rechazos; no se flexibilizo `TelemetryEvent` para ocultarlos.
- El formulario de acceso actual envia JSON a `/auth/login`, cuyo handler espera form-data. El intento real devuelve 422 y el productor emite `auth_login_failed` con `failure_code=network_error`. Ese es el hecho tecnico persistido, no un 401 ficticio ni un login exitoso.
- La captura adjunta muestra datos reales via REST. Si la evaluacion exige especificamente la interfaz de Supabase Studio, debe adjuntarse una captura desde la sesion autenticada del usuario en Table Editor. El verificador no tiene acceso a esa sesion.
- La existencia exacta de los tres indices se confirma ejecutando la consulta `pg_indexes` anterior en SQL Editor; PostgREST no expone ese catalogo del sistema.

## Descripcion del PR

Titulo: `feat: telemetry event storage`

- Sustituye el stub por validacion individual con `TelemetryEvent.model_validate` y bulk insert en Supabase.
- Anade migracion append-only e indices de timestamp, tipo y tags.
- Confirma expresamente: **el frontend no cambio ni una linea**; la URL y el contrato de envio permanecen iguales.
- Adjunta las capturas y el JSON observados enlazados arriba, identificando REST frente a Studio y los limites preexistentes sin presentarlos como requisitos completados.