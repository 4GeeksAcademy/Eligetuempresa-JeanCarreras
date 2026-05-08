# Roadmap Brasaland por hitos (AI Engineering)

## Objetivo

Convertir Brasaland en una operacion digital multipais (Colombia + Florida) con datos en tiempo casi real, manteniendo consistencia de producto y experiencia de cliente.

## Principios de ejecucion

- Priorizar entregables que reduzcan decisiones por intuicion.
- Diseñar para dos monedas (COP, USD) desde el inicio.
- Favorecer MVPs integrables sobre soluciones aisladas.
- Medir impacto de negocio con KPIs desde cada hito.

## Plan de hitos

### Hito 0 - Prework

- Contexto de empresa cargado en CONTEXT.md.
- Definicion de glosario y entidades core.
- Checklist de setup de equipo y repositorio.

Entregables:

- Documento de alcance funcional inicial.
- Backlog priorizado (operaciones, compras, marketing, RRHH).

### Hito 1 - Web

- Sitio corporativo actualizado de Brasaland.
- Formulario para contacto/franquicias/soporte.
- SEO base y estructura de contenidos.

KPI sugeridos:

- Conversion formulario.
- Trafico organico por mercado.

### Hito 2 - Programacion

- Libreria de logica de negocio comun (ticket promedio, conversion de moneda, reglas de alertas).
- Reglas de scoring de riesgo de stock.

KPI sugeridos:

- Precision del scoring vs quiebres reales.

### Hito 3 - UI con IA

- Prototipos guiados por IA para paneles de operaciones y ejecutivos.
- Validacion con stakeholders (Felipe, Mariana).

KPI sugeridos:

- Tiempo de comprension de metricas.
- Numero de iteraciones de UX.

### Hito 4 - Next.js

- Portal interno inicial (operaciones + direccion).
- Modulos: ventas por local, alertas operativas, comparativo por pais.

KPI sugeridos:

- Usuarios activos semanales internos.

### Hito 5 - Backend

- API central de Brasaland (locales, menus, ventas, inventario, clientes, proveedores).
- Contratos API versionados.

KPI sugeridos:

- Cobertura de endpoints criticos.
- Latencia media de consultas.

### Hito 6 - Telemetria

- Ingestion de eventos de ventas e inventario.
- Pipeline de datos para dashboards.

KPI sugeridos:

- Frescura de datos (minutos).
- Porcentaje de eventos procesados correctamente.

### Hito 7 - RAG y memoria

- Base semantica de recetas/procedimientos/documentacion operativa.
- Busqueda interna para soporte de operaciones y formacion.

KPI sugeridos:

- Tasa de respuestas utiles.
- Tiempo de resolucion de dudas operativas.

### Hito 8 - Agentes

- Agente de soporte operativo para managers de local.
- Agente de onboarding para personal nuevo.

KPI sugeridos:

- Reduccion de tickets internos repetitivos.

### Hito 9 - Workflows

- Automatizacion de reporte semanal ejecutivo (lunes 07:00).
- Alertas de local abierto sin ventas.
- Flujos de aprobacion de compras.

KPI sugeridos:

- Tiempo ahorrado por automatizacion.
- SLA de envio de reportes.

### Hito 10 - Tiempo real

- Dashboard en vivo para direccion y operaciones.
- Streaming de eventos con alertas en tiempo real.

KPI sugeridos:

- Tiempo de deteccion de incidentes.
- Tiempo de reaccion operativa.

## Entregables transversales minimos

- Definicion de datos y contratos API.
- Trazabilidad de decisiones tecnicas.
- KPIs medidos por hito.
- Demo funcional al cierre de cada fase.
