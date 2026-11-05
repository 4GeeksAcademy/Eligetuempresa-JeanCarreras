"""HTTP interface for Brasaland's internal knowledge assistant."""

import hashlib
import json
import logging
from threading import BoundedSemaphore

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from data.pipelines.rag import query
from .auth import require_roles


logger = logging.getLogger(__name__)
_query_slots = BoundedSemaphore(2)
knowledge_router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    dependencies=[Depends(require_roles({"admin", "manager", "operations", "executive"}))],
)


class KnowledgeQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        return safe_text(value, 2000)


class KnowledgeAnswer(BaseModel):
    answer: str


@knowledge_router.post("/query", response_model=KnowledgeAnswer)
def query_knowledge(request: KnowledgeQuery) -> KnowledgeAnswer:
    if not _query_slots.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="El asistente esta ocupado. Intenta mas tarde.")
    try:
        return KnowledgeAnswer(answer=query(request.question))
    except Exception as error:
        logger.warning("Knowledge query failed: %s", type(error).__name__)
        raise HTTPException(
            status_code=503,
            detail="El asistente de conocimiento no esta disponible.",
        ) from error
    finally:
        _query_slots.release()
