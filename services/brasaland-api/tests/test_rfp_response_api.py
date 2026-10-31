"""Tests para los endpoints de generacion de respuesta RFP (Parte 2)."""

from fastapi.testclient import TestClient
from unittest.mock import ANY

from src import main
from src.brasaland_api import auth, rfp_intake


client = TestClient(main.app)


class InMemoryResponseRepository:
    """Simula el repositorio sin Supabase para pruebas de API."""

    def __init__(self) -> None:
        self.tickets: dict[str, dict] = {}
        self.drafts: list[dict] = []
        self.evaluations: list[dict] = []
        self.handoffs: dict[str, dict] = {}

    def get_ticket(self, ticket_id: str) -> dict | None:
        return self.tickets.get(ticket_id)

    def update_ticket_status(self, ticket_id: str, status: str) -> None:
        if ticket_id in self.tickets:
            self.tickets[ticket_id]["status"] = status

    def save_response_draft(self, ticket_id: str, department: str, iteration: int, content: str) -> None:
        self.drafts.append({
            "ticket_id": ticket_id,
            "department": department,
            "iteration": iteration,
            "content": content,
        })

    def save_evaluation_result(self, ticket_id: str, department: str, iteration: int, evaluation: dict) -> None:
        self.evaluations.append({
            "ticket_id": ticket_id,
            "department": department,
            "iteration": iteration,
            **evaluation,
        })

    def save_response_handoff(self, ticket_id: str, handoff: dict) -> None:
        self.handoffs[ticket_id] = handoff

    def get_response_handoff(self, ticket_id: str) -> dict | None:
        handoff = self.handoffs.get(ticket_id)
        return {"handoff": handoff} if handoff else None

    def get_response_drafts(self, ticket_id: str) -> list[dict]:
        return [d for d in self.drafts if d["ticket_id"] == ticket_id]

    def get_evaluation_results(self, ticket_id: str) -> list[dict]:
        return [e for e in self.evaluations if e["ticket_id"] == ticket_id]


def test_trigger_generation_requires_analisis_completo(monkeypatch) -> None:
    """Only tickets in 'analisis_completo' state can trigger generation."""
    repository = InMemoryResponseRepository()
    monkeypatch.setattr(rfp_intake, "SupabaseRfpRepository", lambda: repository)

    main.app.dependency_overrides[auth.get_current_user] = lambda: object()

    try:
        # Try with a non-existent ticket
        response = client.post("/rfp-intake/tickets/00000000-0000-4000-8000-000000000001/generate-response")
        assert response.status_code == 404
    finally:
        main.app.dependency_overrides.clear()


def test_trigger_generation_accepted_with_valid_ticket(monkeypatch) -> None:
    """A ticket in analisis_completo state should accept generation trigger."""
    repository = InMemoryResponseRepository()
    ticket_id = "00000000-0000-4000-8000-000000000002"
    repository.tickets[ticket_id] = {
        "id": ticket_id,
        "status": "analisis_completo",
        "handoff": {
            "sales_handoff": "Cliente solicita automatizar pedidos.",
            "workstreams": [
                {
                    "department": "Operaciones de Restaurante",
                    "key_aspects": [{"aspect": "Sistema", "request": "Automatizar", "evidence": "test", "missing_information": []}],
                }
            ],
        },
    }

    monkeypatch.setattr(rfp_intake, "SupabaseRfpRepository", lambda: repository)
    # Mock the actual pipeline to avoid calling LLM
    monkeypatch.setattr(
        "data.pipelines.rfp_response.process_rfp_response",
        lambda *_, **__: {"status": "ok"},
    )

    main.app.dependency_overrides[auth.get_current_user] = lambda: object()

    try:
        response = client.post(f"/rfp-intake/tickets/{ticket_id}/generate-response")
        assert response.status_code == 202
        result = response.json()
        assert result["ticket_id"] == ticket_id
        assert result["status"] == "generando_borrador"
    finally:
        main.app.dependency_overrides.clear()


def test_trigger_generation_rejects_wrong_state(monkeypatch) -> None:
    """Tickets not in analisis_completo should get 409."""
    repository = InMemoryResponseRepository()
    ticket_id = "00000000-0000-4000-8000-000000000003"
    repository.tickets[ticket_id] = {
        "id": ticket_id,
        "status": "analizando",
        "handoff": {"sales_handoff": "Test", "workstreams": []},
    }

    monkeypatch.setattr(rfp_intake, "SupabaseRfpRepository", lambda: repository)

    main.app.dependency_overrides[auth.get_current_user] = lambda: object()

    try:
        response = client.post(f"/rfp-intake/tickets/{ticket_id}/generate-response")
        assert response.status_code == 409
        assert "analisis_completo" in response.json()["detail"]
    finally:
        main.app.dependency_overrides.clear()


def test_get_response_returns_handoff(monkeypatch) -> None:
    """GET /tickets/{id}/response should return drafts and evaluations."""
    repository = InMemoryResponseRepository()
    ticket_id = "00000000-0000-4000-8000-000000000004"
    repository.tickets[ticket_id] = {
        "id": ticket_id,
        "status": "en_evaluacion",
    }
    repository.drafts.append({
        "ticket_id": ticket_id,
        "department": "Operaciones de Restaurante",
        "iteration": 1,
        "content": "Borrador de prueba.",
    })
    repository.evaluations.append({
        "ticket_id": ticket_id,
        "department": "Operaciones de Restaurante",
        "iteration": 1,
        "overall_pass": True,
        "readability": {"pass": True},
        "relevance": {"pass": True},
        "compliance": {"pass": True},
        "feedback_for_generator": "",
    })
    repository.handoffs[ticket_id] = {
        "ticket_id": ticket_id,
        "drafts": {},
        "needs_human_review": False,
    }

    monkeypatch.setattr(rfp_intake, "SupabaseRfpRepository", lambda: repository)

    main.app.dependency_overrides[auth.get_current_user] = lambda: object()

    try:
        response = client.get(f"/rfp-intake/tickets/{ticket_id}/response")
        assert response.status_code == 200
        result = response.json()
        assert result["ticket_id"] == ticket_id
        assert result["status"] == "en_evaluacion"
        assert len(result["drafts"]) == 1
        assert len(result["evaluation_results"]) == 1
        assert result["response_handoff"] is not None
    finally:
        main.app.dependency_overrides.clear()


def test_get_response_returns_404_for_missing_ticket(monkeypatch) -> None:
    """Non-existent ticket should return 404."""
    repository = InMemoryResponseRepository()
    monkeypatch.setattr(rfp_intake, "SupabaseRfpRepository", lambda: repository)

    main.app.dependency_overrides[auth.get_current_user] = lambda: object()

    try:
        response = client.get("/rfp-intake/tickets/00000000-0000-4000-8000-000000000099/response")
        assert response.status_code == 404
    finally:
        main.app.dependency_overrides.clear()