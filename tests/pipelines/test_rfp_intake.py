from data.pipelines import rfp_intake


def test_classifier_rejects_a_clear_non_rfp(monkeypatch) -> None:
    monkeypatch.setattr(
        rfp_intake,
        "ask_model",
        lambda *_: {
            "is_rfp": False,
            "confidence": 0.96,
            "rationale": "El documento es una factura.",
        },
    )

    result = rfp_intake.classify_document("Factura de proveedor")

    assert result["is_rfp"] is False
    assert result["confidence"] == 0.96


def test_classifier_keeps_ambiguous_documents_for_review(monkeypatch) -> None:
    monkeypatch.setattr(
        rfp_intake,
        "ask_model",
        lambda *_: {"is_rfp": False, "confidence": 0.72, "rationale": "Ambiguo"},
    )

    assert rfp_intake.classify_document("Solicitud comercial")["is_rfp"] is True


def test_worker_keeps_only_aspects_with_literal_evidence(monkeypatch) -> None:
    excerpt = "Solicitamos servicio para 12 restaurantes en Bogota."
    monkeypatch.setattr(
        rfp_intake,
        "ask_model",
        lambda *_: {
            "key_aspects": [
                {
                    "aspect": "Cobertura",
                    "request": "Describir cobertura operativa",
                    "evidence": "servicio para 12 restaurantes",
                    "missing_information": ["horarios"],
                },
                {
                    "aspect": "Volumen inventado",
                    "request": "Atender 20 locales",
                    "evidence": "20 locales",
                    "missing_information": [],
                },
            ]
        },
    )

    result = rfp_intake.analyze_department(
        "Operaciones de Restaurante", excerpt, {"customer_name": "Cliente"}
    )

    assert result["contact"] == rfp_intake.DEPARTMENTS["Operaciones de Restaurante"]
    assert [item["aspect"] for item in result["key_aspects"]] == ["Cobertura"]