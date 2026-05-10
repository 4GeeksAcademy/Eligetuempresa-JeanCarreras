# marketing-loyalty-app

Mobile web interface for Brasaland Marketing and Digital Experience.

## Objective

Deliver a customer-facing flow for:

- Digital loyalty with Brasa Points.
- Online order creation (app/web).
- Order history and personalized recommendations.

## Stack

- HTML + CSS + JavaScript.

## Consumed endpoints

- GET /api/v1/stores
- GET /api/v1/customers/{customer_id}
- GET /api/v1/marketing/crm/customers
- GET /api/v1/marketing/customers/{customer_id}/history
- GET /api/v1/marketing/personalization/recommendations
- POST /api/v1/marketing/orders

## Run

1. Start local API:

```bash
bash scripts/run_api_local.sh
```

2. Open the app:

- File: uis/marketing-loyalty-app/index.html
- Or serve it with your preferred static server.

## Notes

- Read calls use executive token.
- Order creation uses operations token.
