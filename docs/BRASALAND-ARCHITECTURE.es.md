# Arquitectura objetivo Brasaland

## Resumen

Arquitectura modular orientada a dominio para soportar operaciones multipais, multimoneda y evolutivas.

Capas:

1. Captura de datos operativos (ventas, inventario, pedidos).
2. API central y servicios de negocio.
3. Plataforma de datos y analitica.
4. Apps y paneles para equipos internos y clientes.
5. Automatizaciones y agentes.

## Dominios de negocio iniciales

- Locales
- Ventas
- Menu y productos
- Inventario
- Compras y proveedores
- Clientes y fidelizacion
- RRHH (fase posterior)

## Componentes iniciales

### 1) API central

Responsabilidades:

- Exponer recursos estandarizados para todos los consumidores internos.
- Normalizar moneda y fechas para reportes multipais.
- Unificar acceso a datos provenientes de POS heterogeneos.
- Aplicar control de acceso por roles para operaciones, direccion y finanzas.

Endpoints MVP sugeridos:

- GET /health
- GET /api/v1/stores
- GET /api/v1/sales/summary
- POST /api/v1/events/sales
- POST /api/v1/events/inventory

### 2) Pipeline de datos

Responsabilidades:

- Ingesta de eventos transaccionales y operativos.
- Transformaciones para metricas de operaciones y direccion.
- Publicacion de datasets para dashboards.

Datasets MVP:

- fact_sales_daily
- fact_ticket_hourly
- fact_inventory_status
- dim_store
- dim_supplier

### 3) Capa de experiencia

- Dashboard ejecutivo (Mariana): ventas, ticket promedio, comparativo por pais.
- Dashboard operativo (Felipe): actividad por local, alertas de inactividad, riesgo de stock.

### 4) Automatizaciones (workflows)

- Reporte semanal ejecutivo (lunes 07:00).
- Alerta de local abierto sin ventas.
- Notificacion de variaciones de precio de proveedores.
- Distribucion automatica de reporte por Slack/email segun configuracion.

## Modelo de datos base

Entidades clave:

- Store: id, pais, ciudad, timezone, moneda_base.
- SaleEvent: id_evento, store_id, fecha_hora, total_bruto, total_neto, moneda.
- InventoryItem: sku, store_id, stock_actual, stock_minimo, unidad.
- SupplierPrice: proveedor_id, sku, precio, moneda, fecha_vigencia.
- Customer: id, mercado, segmento, puntos_fidelizacion.

## Reglas de negocio base

- Toda metrica consolidada debe poder verse en COP y USD.
- Eventos deben registrar timezone de origen.
- Alertas operativas deben considerar calendario y horario de apertura por local.

## No funcionales

- Observabilidad: logs estructurados y metricas por servicio.
- Seguridad: autenticacion para endpoints internos y auditoria basica.
- Escalabilidad: API stateless y procesamiento desacoplado por eventos.
- Trazabilidad: registro de auditoria para operaciones sensibles y exportacion de datos.

## Riesgos principales

- Integracion de POS diferentes por pais.
- Calidad incompleta de datos historicos.
- Diferencias operativas entre mercados.

## Mitigaciones

- Definir contrato canonico de eventos desde el inicio.
- Aplicar validaciones de esquema en ingestion.
- Iterar con pilotos en 2 locales (1 en Medellin, 1 en Florida).
