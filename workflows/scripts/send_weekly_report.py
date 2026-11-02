#!/usr/bin/env python3
"""Envia el reporte semanal de Brasaland por Slack webhook y/o email SMTP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path
from urllib import request

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "brasaland-api"))
from src.brasaland_api.security import consume_approval


def send_to_slack(webhook_url: str, report_text: str, title: str) -> None:
    payload = {
        "text": f"{title}\n\n```{report_text[:3500]}```",
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=15):
        return


def send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    sender: str,
    recipients: list[str],
    subject: str,
    body: str,
) -> None:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enviar reporte semanal Brasaland")
    parser.add_argument("--report-path", required=True, help="Ruta al archivo markdown del reporte")
    parser.add_argument("--title", default="Brasaland - Reporte Ejecutivo Semanal", help="Titulo del envio")
    parser.add_argument("--approval-manifest", action="store_true", help="Mostrar payload para aprobacion sin enviar")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report_path)
    if not report_path.exists():
        print("Error: no existe el archivo de reporte indicado.", file=sys.stderr)
        return 1

    try:
        report_text = report_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        print("Error: no se pudo leer el archivo de reporte.", file=sys.stderr)
        return 1

    slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_SENDER", smtp_user).strip()
    recipient_raw = os.getenv("REPORT_RECIPIENTS", "").strip()
    recipients = [item.strip() for item in recipient_raw.split(",") if item.strip()]
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        manifest = {
            "report_sha256": hashlib.sha256(report_text.encode("utf-8")).hexdigest(),
            "title": args.title,
            "slack_destination_sha256": hashlib.sha256(slack_webhook.encode()).hexdigest() if slack_webhook else None,
            "smtp_host": smtp_host, "smtp_port": smtp_port,
            "sender": sender, "recipients": recipients,
        }
        if args.approval_manifest:
            print(json.dumps(manifest, sort_keys=True))
            return 0
        if not slack_webhook and not (smtp_host and smtp_user and smtp_password and recipients):
            print("Error: no hay destinos de envio configurados.", file=sys.stderr)
            return 1
        consume_approval(
            os.getenv("REPORT_APPROVAL_TOKEN"), os.getenv("REPORT_APPROVER_ID", ""),
            "POST", "workflow:weekly-report", manifest,
        )
    except (PermissionError, ValueError, RuntimeError, OSError):
        print("Error: se requiere aprobacion humana vigente para este reporte y sus destinos.", file=sys.stderr)
        return 1

    delivery_failed = False
    if slack_webhook:
        try:
            send_to_slack(slack_webhook, report_text, args.title)
            print("Reporte enviado a Slack")
        except Exception:
            print("Error: no se pudo enviar el reporte a Slack.", file=sys.stderr)
            delivery_failed = True

    if smtp_host and smtp_user and smtp_password and recipient_raw:
        if recipients:
            try:
                send_email(
                    smtp_host=smtp_host,
                    smtp_port=smtp_port,
                    smtp_user=smtp_user,
                    smtp_password=smtp_password,
                    sender=sender,
                    recipients=recipients,
                    subject=args.title,
                    body=report_text,
                )
                print("Reporte enviado por email")
            except (OSError, ValueError, smtplib.SMTPException):
                print("Error: no se pudo enviar el reporte por email.", file=sys.stderr)
                delivery_failed = True

    return 1 if delivery_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
