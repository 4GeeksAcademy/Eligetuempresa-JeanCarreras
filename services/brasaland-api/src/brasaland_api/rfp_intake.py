import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile

from data.pipelines.rfp_intake import process_rfp_ticket
from .auth import UserInDB, get_current_user


logger = logging.getLogger(__name__)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
rfp_intake_router = APIRouter(prefix="/rfp-intake", tags=["rfp-intake"])
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
RAW_RFP_DIR = REPOSITORY_ROOT / "data" / "raw" / "rfp"
MAX_PDF_BYTES = 25 * 1024 * 1024


class SupabaseRfpRepository:
    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        body: Any = None,
        prefer: str = "return=representation",
    ) -> Any:
        if not self.url or not self.key:
            raise RuntimeError("El almacenamiento de RFP requiere Supabase configurado")
        response = httpx.request(
            method,
            f"{self.url}/rest/v1/{table}",
            params=params,
            headers={
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "Prefer": prefer,
            },
            json=body,
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json() if response.content else None

    def create_ticket(self, ticket_id: str, filename: str, pdf_path: str) -> None:
        self._request(
            "POST",
            "rfp_tickets",
            body={
                "id": ticket_id,
                "status": "analizando",
                "original_filename": filename,
                "pdf_path": pdf_path,
            },
        )

    def save_document_analysis(
        self,
        ticket_id: str,
        markdown_path: str,
        metadata: dict[str, Any],
        readability: dict[str, Any],
        classification: dict[str, Any],
    ) -> None:
        self._request(
            "POST",
            "rfp_documents",
            params={"on_conflict": "ticket_id"},
            body={
                "ticket_id": ticket_id,
                "markdown_path": markdown_path,
                "metadata": metadata,
                "readability_metrics": readability,
                "classification": classification,
            },
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def save_department_sections(self, ticket_id: str, sections: list[dict[str, Any]]) -> None:
        self._request(
            "DELETE",
            "rfp_department_sections",
            params={"ticket_id": f"eq.{ticket_id}"},
            prefer="return=minimal",
        )
        if sections:
            rows = [
                {
                    "ticket_id": ticket_id,
                    "department": section["department"],
                    "contact": section["contact"],
                    "key_aspects": section["key_aspects"],
                    "source_excerpt": section["source_excerpt"],
                }
                for section in sections
            ]
            self._request(
                "POST", "rfp_department_sections", body=rows, prefer="return=minimal"
            )

    def complete_ticket(self, ticket_id: str, handoff: dict[str, Any]) -> None:
        persisted_handoff = {**handoff, "ticket_id": ticket_id}
        self._request(
            "PATCH",
            "rfp_tickets",
            params={"id": f"eq.{ticket_id}"},
            body={
                "status": "analisis_completo",
                "handoff": persisted_handoff,
                "processing_error": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            prefer="return=minimal",
        )

    def discard_ticket(self, ticket_id: str, reason: str) -> None:
        self._request(
            "PATCH",
            "rfp_tickets",
            params={"id": f"eq.{ticket_id}"},
            body={
                "status": "descartado",
                "classification_reason": reason,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            prefer="return=minimal",
        )

    def record_processing_error(self, ticket_id: str, message: str) -> None:
        try:
            self._request(
                "PATCH",
                "rfp_tickets",
                params={"id": f"eq.{ticket_id}"},
                body={
                    "processing_error": message,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                prefer="return=minimal",
            )
        except Exception:
            logger.exception("No se pudo registrar el error del ticket RFP %s", ticket_id)

    def list_tickets(self, limit: int) -> list[dict[str, Any]]:
        result = self._request(
            "GET",
            "rfp_tickets",
            params={
                "select": "id,status,original_filename,created_at,processing_error",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
        return result if isinstance(result, list) else []

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            "rfp_tickets",
            params={"id": f"eq.{ticket_id}", "limit": "1"},
        )
        if not isinstance(rows, list) or not rows:
            return None
        ticket = rows[0]
        documents = self._request(
            "GET",
            "rfp_documents",
            params={"ticket_id": f"eq.{ticket_id}", "limit": "1"},
        )
        sections = self._request(
            "GET",
            "rfp_department_sections",
            params={"ticket_id": f"eq.{ticket_id}", "order": "department.asc"},
        )
        ticket["document"] = documents[0] if isinstance(documents, list) and documents else None
        ticket["department_sections"] = sections if isinstance(sections, list) else []
        return ticket


@rfp_intake_router.post("/tickets", status_code=202)
async def receive_rfp(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _: UserInDB = Depends(get_current_user),
) -> dict[str, str]:
    filename = Path(file.filename or "rfp.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Solo se aceptan archivos PDF")
    content = await file.read(MAX_PDF_BYTES + 1)
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="El PDF supera el limite de 25 MB")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="El archivo no contiene un PDF valido")

    ticket_id = str(uuid4())
    RAW_RFP_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = RAW_RFP_DIR / f"{ticket_id}.pdf"
    pdf_path.write_bytes(content)
    repository = SupabaseRfpRepository()
    try:
        repository.create_ticket(ticket_id, filename[:255], str(pdf_path))
    except Exception as error:
        pdf_path.unlink(missing_ok=True)
        logger.exception("No se pudo crear el ticket de RFP")
        raise HTTPException(status_code=503, detail="No se pudo guardar el ticket") from error

    background_tasks.add_task(process_rfp_ticket, ticket_id, str(pdf_path), repository)
    return {"ticket_id": ticket_id, "status": "analizando"}


@rfp_intake_router.get("/tickets")
def list_rfp_tickets(
    limit: int = Query(default=30, ge=1, le=100),
    _: UserInDB = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        return SupabaseRfpRepository().list_tickets(limit)
    except Exception as error:
        logger.exception("No se pudieron consultar los tickets RFP")
        raise HTTPException(status_code=503, detail="No se pudo consultar la bandeja RFP") from error


@rfp_intake_router.get("/tickets/{ticket_id}")
def get_rfp_ticket(
    ticket_id: UUID,
    _: UserInDB = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        ticket = SupabaseRfpRepository().get_ticket(str(ticket_id))
    except Exception as error:
        logger.exception("No se pudo consultar el ticket RFP %s", ticket_id)
        raise HTTPException(status_code=503, detail="No se pudo consultar el ticket") from error
    if ticket is None:
        raise HTTPException(status_code=404, detail="No existe ese ticket RFP")
    ticket.pop("pdf_path", None)
    if ticket.get("document"):
        ticket["document"].pop("markdown_path", None)
    return ticket