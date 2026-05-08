#!/usr/bin/env python3
"""Genera un reporte ejecutivo semanal consumiendo la API de Brasaland."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def fetch_json(url: str) -> dict | list:
    with urlopen(url, timeout=10) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def build_report(api_base: str, currency: str) -> str:
    summary = fetch_json(f"{api_base}/api/v1/sales/summary?period=week&currency={currency}")
    markets = fetch_json(f"{api_base}/api/v1/markets/summary?currency={currency}")
    alerts = fetch_json(f"{api_base}/api/v1/alerts/inactivity?window_minutes=60")

    lines: list[str] = []
    lines.append("# Reporte Ejecutivo Semanal - Brasaland")
    lines.append("")
    lines.append(f"Generado: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Moneda de reporte: {currency}")
    lines.append("")
    lines.append("## KPI de cadena")
    lines.append("")
    lines.append(f"- Ventas semanales: {summary['total_sales']:.2f} {currency}")
    lines.append(f"- Ticket promedio: {summary['average_ticket']:.2f} {currency}")
    lines.append(f"- Locales activos: {alerts['active_stores']}/{alerts['total_stores']}")
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
