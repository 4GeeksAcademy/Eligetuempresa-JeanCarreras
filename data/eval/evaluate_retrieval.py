"""Measure Recall@3 for the Brasaland knowledge-base evaluation questions."""

import json
import os
import re
from pathlib import Path

from data.pipelines.rag import retrieve


QUERY_FILE = Path(__file__).with_name("test-queries.json")
MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.35"))


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).casefold().strip()


def main() -> int:
    queries = json.loads(QUERY_FILE.read_text(encoding="utf-8"))
    hits = 0
    for item in queries:
        candidates = retrieve(item["question"], k=3, min_score=MIN_SCORE)
        expected_source = item["expected_source_document"]
        expected_text = normalize(item["expected_chunk_text"])
        found = any(
            result.get("source_document") == expected_source
            and expected_text in normalize(result.get("text", ""))
            for result in candidates
        )
        hits += int(found)
        print(f"{'HIT' if found else 'MISS'}: {item['question']}")

    recall = hits / len(queries) if queries else 0.0
    print(f"Recall@3: {hits}/{len(queries)} = {recall:.1%} (umbral {MIN_SCORE:.2f})")
    return 0 if recall >= 0.8 else 1


if __name__ == "__main__":
    raise SystemExit(main())
