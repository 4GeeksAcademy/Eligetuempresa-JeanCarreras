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

    # ------------------------------------------------------------------
    # Part 2: Response generation methods
    # ------------------------------------------------------------------

    def update_ticket_status(self, ticket_id: str, status: str) -> None:
        valid_statuses = {
            "generando_borrador", "en_evaluacion", "needs_human_review",
        }
        if status not in valid_statuses:
            raise ValueError(f"Estado no valido: {status}")
        self._request(
            "PATCH",
            "rfp_tickets",
            params={"id": f"eq.{ticket_id}"},
            body={
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            prefer="return=minimal",
        )

    def save_response_draft(
        self, ticket_id: str, department: str, iteration: int, content: str
    ) -> None:
        self._request(
            "POST",
            "rfp_response_drafts",
            params={
                "on_conflict": "ticket_id,department,iteration",
            },
            body={
                "ticket_id": ticket_id,
                "department": department,
                "iteration": iteration,
                "content": content,
            },
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def save_evaluation_result(
        self, ticket_id: str, department: str, iteration: int, evaluation: dict[str, Any]
    ) -> None:
        self._request(
            "POST",
            "rfp_evaluation_results",
            params={
                "on_conflict": "ticket_id,department,iteration",
            },
            body={
                "ticket_id": ticket_id,
                "department": department,
                "iteration": iteration,
                "overall_pass": evaluation.get("overall_pass", False),
                "readability": evaluation.get("readability", {}),
                "relevance": evaluation.get("relevance", {}),
                "compliance": evaluation.get("compliance", {}),
                "feedback_for_generator": evaluation.get("feedback_for_generator", ""),
            },
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def save_response_handoff(self, ticket_id: str, handoff: dict[str, Any]) -> None:
        self._request(
            "POST",
            "rfp_response_handoff",
            params={"on_conflict": "ticket_id"},
            body={
                "ticket_id": ticket_id,
                "handoff": handoff,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def get_response_handoff(self, ticket_id: str) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            "rfp_response_handoff",
            params={"ticket_id": f"eq.{ticket_id}", "limit": "1"},
        )
        if isinstance(rows, list) and rows:
            return rows[0]
        return None

    def get_response_drafts(self, ticket_id: str) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "rfp_response_drafts",
            params={
                "ticket_id": f"eq.{ticket_id}",
                "order": "department.asc,iteration.desc",
            },
        )
        return rows if isinstance(rows, list) else []

    def get_evaluation_results(self, ticket_id: str) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "rfp_evaluation_results",
            params={
                "ticket_id": f"eq.{ticket_id}",
                "order": "department.asc,iteration.desc",
            },
        )
        return rows if isinstance(rows, list) else []

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


# ------------------------------------------------------------------
# Part 2: Response generation & evaluation endpoints
# ------------------------------------------------------------------


@rfp_intake_router.post("/tickets/{ticket_id}/generate-response", status_code=202)
async def trigger_response_generation(
    ticket_id: UUID,
    background_tasks: BackgroundTasks,
    _: UserInDB = Depends(get_current_user),
) -> dict[str, str]:
    """Trigger Part 2 response generation for a completed analysis ticket.

    Consumes the handoff from Part 1 and runs generator-evaluator loop per department.
    """
    repository = SupabaseRfpRepository()
    ticket = repository.get_ticket(str(ticket_id))
    if ticket is None:
        raise HTTPException(status_code=404, detail="No existe ese ticket RFP")

    if ticket["status"] != "analisis_completo":
        raise HTTPException(
            status_code=409,
            detail=f"El ticket debe estar en estado 'analisis_completo' para generar respuesta. Estado actual: {ticket['status']}",
        )

    handoff = ticket.get("handoff")
    if not handoff:
        raise HTTPException(
            status_code=400,
            detail="El ticket no tiene handoff de la Parte 1. No se puede generar respuesta.",
        )

    from data.pipelines.rfp_response import process_rfp_response

    background_tasks.add_task(
        process_rfp_response,
        str(ticket_id),
        handoff,
        SupabaseRfpRepository(),
    )
    return {"ticket_id": str(ticket_id), "status": "generando_borrador"}


@rfp_intake_router.get("/tickets/{ticket_id}/response")
def get_rfp_response(
    ticket_id: UUID,
    _: UserInDB = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the full response generation result for a ticket (Part 2 handoff)."""
    repository = SupabaseRfpRepository()
    ticket = repository.get_ticket(str(ticket_id))
    if ticket is None:
        raise HTTPException(status_code=404, detail="No existe ese ticket RFP")

    response_handoff = repository.get_response_handoff(str(ticket_id))
    drafts = repository.get_response_drafts(str(ticket_id))
    evaluations = repository.get_evaluation_results(str(ticket_id))

    return {
        "ticket_id": str(ticket_id),
        "status": ticket.get("status"),
        "response_handoff": response_handoff.get("handoff") if response_handoff else None,
        "drafts": drafts,
        "evaluation_results": evaluations,
    }