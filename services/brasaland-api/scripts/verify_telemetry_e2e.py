import argparse
import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from playwright.sync_api import expect, sync_playwright
from pydantic import ValidationError


SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))
from src.brasaland_api.telemetry import TelemetryEvent


def verify(api_base: str, ui_base: str, output: Path) -> None:
    load_dotenv(SERVICE_DIR / ".env")
    supabase_url = os.environ["SUPABASE_URL"].rstrip("/")
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    run_id = str(uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    emitted = {}
    acknowledgements = []
    producer_rejections = []
    output.mkdir(parents=True, exist_ok=True)

    def is_telemetry(response) -> bool:
        return (
            response.request.method == "POST"
            and urlsplit(response.url).path == "/telemetry/events"
        )

    def includes_event(response, event_type: str) -> bool:
        return is_telemetry(response) and any(
            event.get("event_type") == event_type
            for event in response.request.post_data_json["events"]
        )

    def collect(response) -> None:
        if is_telemetry(response):
            for event in response.request.post_data_json["events"]:
                try:
                    TelemetryEvent.model_validate(event)
                except ValidationError:
                    producer_rejections.append({
                        "event_type": event.get("event_type", "unknown"),
                        "reason": "contract_validation_failed",
                    })
                else:
                    emitted[event["eventId"]] = event
            assert response.status == 200, "Frontend telemetry was not acknowledged"
            counts = response.json()
            assert counts["received"] == counts["stored"] + counts["rejected"]
            acknowledgements.append(counts)

    with httpx.Client(base_url=api_base, timeout=30) as api:
        measured_at = perf_counter()
        health = api.get("/health")
        health_duration = (perf_counter() - measured_at) * 1000
        health.raise_for_status()

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            context.on("response", collect)
            page = context.new_page()
            page.goto(f"{ui_base}/executive-dashboard/", wait_until="load")
            page.locator("#receiptForm").scroll_into_view_if_needed()
            page.select_option("#receiptStoreId", "med-001")
            page.select_option("#receiptSku", "CHICKEN")
            page.fill("#receiptQty", "0.1")
            page.select_option("#receiptCurrency", "COP")
            page.fill("#receiptNote", "")
            with page.expect_response(
                lambda response: includes_event(response, "inventory_receipt_created"),
                timeout=45000,
            ) as receipt_ack:
                with page.expect_response(
                    lambda response: response.request.method == "POST"
                    and urlsplit(response.url).path == "/api/v1/inventory/receipts",
                    timeout=30000,
                ) as receipt_response:
                    page.click("#receiptSubmit")
                assert receipt_response.value.status == 201, "Local receipt was not committed"
                receipt = receipt_response.value.json()
                expect(page.locator("#receiptStatus")).to_contain_text("Recepcion registrada")
            assert receipt_ack.value.json()["stored"] > 0
            page.locator("#receiptForm").screenshot(path=str(output / "backoffice-receipt.png"))

            login = context.new_page()
            login.goto(f"{ui_base}/auth/", wait_until="load")
            login.locator('[data-form="login"] input[name="email"]').fill(
                f"telemetry-e2e-{run_id}@example.invalid"
            )
            login.locator('[data-form="login"] input[name="password"]').fill(str(uuid4()))
            with login.expect_response(
                lambda response: includes_event(response, "auth_login_failed"),
                timeout=45000,
            ) as login_ack:
                with login.expect_response(
                    lambda response: response.request.method == "POST"
                    and urlsplit(response.url).path == "/auth/login",
                    timeout=30000,
                ) as login_response:
                    login.locator('[data-form="login"] button').click()
                login_http_status = login_response.value.status
                assert login_http_status in {401, 422}, "Expected a genuinely failed login"
                expect(login.locator('[data-form="login"] .feedback')).to_have_class("feedback error")
            assert login_ack.value.json()["stored"] > 0

            valid = {
                "eventId": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sessionId": None,
                "userId": None,
                "event_type": "api_latency_recorded",
                "schemaVersion": "1.0.0",
                "requestId": f"e2e-manual-{run_id}",
                "properties": {
                    "route_template": "/health", "method": "GET", "status_code": 200,
                    "duration_ms": health_duration, "service_version": "0.1.0",
                },
            }
            invalid = {
                **valid, "eventId": str(uuid4()),
                "properties": {**valid["properties"], "not_allowlisted": True},
            }
            mixed = {"events": [valid, invalid, {"event_type": "unknown_event"}]}
            mixed_response = api.post("/telemetry/events", json=mixed)
            assert mixed_response.status_code == 200
            result = mixed_response.json()
            assert result == {"received": 3, "stored": 1, "rejected": 2}
            retry = api.post("/telemetry/events", json=mixed)
            assert retry.status_code == 200
            assert retry.json() == {"received": 3, "stored": 0, "rejected": 3}

            with httpx.Client(
                base_url=supabase_url,
                headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
                timeout=30,
            ) as storage:
                event_ids = list(emitted) + [valid["eventId"]]
                stored = storage.get("/rest/v1/telemetry_events", params={
                    "select": "event_id,event_type,timestamp,service,tags,request_id,received_at",
                    "event_id": "in.(" + ",".join(event_ids) + ")",
                    "order": "received_at.asc",
                })
                stored.raise_for_status()
                rows = stored.json()
                assert len(rows) >= 5, "Need at least five real persisted events"
                by_id = {row["event_id"]: row for row in rows}
                receipt_events = [
                    event for event in emitted.values()
                    if event["event_type"] == "inventory_receipt_created"
                ]
                assert len(receipt_events) == 1
                assert receipt_events[0]["properties"]["receipt_id"] == str(receipt["receipt_id"])
                assert by_id[receipt_events[0]["eventId"]]["tags"] == receipt_events[0]["properties"]
                assert any(row["event_type"] == "auth_login_failed" for row in rows)
                assert by_id[valid["eventId"]]["tags"] == valid["properties"]
                assert invalid["eventId"] not in by_id
                for event_id, event in emitted.items():
                    assert event_id in by_id, "A frontend event was not persisted"
                    assert by_id[event_id]["tags"] == event["properties"]
                    assert by_id[event_id]["event_type"] == event["event_type"]
                    assert datetime.fromisoformat(by_id[event_id]["timestamp"]) == datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))

            for filename, data in {
                "mixed-batch-response.json": result,
                "supabase-events.json": rows,
                "verification.json": {
                    "run_id": run_id, "started_at": started_at,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "source": "Unmodified local backoffice and real remote Supabase REST API",
                    "frontend_events_stored": len(emitted), "verified_rows": len(rows),
                    "frontend_acknowledgements": acknowledgements,
                    "frontend_contract_rejections": producer_rejections,
                    "login_http_status": login_http_status,
                    "local_receipt": {
                        "receipt_id": receipt["receipt_id"], "store_id": receipt["store_id"],
                        "sku": receipt["sku"], "received_qty": receipt["received_qty"],
                    },
                    "mixed_batch": result, "duplicate_retry": retry.json(),
                    "outbound_order": "Not implemented in existing backend or backoffice; not fabricated",
                    "screenshot_source": "Live Supabase REST query rendered as an evidence view, not Supabase Studio",
                },
            }.items():
                (output / filename).write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

            priorities = {"inventory_receipt_created": 0, "auth_login_failed": 1, "frontend_page_load_recorded": 2, "navigation_section_viewed": 3}
            display_rows = sorted(rows, key=lambda row: priorities.get(row["event_type"], 4))[:8]
            table_rows = "".join(
                "<tr><td>" + html.escape(row["event_type"]) + "</td><td>"
                + html.escape(row["timestamp"]) + "</td><td>"
                + html.escape(row["service"]) + "</td><td><pre>"
                + html.escape(json.dumps(row["tags"], indent=2, ensure_ascii=True))
                + "</pre></td></tr>" for row in display_rows
            )
            evidence_page = context.new_page()
            evidence_page.set_content(
                "<!doctype html><html lang='es'><meta charset='utf-8'><title>Supabase telemetry evidence</title>"
                "<style>body{margin:32px;color:#17221e;background:#f4f7f5;font:15px sans-serif}"
                "h1{font-size:26px;margin-bottom:8px}p{color:#44584c}table{width:100%;border-collapse:collapse;background:white}"
                "th,td{text-align:left;vertical-align:top;border:1px solid #cad8cf;padding:12px}"
                "th{background:#e0eee5}pre{margin:0;font:12px monospace;white-space:pre-wrap;overflow-wrap:anywhere}"
                "td:first-child{width:260px;overflow-wrap:anywhere}td:nth-child(2){width:220px}footer{margin-top:18px;color:#44584c}</style>"
                "<h1>Supabase / public.telemetry_events</h1>"
                "<p>Consulta real por API REST. Vista de evidencia; no es Supabase Studio.</p>"
                f"<p>Verificacion: {html.escape(started_at)} | Filas comprobadas: {len(rows)} | Run: {run_id}</p>"
                "<table><thead><tr><th>event_type</th><th>timestamp</th><th>service</th><th>tags (JSONB)</th></tr></thead>"
                f"<tbody>{table_rows}</tbody></table>"
                "<footer>Origen: navegacion, recepcion local de desarrollo y login fallido reales del backoffice existente. Sin credenciales en esta evidencia.</footer></html>"
            )
            evidence_page.screenshot(path=str(output / "supabase-events.png"), full_page=True)
            browser.close()
    print(json.dumps({"verified_rows": len(rows), "mixed_batch": result, "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify live telemetry and capture evidence without modifying the frontend")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--ui-base", default="http://localhost:4173")
    parser.add_argument("--output", type=Path, default=SERVICE_DIR / "evidence/telemetry")
    parser.add_argument("--allow-local-receipt", action="store_true", required=True, help="Confirm creation of one 0.1-unit CHICKEN receipt in med-001 in the local development database")
    options = parser.parse_args()
    assert urlsplit(options.api_base).hostname in {"localhost", "127.0.0.1"}, "Only local development API writes are allowed"
    verify(options.api_base.rstrip("/"), options.ui_base.rstrip("/"), options.output)