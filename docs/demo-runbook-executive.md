# Executive Demo Script (10 minutes) - Brasaland

This script helps present business value by role with live, verifiable evidence.

## Setup (1 minute)

1. Verify active services:
- API: http://localhost:8000/health
- Executive dashboard: http://localhost:4173
- Mobile loyalty/ordering app: http://localhost:4174
2. Keep one tab/window per interface:
- Dashboard (operations/procurement/marketing)
- Mobile customer app

## Demo agenda

## 1) Felipe Guerrero - Operations (3 minutes)

Goal: show day-to-day visibility and immediate operational action across 14 stores.

Flow:
1. Open dashboard at http://localhost:4173.
2. Show sales by store and switch country/currency filters (COP/USD).
3. Open opening-hours inactivity alerts.
4. Execute an alert action (ACK and then RESOLVE).
5. Open smart order recommendations (history + stock).

Key messages:
- Chain-wide store monitoring is continuous.
- Operations can respond to alerts without leaving the console.
- Suggested ordering helps reduce stockout risk.

## 2) Lucia Fernandez - Procurement and Suppliers (3 minutes)

Goal: show cost control and multi-country centralized negotiation.

Flow:
1. Go to Procurement and suppliers section.
2. Show supplier/SKU price history.
3. Show configurable threshold-based price alerts.
4. Show chain consolidated purchases (CO + US).

Key messages:
- Price spikes are detected using configurable thresholds.
- Consolidation enables better volume negotiation leverage.
- Country/currency support keeps comparisons decision-ready.

## 3) Camila Ospina - Marketing and Digital Experience (3 minutes)

Goal: show end-to-end customer-CRM-personalization cycle.

Flow:
1. In dashboard, open Marketing panel and show CRM overview.
2. Show customer list with history and behavior summary.
3. Show personalized recommendations for a customer.
4. Open mobile app at http://localhost:4174 and simulate an order.

Key messages:
- Every digital order updates loyalty points.
- CRM centralizes history and preferences for campaign activation.
- Personalization improves repurchase probability.

## Executive close (1 minute)

Impact summary:
1. Operations: faster response to inactivity events.
2. Procurement: stronger negotiation position via demand consolidation.
3. Marketing: higher recurrence via loyalty and recommendations.

## Quick fallback plan

If dashboard data is not loading:
1. Check API health at http://localhost:8000/health.
2. Restart API with scripts/restart_api_local.sh.

If mobile app is not loading:
1. Confirm port 4174 is active.
2. Start static server in uis/marketing-loyalty-app with python3 -m http.server 4174 --bind 0.0.0.0.

If an endpoint fails:
1. Verify role/token headers.
2. Retry using examples in services/brasaland-api/README.md.
