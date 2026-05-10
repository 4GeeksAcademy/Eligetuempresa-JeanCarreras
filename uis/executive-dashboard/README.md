# executive-dashboard

Brasaland executive dashboard MVP for quick chain KPI visibility.

## Initial scope

- Consolidated weekly sales.
- Average ticket.
- Store activity status.
- Country and date range filters.
- Sales by-store table.
- Daily sales trend chart.
- Market comparison with WoW variation.
- Estimated finance KPI panel (revenue, COGS, gross profit, margin).
- Procurement and suppliers panel (history, alerts, and chain consolidated purchases).
- Marketing panel (CRM, customer intelligence, and personalization).
- People and culture panel (vacation/absence requests, onboarding flow, and HR KPIs by country).
- Training and quality standards panel (recipe search, structured onboarding itineraries, and chain-wide recipe update publishing).
- Executive direction panel (weekly chain sales in USD and COP, natural-language AI assistant, and Monday 07:00 automated weekly report preview).

## Run locally

Simple option:

```bash
cd services/brasaland-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd uis/executive-dashboard
python -m http.server 5500
```

Open in browser:

- http://localhost:5500

## Next step

- Add drill-down by store.
- Integrate authentication for internal profiles.
