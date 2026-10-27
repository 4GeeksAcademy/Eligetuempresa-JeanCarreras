from types import SimpleNamespace

from data.pipelines import rag


def test_retrieve_filters_below_min_score_and_returns_payloads(monkeypatch):
    payloads = [
        {"source_document": "loyalty-program", "text": "chunk válido"},
        {"source_document": "menu-allergens", "text": "chunk de score bajo"},
        {"source_document": "supplier-ordering", "text": "chunk válido dos"},
    ]
    points = [
        SimpleNamespace(score=0.81, payload=payloads[0]),
        SimpleNamespace(score=0.29, payload=payloads[1]),
        SimpleNamespace(score=0.63, payload=payloads[2]),
    ]

    class FakeQdrant:
        def query_points(self, **kwargs):
            assert kwargs["limit"] == 5
            assert kwargs["with_payload"] is True
            return SimpleNamespace(points=points)

    monkeypatch.setattr(rag, "embed", lambda _: [0.1, 0.2])
    monkeypatch.setattr(rag, "_qdrant_client", lambda: FakeQdrant())

    result = rag.retrieve("¿Cómo funciona el programa?", k=5, min_score=0.5)

    assert result == [payloads[0], payloads[2]]
    assert all("score" not in payload for payload in result)


def test_retrieve_can_return_fewer_than_k_results(monkeypatch):
    class FakeQdrant:
        def query_points(self, **kwargs):
            return SimpleNamespace(
                points=[SimpleNamespace(score=0.9, payload={"text": "único"})]
            )

    monkeypatch.setattr(rag, "embed", lambda _: [0.1])
    monkeypatch.setattr(rag, "_qdrant_client", lambda: FakeQdrant())

    result = rag.retrieve("consulta", k=5, min_score=0.4)

    assert result == [{"text": "único"}]
    assert len(result) < 5


def test_query_returns_generated_answer_not_retrieved_chunk(monkeypatch):
    retrieved_context = [{"source_document": "loyalty-program", "text": "50+ puntos"}]
    captured: dict[str, object] = {}
    generated_answer = "El nivel Oro comienza en 50 puntos. (loyalty-program)"

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=generated_answer)
                    )
                ]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client_options"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setattr(rag, "_model_names", lambda: ("embed-test", "generation-test"))
    monkeypatch.setattr(rag, "OpenAI", FakeClient)
    monkeypatch.setattr(rag, "retrieve", lambda question: retrieved_context)

    answer = rag.query("¿Cuántos puntos necesito para Oro?")

    assert answer == generated_answer
    assert answer != retrieved_context[0]["text"]
    assert captured["model"] == "generation-test"
    assert "50+ puntos" in captured["messages"][1]["content"]


def test_query_generates_an_insufficient_information_answer_for_empty_context(monkeypatch):
    generation_response = "La base de conocimiento no contiene información suficiente."
    seen_context: list[dict] | None = None

    def fake_generate(question: str, context: list[dict]) -> str:
        nonlocal seen_context
        seen_context = context
        return generation_response

    monkeypatch.setattr(rag, "retrieve", lambda _: [])
    monkeypatch.setattr(rag, "generate_answer", fake_generate)

    answer = rag.query("¿Cuál es la política sobre otra cosa?")

    assert answer == generation_response
    assert seen_context == []
