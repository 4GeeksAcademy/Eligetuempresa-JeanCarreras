#!/usr/bin/env python3
"""Reprocesa manualmente un ticket RFP que quedó con error técnico."""

import argparse
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "services" / "brasaland-api" / "src"))

from brasaland_api.rfp_intake import RAW_RFP_DIR, SupabaseRfpRepository
from data.pipelines.rfp_intake import process_rfp_ticket


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticket_id")
    parser.add_argument(
        "--confirm-stale",
        action="store_true",
        help="autoriza reintentar un ticket analizando sin error registrado",
    )
    args = parser.parse_args()

    ticket_id = args.ticket_id
    repository = SupabaseRfpRepository()
    ticket = repository.get_ticket(ticket_id)
    if ticket is None:
        print("No existe ese ticket RFP", file=sys.stderr)
        return 1
    if ticket["status"] != "analizando":
        print("Solo se pueden reprocesar tickets en estado analizando", file=sys.stderr)
        return 1
    if not ticket.get("processing_error") and not args.confirm_stale:
        print(
            "No hay error registrado; confirma que no hay un worker activo con --confirm-stale",
            file=sys.stderr,
        )
        return 1

    pdf_path = Path(ticket["pdf_path"]).resolve()
    if not pdf_path.is_relative_to(RAW_RFP_DIR.resolve()) or not pdf_path.is_file():
        print("El PDF del ticket no esta disponible en data/raw/rfp", file=sys.stderr)
        return 1

    process_rfp_ticket(ticket_id, str(pdf_path), repository)
    updated = repository.get_ticket(ticket_id)
    if updated and not updated.get("processing_error"):
        print(f"Ticket reprocesado: {updated['status']}")
        return 0
    print("El reproceso termino con error; consulta processing_error en el ticket", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())