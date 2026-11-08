from datetime import datetime, timezone
from threading import RLock
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from tinydb import Query as DocumentQuery

from .auth import get_db, require_roles


talent_router = APIRouter(
    prefix="/api/v1/talent", tags=["talent"],
    dependencies=[Depends(require_roles({"admin", "manager"}))],
)
_lock = RLock()


class CandidateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=1, max_length=200)
    email: str = Field(max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str = Field(max_length=50)
    position: str = Field(min_length=1, max_length=200)
    linkedin_url: str | None = Field(default=None, max_length=2048, pattern=r"^https?://")
    cv_url: str | None = Field(default=None, max_length=2048, pattern=r"^https?://")
    experience_years: float = Field(ge=0, le=80)


class CandidatePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["new", "in_progress", "on_hold", "closed"] | None = None
    stage: Literal["sourced", "review", "screening", "interview", "assessment", "offer", "hired", "rejected"] | None = None


class NoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=10000)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def candidate(record_id: str) -> dict:
    record = get_db().table("talent_candidates").get(DocumentQuery().id == record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    return {**record, "notes_count": len(get_db().table("talent_notes").search(DocumentQuery().record_id == record_id))}


@talent_router.get("/records")
def list_records(page: int = Query(default=1, ge=1), limit: int = Query(default=50, ge=1, le=100)) -> dict:
    with _lock:
        records = sorted(get_db().table("talent_candidates").all(), key=lambda record: record["applied_at"], reverse=True)
        offset = (page - 1) * limit
        return {"data": [candidate(record["id"]) for record in records[offset:offset + limit]], "total": len(records), "page": page, "limit": limit}


@talent_router.post("/records", status_code=201)
def create_record(payload: CandidateInput) -> dict:
    with _lock:
        record_id = str(uuid4())
        now = timestamp()
        get_db().table("talent_candidates").insert({
            **payload.model_dump(), "id": record_id, "status": "new", "stage": "sourced",
            "applied_at": now, "updated_at": now,
        })
        return candidate(record_id)


@talent_router.get("/records/{record_id}")
def get_record(record_id: str) -> dict:
    with _lock:
        return candidate(record_id)


@talent_router.put("/records/{record_id}")
def update_record(record_id: str, payload: CandidateInput) -> dict:
    with _lock:
        candidate(record_id)
        get_db().table("talent_candidates").update({**payload.model_dump(), "updated_at": timestamp()}, DocumentQuery().id == record_id)
        return candidate(record_id)


@talent_router.patch("/records/{record_id}")
def patch_record(record_id: str, payload: CandidatePatch) -> dict:
    with _lock:
        candidate(record_id)
        changes = payload.model_dump(exclude_none=True)
        if not changes:
            raise HTTPException(status_code=422, detail="Indica un estado o una etapa")
        get_db().table("talent_candidates").update({**changes, "updated_at": timestamp()}, DocumentQuery().id == record_id)
        return candidate(record_id)


@talent_router.delete("/records/{record_id}", status_code=204)
def delete_record(record_id: str) -> Response:
    with _lock:
        candidate(record_id)
        get_db().table("talent_notes").remove(DocumentQuery().record_id == record_id)
        get_db().table("talent_candidates").remove(DocumentQuery().id == record_id)
        return Response(status_code=204)


@talent_router.get("/records/{record_id}/notes")
def list_notes(record_id: str) -> list[dict]:
    with _lock:
        candidate(record_id)
        return sorted(get_db().table("talent_notes").search(DocumentQuery().record_id == record_id), key=lambda note: note["created_at"])


@talent_router.post("/records/{record_id}/notes", status_code=201)
def create_note(record_id: str, payload: NoteInput) -> dict:
    with _lock:
        candidate(record_id)
        note = {"id": str(uuid4()), "record_id": record_id, "content": payload.content, "created_at": timestamp()}
        get_db().table("talent_notes").insert(note)
        get_db().table("talent_candidates").update({"updated_at": timestamp()}, DocumentQuery().id == record_id)
        return note


@talent_router.delete("/records/{record_id}/notes/{note_id}", status_code=204)
def delete_note(record_id: str, note_id: str) -> Response:
    with _lock:
        candidate(record_id)
        condition = (DocumentQuery().id == note_id) & (DocumentQuery().record_id == record_id)
        if not get_db().table("talent_notes").contains(condition):
            raise HTTPException(status_code=404, detail="Nota no encontrada")
        get_db().table("talent_notes").remove(condition)
        get_db().table("talent_candidates").update({"updated_at": timestamp()}, DocumentQuery().id == record_id)
        return Response(status_code=204)