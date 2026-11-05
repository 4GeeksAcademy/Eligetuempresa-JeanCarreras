# RFP Response Generation (Parte 2)

Generación y evaluación de respuestas a RFP — ciclo generador-evaluador por departamento.

## Flujo

```
analisis_completo → generando_borrador → en_evaluacion → (needs_human_review)
```

1. **Consumir handoff de la Parte 1**: cada ticket en `analisis_completo` tiene un
   handoff con `sales_handoff` y `workstreams` (por departamento).
2. **Generar borrador por departamento**: un agente generador específico redacta la
   sección de propuesta económica.
3. **Evaluar en paralelo**: tres evaluadores (legibilidad, pertinencia, cumplimiento)
   corren simultáneamente sobre cada borrador.
4. **Ciclo generador-evaluador**: si la evaluación falla, el borrador vuelve al
   generador con feedback concreto (hasta `MAX_ITERATIONS=3` intentos).
5. **Handoff a la Parte 3**: se persiste el resultado (borrador final + EvaluationResult
   estructurado). Las secciones que agotaron iteraciones van con `needs_human_review`.

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/rfp-intake/tickets/{id}/generate-response` | Dispara generación (estado `analisis_completo` → `generando_borrador`) |
| GET | `/rfp-intake/tickets/{id}/response` | Obtiene drafts + evaluaciones + handoff |

## Estructura de datos

### EvaluationResult (YAML)
```yaml
section_id: "Operaciones de Restaurante"
department_id: "Operaciones de Restaurante"
readability:
  pass: true
  score: 9.2
  details: "Flesch-Kincaid Grade Level: 9.2. Aceptable."
relevance:
  pass: true
  missing_aspects: []
  details: "El borrador cubre los aspectos clave."
compliance:
  pass: true
  rule_ids: []
  violations: []
  details: "Cumple todas las reglas."
overall_pass: true
feedback_for_generator: ""
```

### DepartmentDraft
```yaml
department: "Operaciones de Restaurante"
iteration: 2
content: "## Alcance del servicio..."
evaluation: (EvaluationResult)
needs_human_review: false  # true si agotó iteraciones sin pasar
```

## Reglas de cumplimiento (del company-BRIEFING)

Ver `data/pipelines/rfp_response/__init__.py` → `COMPLIANCE_RULES`.
Cubren: tono, moneda explícita, plazos de entrega, alérgenos, programa
Brasa Points, alcance geográfico, descuentos, formato de sección y
limitaciones tecnológicas.

## Persistencia

Tablas en Supabase (migración `003_rfp_response_generation.sql`):
- `rfp_response_drafts`: borradores por departamento/iteración
- `rfp_evaluation_results`: resultados de evaluación estructurados
- `rfp_response_handoff`: handoff consolidado para la Parte 3

## Pruebas

```bash
# Unit tests del pipeline
uv run --project services/brasaland-api python -m pytest tests/pipelines/test_rfp_response.py -v

# API tests
uv run --project services/brasaland-api python -m pytest services/brasaland-api/tests/test_rfp_response_api.py -v
```