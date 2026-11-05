# Intake de RFP

El API central expone `POST /rfp-intake/tickets`, `GET /rfp-intake/tickets` y
`GET /rfp-intake/tickets/{ticket_id}`. Las rutas requieren un JWT de usuario;
el PDF se limita a 25 MB y se guarda en `data/raw/rfp/`. El POST crea primero el
ticket `analizando`, responde `202` y entrega el pipeline al `BackgroundTasks`
del mismo proceso FastAPI.

Aplicar `migrations/002_rfp_intake.sql` en Supabase y configurar
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y `OPENAI_API_KEY`. El pipeline
dedicado está bajo `data/pipelines/rfp_intake/`; convierte a Markdown con
MarkItDown antes de que el clasificador o los workers lean el documento. Solo
rechaza documentos claramente ajenos con confianza alta. Los departamentos y
contactos se limitan al catálogo de Brasaland en el grafo.

## Persistencia y handoff

- `rfp_tickets` conserva estado, ruta del original, `processing_error` y el
  handoff final.
- `rfp_documents` conserva ruta Markdown, metadatos, clasificación y métricas
  de legibilidad.
- `rfp_department_sections` conserva responsable, extracto y `key_aspects`.
- El handoff tiene `ticket_id`, `sales_handoff` y `workstreams`; Parte 2 puede
  continuar sin reparsear el PDF.

Si una tarea falla, el ticket sigue `analizando` y publica `processing_error`;
no se confunde un error técnico con un rechazo de negocio. El trabajo está
ejecutado en memoria por `BackgroundTasks`, no en una cola durable: tras una
caída abrupta puede quedar `analizando` sin `processing_error`. Tras confirmar
que el worker ya no está activo, un operador puede reprocesarlo con:

```bash
uv run --project services/brasaland-api --no-sync python scripts/reprocess_rfp_ticket.py <ticket_id> --confirm-stale
```

No usar `--confirm-stale` mientras el API siga procesando ese ticket para evitar
workers duplicados. Los tickets con `processing_error` sí pueden reprocesarse
sin esa confirmación.

El briefing versionado disponible no contiene PDFs de RFP de ejemplo ni un
formato comercial específico. El flujo usa el contexto de Brasaland para el
catálogo y aplica clasificación conservadora; la validación con solicitudes
formales, informales e inválidas requiere que Ventas aporte los ejemplos.