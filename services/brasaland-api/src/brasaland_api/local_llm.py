import base64
import hmac
import os
import struct
from threading import Lock
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastembed import TextEmbedding
from pydantic import BaseModel, ConfigDict, Field, field_validator


EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION = 384
app = FastAPI(title="Brasaland local embeddings and Groq gateway")
_model: TextEmbedding | None = None
_model_lock = Lock()


def authenticate(authorization: str | None = Header(default=None)) -> None:
    secret = os.environ.get("BRASALAND_LOCAL_LLM_KEY", "")
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail="Configura una clave local de al menos 32 caracteres.")
    supplied = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
    if not hmac.compare_digest(supplied.encode(), secret.encode()):
        raise HTTPException(status_code=401, detail="Clave local no valida.")


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: Literal["sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"]
    input: str | list[str]
    encoding_format: Literal["float", "base64"] = "float"
    dimensions: Literal[384] | None = None
    user: str | None = Field(default=None, max_length=200)

    @field_validator("input")
    @classmethod
    def validate_input(cls, value: str | list[str]) -> str | list[str]:
        texts = [value] if isinstance(value, str) else value
        if not 1 <= len(texts) <= 32 or any(not text.strip() or len(text) > 20000 for text in texts):
            raise ValueError("Indica de 1 a 32 textos no vacios de hasta 20000 caracteres.")
        return value


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = Field(min_length=1, max_length=200)
    messages: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    stream: Literal[False] = False


def embed_texts(texts: list[str]) -> list[list[float]]:
    global _model
    with _model_lock:
        if _model is None:
            _model = TextEmbedding(
                model_name=EMBEDDING_MODEL,
                cache_dir=os.getenv("BRASALAND_EMBED_CACHE"),
                threads=2,
                providers=["CPUExecutionProvider"],
            )
        return [vector.tolist() for vector in _model.embed(texts)]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "embedding_model": EMBEDDING_MODEL, "dimensions": EMBEDDING_DIMENSION, "model_loaded": _model is not None}


@app.get("/v1/models", dependencies=[Depends(authenticate)])
def models() -> dict:
    return {"object": "list", "data": [{"id": EMBEDDING_MODEL, "object": "model", "owned_by": "local"}]}


@app.post("/v1/embeddings", dependencies=[Depends(authenticate)])
def embeddings(request: EmbeddingRequest) -> dict:
    texts = [request.input] if isinstance(request.input, str) else request.input
    try:
        vectors = embed_texts(texts)
    except Exception:
        raise HTTPException(status_code=503, detail="No se pudo cargar o ejecutar el modelo local.") from None
    data = []
    for index, vector in enumerate(vectors):
        if len(vector) != EMBEDDING_DIMENSION:
            raise HTTPException(status_code=503, detail="Dimension de embedding inesperada.")
        encoded = base64.b64encode(struct.pack(f"<{EMBEDDING_DIMENSION}f", *vector)).decode("ascii")
        data.append({"object": "embedding", "index": index, "embedding": encoded if request.encoding_format == "base64" else vector})
    return {"object": "list", "data": data, "model": EMBEDDING_MODEL}


@app.post("/v1/chat/completions", dependencies=[Depends(authenticate)])
def chat_completions(request: ChatRequest) -> dict:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="Configura GROQ_API_KEY para generar respuestas.")
    if request.model == EMBEDDING_MODEL:
        raise HTTPException(status_code=422, detail="Selecciona un modelo de generacion de Groq.")
    payload = request.model_dump(exclude_none=True)
    configured_model = os.environ.get("GROQ_GENERATION_MODEL", "").strip()
    if configured_model:
        payload["model"] = configured_model
    try:
        with httpx.Client(timeout=60, follow_redirects=False, trust_env=False) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=503, detail="Groq no pudo completar la solicitud.") from None