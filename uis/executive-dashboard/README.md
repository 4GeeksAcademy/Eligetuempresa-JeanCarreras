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
