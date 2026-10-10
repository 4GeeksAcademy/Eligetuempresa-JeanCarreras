# Plan de telemetría Brasaland

**Estado:** diseño previo a instrumentación  
**Versión del contrato:** `1.0.0`  
**Alcance:** API y backoffice actuales, con contratos explícitos para capacidades de inventario aún no implementadas.

## Base y alcance

El archivo disponible en este monorepo es `CONTEXT.md` (no existe `CONTEXT-empresa.md`). Su sección “KPI iniciales sugeridos” no etiqueta métricas como obligatorias. Para no atribuirle requisitos que no contiene, este plan conserva como **baseline CONTEXT** todos esos KPI y los distingue de las preguntas expresas del RFI, clasificadas como **obligatorias RFI**. La suma de ambos grupos constituye el piso de diseño; las **oportunidades** son propuestas adicionales.

El backend observado usa `store_id`, `country` (`CO`/`US`), `timezone`, `sku`, `current_stock`, `min_stock`, órdenes de entrada (`inventory_receipts`), ventas, proveedores, clientes, formación y RR. HH. Tiene login por email/contraseña y auditoría por rol. En cambio, no se encontró una orden de salida de inventario ni una ruta de edición directa de stock; los dos eventos correspondientes se definen como contratos futuros. La ausencia de evento no se interpretará como cero actividad hasta que la cobertura y salud del productor estén confirmadas.

## Requisitos y catálogo

El inventario conserva la regla innegociable: el stock solo cambia mediante movimientos trazables a un actor autenticado. Los eventos de rechazo de edición directa no deben habilitar ni implementar tal edición. El evento de salida describe una orden aprobada/registrada, no una mutación directa del stock.

| # | `event_type` | Grupo | Hipótesis y decisión habilitada | Entrega |
|---:|---|---|---|---|
| 1 | `sales_event_recorded` | Baseline CONTEXT | El volumen y valor de ventas varía por local, país y moneda; ajustar operación y comparar mercados con importes en moneda original. | Batch; reportes agregados por día/semana, sin urgencia de segundos. |
| 2 | `finance_kpi_snapshot_recorded` | Baseline CONTEXT | Ticket promedio y margen estimado varían por mercado; priorizar revisión comercial/financiera. | Batch diario; el cálculo consolidado no requiere alerta inmediata. |
| 3 | `inventory_outbound_order_submitted` | Obligatorio RFI | El número y cantidad de salidas cambia por local/SKU; ajustar reposición y revisar patrones de consumo. | Stream; operaciones necesita ver movimientos recientes y actualizar riesgo de quiebre. |
| 4 | `inventory_receipt_created` | Oportunidad | Una recepción reduce una recomendación abierta; confirmar reposición y conciliar costo/cantidad. | Stream; confirmar existencias en el flujo operativo. |
| 5 | `inventory_validation_failed` | Obligatorio RFI | Los errores se concentran en ciertos SKU/reglas; corregir catálogo, interfaz o capacitación. | Batch cada 15 min; la tendencia importa más que la alerta individual. |
| 6 | `inventory_direct_stock_edit_rejected` | Obligatorio RFI | Se intentan saltar movimientos trazables; investigar permisos, UX o abuso y preservar auditoría. | Stream; detectar inmediatamente intentos de elusión. |
| 7 | `inventory_stock_threshold_triggered` | Obligatorio RFI | El stock cruza el mínimo en ciertos locales/SKU; priorizar reposición antes del quiebre. | Stream; requiere acción durante el turno. Solo transición hacia abajo, no cada lectura. |
| 8 | `inventory_stockout_detected` | Baseline CONTEXT | Los quiebres se concentran por categoría/local; reasignar stock o ajustar compras. | Stream; limita servicio y disponibilidad del menú. |
| 9 | `inventory_overstock_detected` | Baseline CONTEXT | El exceso se concentra por categoría/local; reducir compras y redistribuir inventario. | Batch diario; la respuesta no depende de segundos. |
| 10 | `inventory_recommendation_generated` | Oportunidad | Riesgo y cobertura proyectada varían por SKU/local; priorizar órdenes sugeridas y calibrar predicción. | Batch cada hora; no es una alarma hasta cruzar el mínimo. |
| 11 | `auth_login_succeeded` | Oportunidad | La adopción y horario de acceso varían por rol/local; planificar soporte y acceso. | Batch diario; no requiere acción inmediata. |
| 12 | `auth_login_failed` | Obligatorio RFI | Fallos anómalos o repetidos pueden señalar fricción o ataque; investigar y aplicar controles. | Stream para agregados de umbral, con actualización en minutos; nunca emitir credenciales. |
| 13 | `auth_session_expired` | Obligatorio RFI | Expiraciones interrumpen trabajo; ajustar duración de sesión o mejorar recuperación. | Batch cada 15 min; analizar tasa y contexto, sin alertar por cada sesión. |
| 14 | `auth_access_denied` | Oportunidad | Denegaciones repetidas indican permisos incorrectos o intentos fuera de rol; corregir acceso o investigar. | Stream para denegaciones a recursos sensibles; resto batch cada 15 min. |
| 15 | `navigation_section_viewed` | Obligatorio RFI | El uso de secciones varía por rol/local; priorizar mejoras y formación. | Batch diario; telemetría de producto, no decisión por segundo. |
| 16 | `navigation_flow_started` | Oportunidad de medición | El denominador de flujos iniciados permite calcular abandono por paso; localizar fricción. | Batch diario; analítica de embudo. |
| 17 | `navigation_flow_abandoned` | Obligatorio RFI | Un flujo iniciado no llega a completar; simplificar pasos o corregir errores. | Batch cada 15 min; investigar tendencia, no interrumpir al usuario. |
| 18 | `api_latency_recorded` | Obligatorio RFI | Latencia y tasa de error superan objetivos por ruta; escalar o optimizar servicio. | Stream agregado/minuto para incumplimientos de SLO; detalle batch para diagnóstico. |
| 19 | `frontend_page_load_recorded` | Obligatorio RFI | Ciertas páginas tardan más por dispositivo/mercado; optimizar carga y priorizar impacto. | Batch cada 15 min; p95 por página guía acción, no evento individual. |
| 20 | `frontend_error_captured` | Obligatorio RFI | Errores cliente afectan flujos o versiones específicas; corregir release y reducir abandono. | Stream de conteos por huella/version para errores nuevos o crecientes; resto batch. |
| 21 | `backend_error_captured` | Oportunidad | Excepciones se agrupan por ruta/versión; corregir regresiones y proteger disponibilidad. | Stream para 5xx y fallos críticos; detalles batch/redactados para análisis. |
| 22 | `pos_connectivity_observed` | Oportunidad | Un POS o local pierde conectividad o deja de reportar ventas en horario abierto; contactar local/restaurar integración. | Stream; inactividad operativa requiere detección cercana al tiempo real. |
| 23 | `supplier_price_changed` | Oportunidad | El costo de proveedor cambia por SKU/país; revisar negociación y margen. | Batch diario; detección al recibir/importar precio es suficiente. |
| 24 | `customer_order_completed` | Baseline CONTEXT | La frecuencia/retención cambia por cohorte y mercado; ajustar fidelización/personalización. | Batch diario; análisis de cohortes, sin perfil identificable en el evento. |
| 25 | `training_recipe_update_published` | Baseline CONTEXT | Cambios tardan en distribuirse; priorizar publicación y comprobar tiempo de despliegue. | Stream; centros/locales deben recibir cambios operativos oportunamente. |
| 26 | `training_recipe_update_acknowledged` | Baseline CONTEXT | Locales no reconocen una versión publicada; escalar formación y cerrar brechas de adopción. | Batch cada hora; alerta solo por SLA vencido, no por cada confirmación. |
| 27 | `hr_vacancy_filled` | Baseline CONTEXT | El tiempo de cobertura cambia por país/rol; ajustar reclutamiento y capacidad. | Batch diario; KPI de gestión, no acción en segundos. |
| 28 | `hr_absence_recorded` | Baseline CONTEXT | El absentismo se concentra por periodo/local; ajustar cobertura de turnos. | Batch diario; evitar revelar información personal/sanitaria. |
| 29 | `hr_employment_status_changed` | Baseline CONTEXT | La rotación varía por país/rol/local; revisar retención y planificación de plantilla. | Batch diario; indicador agregado, sin motivo personal. |
| 30 | `audit_sensitive_action_recorded` | Oportunidad | Operaciones sensibles sin trazabilidad suficiente elevan riesgo; revisar auditoría y controles de acceso. | Stream para cambios y exportaciones sensibles; respuesta rápida ante uso indebido. |

El JSON adjunto contiene descripción, allowlist cerrada, tipos, obligatoriedad, significado, sensibilidad/sanitización, hipótesis, decisión y modo/justificación para cada evento. La propiedad `classification` permite distinguir los grupos. Son 30 eventos: 11 requisitos expresos del RFI, 10 del baseline KPI sugerido por CONTEXT y 9 oportunidades identificadas. Dado que el CONTEXT disponible no marca esos KPI como obligatorios, el recuento estricto es 10 baseline de CONTEXT vs. 20 eventos adicionales (11 RFI + 9 oportunidades); el piso completo del encargo son los 21 eventos de CONTEXT/RFI.

### Cobertura de KPI del CONTEXT

- Ventas diarias/semanales por local, país y moneda: `sales_event_recorded` (agregación derivada de ventas canónicas).
- Ticket promedio y margen estimado: `finance_kpi_snapshot_recorded`.
- Quiebres y sobrestock por categoría: `inventory_stockout_detected` e `inventory_overstock_detected`.
- Tiempo medio de cobertura de vacantes: `hr_vacancy_filled`.
- Rotación y absentismo: `hr_employment_status_changed` y `hr_absence_recorded`.
- Frecuencia/retención por cohortes: `customer_order_completed` con identificador seudónimo rotatorio.
- Tiempo de despliegue y adopción de recetas: `training_recipe_update_published` y `training_recipe_update_acknowledged`.

Los KPI sugeridos no son nuevos eventos obligatorios por sí mismos: se calculan desde eventos/transacciones fuente y snapshots definidos aquí. Reportes financieros convierten a COP/USD solo mediante tasa versionada y conservan siempre `country`, moneda original y fecha efectiva; no mezclar monedas sin conversión trazable.

## Flujo de inventario y puntos de captura

1. Login exitoso/fallido y expiración: `auth_login_succeeded`, `auth_login_failed`, `auth_session_expired`.
2. Acceso a sección y comienzo de flujo: `navigation_section_viewed`, `navigation_flow_started`.
3. Consulta de existencias/recomendación: oportunidad `inventory_recommendation_generated`; no emitir evento por cada lectura de lista.
4. Validación de una orden de salida: `inventory_validation_failed` por rechazo; emitir solo regla/código estable y SKU permitido, nunca el texto libre de entrada.
5. Envío de orden de salida autorizada: `inventory_outbound_order_submitted`, únicamente tras aceptación persistida por el dominio. La implementación futura debe enlazar el evento con su `movementId` y actor.
6. Recepción/entrada: `inventory_receipt_created`, tras transacción persistida. El sistema ya implementa `/api/v1/inventory/receipts` y el cambio de stock queda respaldado por recibo y rol.
7. Cruce de mínimo, quiebre y exceso: `inventory_stock_threshold_triggered`, `inventory_stockout_detected`, `inventory_overstock_detected`. Evaluar transiciones/estado con ventanas definidas, no cada polling.
8. Intento de mutación directa: `inventory_direct_stock_edit_rejected`; registrar el rechazo sin mutar stock y con actor/scope si se conoce.
9. Errores y demora del flujo: `api_latency_recorded`, `backend_error_captured`, `frontend_error_captured`, `navigation_flow_abandoned`.

Los IDs de orden/sesión/correlación permiten reconstruir la cadena sin poner contenido de notas ni datos de credenciales en telemetría. Los eventos de entrada/salida se escriben en la misma unidad lógica de confirmación o mediante outbox transaccional; no publicar un éxito antes del commit.

## Event Envelope y contrato

Todo evento transporta `eventId`, `timestamp`, `sessionId`, `userId`, `event_type`, `schemaVersion`, `requestId` y `properties`. El sobre siempre conserva las claves requeridas. `timestamp` es ISO 8601 UTC (`Z` o `+00:00`); `eventId` UUID único; `schemaVersion` es `1.0.0`; `requestId` se crea en el borde si no llega uno confiable y se propaga entre cliente, API y logs. `sessionId`/`userId` admiten `null` antes de autenticar o para trabajos de sistema; el campo no se omite. Para `userId`, usar HMAC estable con clave rotatoria y ámbito Brasaland, nunca email, nombre ni ID interno en claro. Un actor de proceso usa `userId: null` y `properties.actor_type: "system"` cuando el evento lo declara.

`properties` es objeto cerrado: cada evento permite exactamente las claves de `allowlist` de `event-schemas.json`; claves extra se rechazan al validar. Datos de hora operativa incluyen `store_id`, `country` y `timezone` cuando aplican. Los países son `CO`/`US`; monedas `COP`/`USD`; fechas de evento se emiten en UTC y se interpretan para operación usando la zona IANA del local. No usar nombre del local como clave cuando `store_id` baste.

El archivo JSON usa el formato personalizado `brasaland-event-catalog/v1` (no se presenta como JSON Schema Draft-07). Se valida su sintaxis y las invariantes descritas aquí: tipo único, sobre común, allowlist igual a claves de `properties`, `required` como subconjunto de allowlist y modo `stream|batch` con justificación no vacía. Cada propiedad declara tipo, requerida/opcional, descripción, sensibilidad y sanitización.

## Entrega, frecuencia y calidad

- **Stream:** eventos que exigen respuesta durante el turno (mínimos/quiebres, orden confirmada, rechazo directo, conectividad, errores/latencia críticos y publicación de receta). Ingesta objetivo p95 menor a 60 s; conservar `eventId` para deduplicación y reintentar con backoff.
- **Batch:** analítica de negocio, RR. HH., navegación y rendimiento ordinario. Agregar por ventana UTC y dimensión; preservar el `timestamp` original, zona del local, periodo y cantidad de eventos. Lote inicial cada 15 minutos, horario o diario según el contrato individual.
- **Throttle/debounce:** visitas a sección una por sesión/sección/30 s; page-load una por navegación finalizada; latencia agrupada por minuto/ruta/método/status/versión y percentiles, no una muestra ilimitada de payloads; errores agrupados por huella normalizada y versión, con primera ocurrencia y contador cada minuto; conectividad solo ante cambio de estado y heartbeat como máximo cada 5 min por local/fuente; alertas de mínimo/quiebre solo en transición, con rearmado cuando el stock vuelva sobre el umbral; flujo abandonado una sola vez tras 30 min sin actividad, cancelación explícita o cierre cuando sea observable. No perder conteos: la agregación debe conservar total, primera/última ocurrencia y cardinalidad acotada.
- **Integridad:** esquema validado en productor e ingreso; rechazar propiedades extra, cuarentena de inválidos sin payload sensible; deduplicar por `eventId`; medir eventos aceptados/rechazados, atraso de ingestión y cobertura de productores. Reconciliar recibos/salidas con el ledger operacional; telemetría no sustituye la fuente transaccional.
- **Retención propuesta:** eventos crudos seudónimos 30 días, agregados no identificables 13 meses; auditoría sensible según política de seguridad/retención legal. Acordar estos plazos con seguridad y RR. HH. antes de producción.

## Privacidad, riesgos y exclusiones

- Nunca capturar contraseñas, tokens JWT/API/reset, cabeceras de autenticación, email, teléfono, nombre, dirección, nota/comentario libre, contenido de recetas, pedido detallado de cliente, texto completo de excepción, query string, cuerpo HTTP ni IP sin truncar/justificación aprobada. Tampoco registrar información médica, motivo de ausencia o causa de terminación.
- Emails usados en login se descartan tras resolver usuario; fallos no deben permitir enumeración. Usar solo `failure_code` controlado y `userId` HMAC únicamente si el sujeto existe; de lo contrario `null`. Contadores y umbrales no deben exponer identidades.
- RR. HH. se agrega por país/local/rol y periodo con umbral mínimo de cohorte (p. ej. 5 personas); suprimir celdas pequeñas. `employee_ref` es seudónimo con rotación, solo si la evaluación de privacidad autoriza análisis longitudinal.
- Exclusiones: capturas de pantalla/teclas, navegación externa, ubicación precisa, perfilado individual de empleados/clientes, cuerpos completos de requests/responses y cada lectura/polling. Su coste y riesgo exceden la decisión soportada.
- Riesgos: APIs actuales no aportan `sessionId`/`requestId` uniformes; login no persiste fallos; navegación depende del cliente; no existe orden de salida ni rechazo de mutación directa en rutas actuales; umbral/quiebre necesita regla de negocio y configuración de mínimo; datos de ventas/moneda y zonas requieren normalización; alertas pueden duplicarse durante reintentos. Añadir middleware/correlación, productores transaccionales y controles de acceso antes de prometer cobertura.
- Acordar definición exacta de “quiebre”, “sobrestock”, “margen estimado”, “flujo abandonado”, la tasa de conversión COP/USD, objetivos SLO y ventana/retención con Operaciones, Finanzas y RR. HH. Si una regla crítica no está acordada, no emitir una clasificación presentada como verdad.

## Secuencia de implementación sugerida

1. Instrumentar sobre transacciones confirmadas ventas/recibos y el envelope común, con outbox/deduplicación y correlación.
2. Añadir umbrales de inventario configurables y eventos de rechazo; implementar orden de salida trazable antes de emitir su evento.
3. Añadir login, acceso, API/frontend, conectividad y navegación con sanitización y límites de frecuencia.
4. Completar eventos de formación, clientes, proveedores y RR. HH. tras aprobación de privacidad y definición de cohortes.
5. Evaluar cobertura, falsos positivos, latencia y decisiones tomadas en piloto Medellín/Florida antes de ampliar.