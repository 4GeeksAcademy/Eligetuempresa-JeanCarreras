import secrets

import pytest
from fastapi.testclient import TestClient

from src import main
from src.brasaland_api import knowledge


@pytest.fixture
def client(monkeypatch):
    token = secrets.token_hex(32)
    monkeypatch.setenv("BRASALAND_OPERATIONS_TOKEN", token)
    return TestClient(main.app, headers={"X-API-Role": "operations", "X-API-Token": token})


def test_knowledge_query_returns_only_generated_answer(monkeypatch, client):
    monkeypatch.setattr(knowledge, "query", lambda question: "Respuesta generada.")

    response = client.post("/knowledge/query", json={"question": "¿Cómo funciona Oro?"})

    assert response.status_code == 200
    assert response.json() == {"answer": "Respuesta generada."}


def test_knowledge_query_hides_pipeline_failures(monkeypatch, client):
    def fail_query(_: str) -> str:
        raise RuntimeError("internal retrieval details")

    monkeypatch.setattr(knowledge, "query", fail_query)

    response = client.post("/knowledge/query", json={"question": "Pregunta válida"})

    assert response.status_code == 503
    assert "internal retrieval details" not in response.text
    assert set(response.json()) == {"detail"}


def test_knowledge_query_rejects_blank_questions(client):
    response = client.post("/knowledge/query", json={"question": "   "})

    assert response.status_code == 422
