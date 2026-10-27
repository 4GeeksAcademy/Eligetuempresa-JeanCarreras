"""Document preparation and Qdrant indexing for Brasaland's knowledge base."""

import os
import re
import uuid
from pathlib import Path

from openai import OpenAI
from qdrant_client import QdrantClient, models


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_DIR = REPOSITORY_ROOT / "docs" / "company-knowledge-base"
COLLECTION_NAME = os.getenv("RAG_QDRANT_COLLECTION", "brasaland_knowledge_base")
COLLECTION_NAMESPACE = uuid.UUID("ed96e1ee-849d-4ebd-96fd-96d626073d94")


def _llm_client() -> OpenAI:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("Configura LLM_API_KEY para acceder al proveedor de modelos.")
    return OpenAI(api_key=api_key, base_url=os.getenv("LLM_API_BASE_URL"))


def _qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=os.getenv("RAG_QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("RAG_QDRANT_API_KEY"),
    )


def embed(text: str) -> list[float]:
    """Embed text with the dedicated model configured for retrieval."""
    model = os.getenv("RAG_EMBEDDING_MODEL")
    if not model:
        raise RuntimeError("Configura RAG_EMBEDDING_MODEL con un modelo de embeddings.")
    response = _llm_client().embeddings.create(model=model, input=text)
    return response.data[0].embedding


def _markdown_sections(text: str, source_name: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading_stack: list[tuple[int, str]] = []
    current_heading = source_name
    current_lines: list[str] = []

    def save_section() -> None:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_heading, f"{current_heading}\n\n{body}"))

    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match:
            save_section()
            level = len(match.group(1))
            heading_stack = [entry for entry in heading_stack if entry[0] < level]
            heading_stack.append((level, match.group(2).strip()))
            current_heading = " > ".join(title for _, title in heading_stack)
            current_lines = []
        else:
            current_lines.append(line)

    save_section()
    return sections


def _load_chunks(corpus_dir: Path) -> list[dict]:
    chunks: list[dict] = []
    documents = sorted(
        path for path in corpus_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}
    )

    for document in documents:
        source_document = document.relative_to(corpus_dir).as_posix()
        content = document.read_text(encoding="utf-8").strip()
        if not content:
            continue
        if document.suffix.lower() == ".md":
            sections = _markdown_sections(content, document.stem)
        else:
            sections = [(document.stem, content)]

        language = "en" if re.search(r"\.en(?:\.|$)", document.name) else "es"
        for chunk_index, (section, chunk_text) in enumerate(sections):
            chunks.append(
                {
                    "source_document": source_document,
                    "section": section,
                    "company": "Brasaland",
                    "language": language,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                }
            )
    return chunks


def setup(corpus_dir: Path | None = None) -> int:
    """Recreate the development collection from semantic document sections."""
    corpus_path = corpus_dir or DEFAULT_CORPUS_DIR
    if not corpus_path.is_dir():
        raise FileNotFoundError(f"No existe el corpus de conocimiento: {corpus_path}")

    chunks = _load_chunks(corpus_path)
    if not chunks:
        raise ValueError(f"No hay documentos Markdown o texto para indexar en {corpus_path}")

    vectors = [embed(chunk["text"]) for chunk in chunks]
    client = _qdrant_client()
    if client.collection_exists(collection_name=COLLECTION_NAME):
        client.delete_collection(collection_name=COLLECTION_NAME)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE),
    )
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=str(uuid.uuid5(COLLECTION_NAMESPACE, f"{chunk['source_document']}:{chunk['chunk_index']}")),
                vector=vector,
                payload=chunk,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ],
    )
    return len(chunks)