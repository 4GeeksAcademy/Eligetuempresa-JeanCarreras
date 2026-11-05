from fastapi.testclient import TestClient

from src import main
from src.brasaland_api import auth, rfp_intake


client = TestClient(main.app)


class InMemoryRfpRepository:
    def __init__(self) -> None:
        self.created: list[tuple[str, str, str]] = []

    def create_ticket(self, ticket_id: str, filename: str, pdf_path: str) -> None:
        self.created.append((ticket_id, filename, pdf_path))


def test_upload_creates_ticket_and_schedules_background_pipeline(tmp_path, monkeypatch) -> None:
    repository = InMemoryRfpRepository()
    scheduled: list[tuple[str, str]] = []
    upload_dir = tmp_path / "raw" / "rfp"
    monkeypatch.setattr(rfp_intake, "RAW_RFP_DIR", upload_dir)
    monkeypatch.setattr(rfp_intake, "SupabaseRfpRepository", lambda: repository)
    monkeypatch.setattr(
        rfp_intake,
        "process_rfp_ticket",
        lambda ticket_id, pdf_path, _repository: scheduled.append((ticket_id, pdf_path)),
    )
    main.app.dependency_overrides[auth.get_current_user] = lambda: object()

    try:
        response = client.post(
            "/rfp-intake/tickets",
            files={"file": ("request.pdf", b"%PDF-1.7\ncontent", "application/pdf")},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 202
    result = response.json()
    assert result["status"] == "analizando"
    assert len(repository.created) == 1
    ticket_id, filename, pdf_path = repository.created[0]
    assert result["ticket_id"] == ticket_id
    assert filename == "request.pdf"
    assert open(pdf_path, "rb").read() == b"%PDF-1.7\ncontent"
    assert scheduled == [(ticket_id, pdf_path)]


def test_upload_rejects_non_pdf_and_invalid_pdf_content(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(rfp_intake, "RAW_RFP_DIR", tmp_path / "raw")
    main.app.dependency_overrides[auth.get_current_user] = lambda: object()

    try:
        wrong_extension = client.post(
            "/rfp-intake/tickets",
            files={"file": ("request.txt", b"%PDF-1.7", "application/pdf")},
        )
        wrong_signature = client.post(
            "/rfp-intake/tickets",
            files={"file": ("request.pdf", b"not a PDF", "application/pdf")},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert wrong_extension.status_code == 415
    assert wrong_signature.status_code == 415
    assert not (tmp_path / "raw").exists()


def test_ticket_list_requires_authentication() -> None:
    response = client.get("/rfp-intake/tickets")

    assert response.status_code == 401