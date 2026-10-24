"""HTTP interface for Brasaland's internal knowledge assistant."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from data.pipelines.rag import query


logger = logging.getLogger(__name__)
knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question must not be blank")
        return cleaned


class KnowledgeAnswer(BaseModel):
    answer: str


@knowledge_router.post("/query", response_model=KnowledgeAnswer)
def query_knowledge(request: KnowledgeQuery) -> KnowledgeAnswer:
    try:
        return KnowledgeAnswer(answer=query(request.question))
    except Exception as error:
        logger.exception("Knowledge query failed")
        raise HTTPException(
            status_code=503,
            detail="El asistente de conocimiento no esta disponible.",
        ) from error
