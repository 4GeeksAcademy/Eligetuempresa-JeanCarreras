#!/usr/bin/env python3
"""Genera un reporte ejecutivo semanal consumiendo la API de Brasaland."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


def fetch_json(url: str, headers: dict[str, str] | None = None) -> dict | list:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=10) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def build_report(api_base: str, currency: str) -> str:
    exec_token = os.getenv("BRASALAND_EXECUTIVE_TOKEN", "brasaland-executive-token")
    headers = {
        "X-API-Role": "executive",
        "X-API-Token": exec_token,
    }
    report_primary = fetch_json(f"{api_base}/api/v1/executive/weekly-report?currency={currency}", headers=headers)
    report_usd = fetch_json(f"{api_base}/api/v1/executive/weekly-report?currency=USD", headers=headers)
    report_cop = fetch_json(f"{api_base}/api/v1/executive/weekly-report?currency=COP", headers=headers)
    ask_florida = fetch_json(
        f"{api_base}/api/v1/executive/ask?question=Cuanto%20vendimos%20esta%20semana%20en%20Florida%3F&currency={currency}",
        headers=headers,
    )
    ask_top_ticket = fetch_json(
        f"{api_base}/api/v1/executive/ask?question=Que%20local%20tiene%20el%20ticket%20medio%20mas%20alto%20este%20mes%3F&currency={currency}",
        headers=headers,
    )

    summary = report_primary["summary"]
    markets = report_primary["markets"]
    alerts = report_primary["inactivity"]
    alerts_sla = report_primary["alerts_sla"]

    lines: list[str] = []
    lines.append("# Reporte Ejecutivo Semanal - Brasaland")
    lines.append("")
    lines.append(f"Generado: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Moneda de reporte: {currency}")
    lines.append("")
    lines.append("## KPI de cadena")
    lines.append("")
    lines.append(f"- Ventas semanales de cadena (USD): {report_usd['summary']['total_sales']:.2f} USD")
    lines.append(f"- Ventas semanales de cadena (COP): {report_cop['summary']['total_sales']:.2f} COP")
    lines.append(f"- Ventas semanales: {summary['total_sales']:.2f} {currency}")
    lines.append(f"- Ticket promedio: {summary['average_ticket']:.2f} {currency}")
    lines.append(f"- Locales activos: {alerts['active_stores']}/{alerts['total_stores']}")
    lines.append(f"- Riesgo inactividad: {alerts['risk_level'].upper()} ({alerts['critical_ratio_pct']:.2f}% critico)")
    lines.append(f"- SLA alertas <=30m: {alerts_sla['resolved_within_sla_pct']:.2f}%")
    lines.append("")
    lines.append("## Mercados")
    lines.append("")

    for market in markets:
        variation = market["wow_variation_pct"]
        sign = "+" if variation >= 0 else ""
        lines.append(
            f"- {market['market']}: ventas {market['sales']:.2f} {currency}, "
            f"ticket {market['average_ticket']:.2f} {currency}, "
            f"WoW {sign}{variation:.1f}%"
        )

    lines.append("")
    lines.append("## Highlights asistente ejecutivo")
    lines.append("")
    lines.append(f"- Pregunta: {ask_florida['question']}")
    lines.append(f"  Respuesta: {ask_florida['answer']}")
    lines.append(f"- Pregunta: {ask_top_ticket['question']}")
    lines.append(f"  Respuesta: {ask_top_ticket['answer']}")

    if alerts["alerts"]:
        lines.append("")
        lines.append("## Alertas de inactividad")
        lines.append("")
        for item in alerts["alerts"]:
            lines.append(
                f"- {item['store_name']} ({item['market']}): "
                f"{item['minutes_without_sales']} min sin ventas"
            )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generar reporte ejecutivo semanal Brasaland")
    parser.add_argument("--api-base", default="http://localhost:8000", help="Base URL del API")
    parser.add_argument("--currency", default="USD", choices=["USD", "COP"], help="Moneda del reporte")
    parser.add_argument("--output", default="", help="Ruta de salida opcional")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        report = build_report(args.api_base, args.currency)
    except URLError as exc:
        print(f"Error conectando al API: {exc}")
        return 1

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"Reporte guardado en {output_path}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
