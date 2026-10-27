"""Semantic chunking, embeddings, and Qdrant indexing for Brasaland."""

import os
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient, models


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_DIR = REPOSITORY_ROOT / "docs" / "company-knowledge-base"
COLLECTION_NAME = "brasaland_knowledge"
COLLECTION_NAMESPACE = uuid.UUID("ed96e1ee-849d-4ebd-96fd-96d626073d94")
MIN_CHUNKS_PER_DOCUMENT = 3
SOURCE_DOCUMENTS = {
    "brasaland-loyalty-program.es.md": "loyalty-program",
    "brasaland-waste-protocol.es.md": "waste-protocol",
    "brasaland-menu-allergens.es.md": "menu-allergens",
    "brasaland-supplier-ordering.es.md": "supplier-ordering",
}

load_dotenv(REPOSITORY_ROOT / "services" / "brasaland-api" / ".env")


def _model_names() -> tuple[str, str]:
    embedding_model = os.getenv("RAG_EMBEDDING_MODEL", "").strip()
    generation_model = os.getenv("RAG_GENERATION_MODEL", "").strip()
    if not embedding_model or not generation_model:
        raise RuntimeError(
            "Configura RAG_EMBEDDING_MODEL y RAG_GENERATION_MODEL en el entorno."
        )
    if embedding_model == generation_model:
        raise RuntimeError("Los modelos de embeddings y generacion deben ser distintos.")
    return embedding_model, generation_model


def _llm_client() -> OpenAI:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("Configura LLM_API_KEY para acceder al proveedor de modelos.")
    return OpenAI(api_key=api_key, base_url=os.getenv("LLM_API_BASE_URL") or None)


def _qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=os.getenv("RAG_QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("RAG_QDRANT_API_KEY") or None,
    )


def embed(text: str) -> list[float]:
    """Return a vector from the dedicated embeddings model."""
    embedding_model, _ = _model_names()
    result = _llm_client().embeddings.create(model=embedding_model, input=text)
    vector = result.data[0].embedding
    if not vector or any(not isinstance(value, (float, int)) for value in vector):
        raise ValueError("El proveedor devolvio un embedding vacio o invalido.")
    return [float(value) for value in vector]


def _semantic_chunks(markdown: str, fallback_section: str) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    heading_stack: list[tuple[int, str]] = []
    current_section = fallback_section
    block_lines: list[str] = []

    def save_block() -> None:
        body = "\n".join(block_lines).strip()
        if body:
            chunks.append((current_section, f"{current_section}\n\n{body}"))

    for line in markdown.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            save_block()
            block_lines.clear()
            level = len(heading.group(1))
            heading_stack = [item for item in heading_stack if item[0] < level]
            heading_stack.append((level, heading.group(2).strip()))
            current_section = " > ".join(title for _, title in heading_stack)
        elif line.strip():
            block_lines.append(line.rstrip())
        else:
            save_block()
            block_lines.clear()

    save_block()
    return chunks


def _load_chunks(corpus_dir: Path) -> list[dict]:
    missing = [name for name in SOURCE_DOCUMENTS if not (corpus_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Faltan documentos del BRIEFING en {corpus_dir}: {', '.join(missing)}"
        )

    chunks: list[dict] = []
    for filename, source_document in SOURCE_DOCUMENTS.items():
        document = corpus_dir / filename
        markdown = document.read_text(encoding="utf-8").strip()
        if not markdown:
            raise ValueError(f"El documento fuente esta vacio: {filename}")
        sections = _semantic_chunks(markdown, source_document)
        if len(sections) < MIN_CHUNKS_PER_DOCUMENT:
            raise ValueError(
                f"{filename} debe producir al menos {MIN_CHUNKS_PER_DOCUMENT} chunks; "
                f"produjo {len(sections)}"
            )

        for chunk_index, (section, text) in enumerate(sections):
            chunks.append(
                {
                    "source_document": source_document,
                    "section": section,
                    "company": "brasaland",
                    "language": "es",
                    "chunk_index": chunk_index,
                    "text": text,
                }
            )
    return chunks


def setup(corpus_dir: Path | None = None) -> int:
    """Recreate the development collection from the official semantic corpus."""
    corpus_path = Path(corpus_dir) if corpus_dir else DEFAULT_CORPUS_DIR
    if not corpus_path.is_dir():
        raise FileNotFoundError(f"No existe el corpus de conocimiento: {corpus_path}")

    chunks = _load_chunks(corpus_path)
    vectors = [embed(chunk["text"]) for chunk in chunks]
    vector_size = len(vectors[0])
    if vector_size == 0 or any(len(vector) != vector_size for vector in vectors):
        raise ValueError("Los embeddings deben tener una dimension constante y no vacia.")

    client = _qdrant_client()
    if client.collection_exists(collection_name=COLLECTION_NAME):
        client.delete_collection(collection_name=COLLECTION_NAME)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
    )
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=str(
                    uuid.uuid5(
                        COLLECTION_NAMESPACE,
                        f"{chunk['source_document']}:{chunk['chunk_index']}",
                    )
                ),
                vector=vector,
                payload=chunk,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ],
    )
    return len(chunks)
