# marketing-loyalty-app

Interfaz movil web para Marketing y Experiencia Digital en Brasaland.

## Objetivo

Ofrecer una experiencia de cliente final para:

- Fidelizacion digital con Brasa Points.
- Creacion de pedidos online (app/web).
- Consulta de historial y recomendaciones personalizadas.

## Stack

- HTML + CSS + JavaScript.

## Endpoints consumidos

- GET /api/v1/stores
- GET /api/v1/customers/{customer_id}
- GET /api/v1/marketing/crm/customers
- GET /api/v1/marketing/customers/{customer_id}/history
- GET /api/v1/marketing/personalization/recommendations
- POST /api/v1/marketing/orders

## Ejecutar

1. Levanta la API local:

```bash
bash scripts/run_api_local.sh
```

2. Abre la app:

- Archivo: uis/marketing-loyalty-app/index.html
- O con servidor estático de tu preferencia.

## Notas

- Usa token ejecutivo para lectura CRM/recomendaciones.
- Usa token de operaciones para crear pedidos digitales.
