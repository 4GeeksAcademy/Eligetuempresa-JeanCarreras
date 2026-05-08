# Workflows iniciales Brasaland

## Objetivo

Definir automatizaciones prioritarias para reducir carga manual y mejorar velocidad de decision.

## Workflow 1 - Reporte ejecutivo semanal

Nombre: weekly-executive-report

Frecuencia:

- Cada lunes a las 07:00 (zona horaria configurable por destinatario principal).

Entradas:

- Ventas semanales por local.
- Ticket promedio por local y pais.
- Top variaciones semana contra semana.

Procesamiento:

1. Extraer metricas de la ultima semana cerrada.
2. Normalizar vista en COP y USD.
3. Generar resumen narrativo corto.
4. Publicar por email/Slack a direccion.

Salidas:

- Informe en PDF o HTML.
- Registro de ejecucion (status, duracion, errores).

Alertas de fallo:

- Notificar a equipo de Tecnologia si falla 2 veces consecutivas.

Implementacion inicial disponible:

- `workflows/scripts/weekly_executive_report.py`
- Ejemplo: `python workflows/scripts/weekly_executive_report.py --api-base http://localhost:8000 --currency USD --output workflows/output/weekly-report.md`

## Workflow 2 - Local abierto sin ventas

Nombre: zero-sales-open-store-alert

Frecuencia:

- Revision cada 15 minutos durante horario de apertura por local.

Entradas:

- Estado de horario de local.
- Eventos de venta en ventana movil.

Regla base:

- Si local esta en horario abierto y no hay ventas en los ultimos 60 minutos, generar alerta.

Salidas:

- Mensaje a supervisor de operaciones.
- Registro de incidente.

## Workflow 3 - Variacion de precio de proveedor

Nombre: supplier-price-change-alert

Frecuencia:

- Diaria al cierre de jornada.

Entradas:

- Ultima lista de precios por proveedor.
- Historico de precios por SKU.

Regla base:

- Alertar si variacion absoluta supera umbral configurable (ej. 8%).

Salidas:

- Resumen por proveedor/categoria.
- Recomendacion de SKU a renegociar.

## Workflow 4 - Onboarding operativo

Nombre: kitchen-onboarding-flow

Disparador:

- Alta de nueva persona en RRHH.

Pasos:

1. Crear checklist de formacion por rol.
2. Asignar material de recetas y seguridad alimentaria.
3. Programar recordatorios de seguimiento.
4. Registrar completitud de hitos.

## Estandar de documentacion por workflow

Cada flujo debe incluir:

- Objetivo.
- Trigger.
- Dependencias de datos.
- Credenciales necesarias.
- Manejo de errores y reintentos.
- Responsable operativo.
