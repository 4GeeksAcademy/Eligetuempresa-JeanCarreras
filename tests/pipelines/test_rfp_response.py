"""Tests para el pipeline de generacion y evaluacion de respuestas RFP (Parte 2).

Cubre:
- Agente generador (caso de exito)
- Agente evaluador de legibilidad
- Agente evaluador de pertinencia
- Agente evaluador de cumplimiento (incluyendo fallo anclado al BRIEFING)
- Ciclo generador-evaluador con iteraciones
- Límite de iteraciones y needs_human_review
"""

import json
from unittest.mock import ANY

import pytest

from data.pipelines import rfp_response
from data.pipelines.rfp_response import (
    MAX_ITERATIONS,
    ReadabilityResult,
    RelevanceResult,
    ComplianceResult,
    EvaluationResult,
    DepartmentDraft,
    evaluate_readability,
    evaluate_relevance,
    evaluate_compliance,
    evaluate_draft,
    process_department,
    COMPLIANCE_RULES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_KEY_ASPECTS = [
    {
        "aspect": "Sistema de pedidos",
        "request": "Implementar sistema automatizado de pedidos a proveedores",
        "evidence": "necesitamos automatizar pedidos",
        "missing_information": [],
    },
    {
        "aspect": "Stock minimo",
        "request": "Alertas automaticas de stock minimo",
        "evidence": "alertas de inventario",
        "missing_information": ["volumen mensual"],
    },
]

SAMPLE_METADATA = {
    "customer_name": "Cliente Ejemplo SA",
    "request_title": "Propuesta de digitalizacion de pedidos",
    "response_deadline": "2026-12-15",
    "estimated_value": 150000,
    "currency": "USD",
}


# ---------------------------------------------------------------------------
# Generator agent test
# ---------------------------------------------------------------------------


def test_generator_produces_valid_draft(monkeypatch) -> None:
    """Verify the generator agent produces a properly structured proposal section."""
    captured_prompts: dict[str, str] = {}

    def fake_ask_model(system_prompt: str, user_prompt: str, response_format: str = "text") -> str:
        captured_prompts["system"] = system_prompt
        captured_prompts["user"] = user_prompt
        return (
            "## Alcance del servicio\n"
            "Se implementara un sistema automatizado de pedidos para los 14 locales de Brasaland "
            "en Colombia y Florida.\n\n"
            "## Desglose de precios\n"
            "La inversion total estimada es de 150.000 USD.\n\n"
            "## Cronograma de entregas\n"
            "Fase 1: Diagnostico (2 semanas). Fase 2: Implementacion (6 semanas).\n\n"
            "## Condiciones comerciales\n"
            "Pago: 50% al inicio, 50% contra entrega. Validez de la oferta: 30 dias."
        )

    monkeypatch.setattr(rfp_response, "ask_model", fake_ask_model)

    draft = rfp_response.generate_department_draft(
        department="Operaciones de Restaurante",
        key_aspects=SAMPLE_KEY_ASPECTS,
        metadata=SAMPLE_METADATA,
        sales_handoff="Cliente solicita automatizar pedidos a proveedores con alertas de stock minimo.",
        contact="Felipe Guerrero",
    )

    # Verify structure
    assert "Alcance del servicio" in draft
    assert "Desglose de precios" in draft
    assert "Cronograma de entregas" in draft
    assert "Condiciones comerciales" in draft
    assert "COP" in draft or "USD" in draft or "150.000" in draft

    # Verify prompt construction
    assert "Operaciones de Restaurante" in captured_prompts["system"]
    assert "Felipe Guerrero" in captured_prompts["system"]
    assert "C001" in captured_prompts["system"]  # compliance rules in system prompt


# ---------------------------------------------------------------------------
# Evaluator agents tests
# ---------------------------------------------------------------------------


def test_evaluate_readability_short_text_passes_automatically() -> None:
    """Very short texts should pass readability without library call."""
    draft = "Oferta valida por 30 dias. Precio: 500 USD."
    result = evaluate_readability(draft)
    assert result.passed is True
    assert result.score is None


def test_evaluate_relevance_passes_with_good_draft(monkeypatch) -> None:
    """A draft covering all key aspects should pass relevance."""
    draft = (
        "## Alcance\nImplementaremos un sistema que automatica pedidos a proveedores "
        "y genera alertas de stock minimo.\n"
        "## Precios\nInversion: 150.000 USD.\n"
        "## Cronograma\nEntrega en 8 semanas.\n"
        "## Condiciones\nPago a 30 dias."
    )

    monkeypatch.setattr(
        rfp_response,
        "ask_model_json",
        lambda *_, **__: {
            "passed": True,
            "missing_aspects": [],
            "details": "El borrador cubre los aspectos clave solicitados.",
        },
    )

    result = evaluate_relevance(draft, SAMPLE_KEY_ASPECTS, SAMPLE_METADATA)
    assert result.passed is True
    assert len(result.missing_aspects) == 0


def test_evaluate_relevance_fails_when_aspects_missing(monkeypatch) -> None:
    """A draft missing key aspects should fail relevance."""
    draft = (
        "## Alcance\nOfrecemos consultoria general.\n"
        "## Precios\nConsultar.\n"
        "## Cronograma\nPor definir.\n"
        "## Condiciones\nA convenir."
    )

    monkeypatch.setattr(
        rfp_response,
        "ask_model_json",
        lambda *_, **__: {
            "passed": False,
            "missing_aspects": ["Sistema de pedidos", "Stock minimo"],
            "details": "El borrador no menciona los aspectos clave solicitados.",
        },
    )

    result = evaluate_relevance(draft, SAMPLE_KEY_ASPECTS, SAMPLE_METADATA)
    assert result.passed is False
    assert "Sistema de pedidos" in result.missing_aspects


def test_evaluate_compliance_passes_with_compliant_draft(monkeypatch) -> None:
    """A draft following all rules should pass compliance."""
    draft = (
        "## Alcance del servicio\n"
        "Propuesta para los 14 locales de Brasaland en Colombia y Florida.\n\n"
        "## Desglose de precios\n"
        "Inversion total: 150.000 USD.\n\n"
        "## Cronograma de entregas\n"
        "Proteinas: entrega en 48 horas. Vegetales: 24 horas.\n\n"
        "## Condiciones comerciales\n"
        "Pago: 50% inicial, 50% contra entrega. Validez: 30 dias.\n\n"
        "*Nota: No se garantiza cero riesgo de contaminacion cruzada.*"
    )

    monkeypatch.setattr(
        rfp_response,
        "ask_model_json",
        lambda *_, **__: {
            "passed": True,
            "rule_ids": [],
            "violations": [],
            "details": "El borrador cumple con todas las reglas de cumplimiento.",
        },
    )

    result = evaluate_compliance(draft)
    assert result.passed is True
    assert len(result.violations) == 0


def test_evaluate_compliance_fails_on_briefing_violation(monkeypatch) -> None:
    """Compliance must reject a draft that promises something the BRIEFING prohibits.

    Anchored to rule C004: Never promise 'zero cross-contamination risk'.
    """
    draft = (
        "## Alcance del servicio\n"
        "Ofrecemos platos preparados con garantia de cero riesgo de contaminacion cruzada.\n\n"
        "## Desglose de precios\n"
        "Precio por plato: 5.000 COP.\n\n"
        "## Cronograma de entregas\n"
        "Entrega en 24 horas.\n\n"
        "## Condiciones comerciales\n"
        "Pago contra entrega."
    )

    monkeypatch.setattr(
        rfp_response,
        "ask_model_json",
        lambda *_, **__: {
            "passed": False,
            "rule_ids": ["C004"],
            "violations": ["C004: El borrador promete 'cero riesgo de contaminacion cruzada', lo cual viola la regla que prohibe esta afirmacion."],
            "details": "Violacion de la regla C004 sobre contaminacion cruzada.",
        },
    )

    result = evaluate_compliance(draft)
    assert result.passed is False
    assert "C004" in result.rule_ids
    assert any("cero riesgo" in v.lower() or "C004" in v for v in result.violations)


# ---------------------------------------------------------------------------
# Full evaluation runner test (parallel evaluators)
# ---------------------------------------------------------------------------


def test_evaluate_draft_aggregates_results(monkeypatch) -> None:
    """Verify that evaluate_draft runs all three evaluators and aggregates correctly."""
    draft = "Sample draft content for testing evaluation aggregation."

    monkeypatch.setattr(
        rfp_response,
        "evaluate_readability",
        lambda _: ReadabilityResult(passed=True, score=8.5, details="Legible."),
    )
    monkeypatch.setattr(
        rfp_response,
        "evaluate_relevance",
        lambda *_: RelevanceResult(passed=True, missing_aspects=[], details="Pertinente."),
    )
    monkeypatch.setattr(
        rfp_response,
        "evaluate_compliance",
        lambda _: ComplianceResult(passed=True, rule_ids=[], violations=[], details="Cumple."),
    )

    result = evaluate_draft(draft, "Operaciones de Restaurante", SAMPLE_KEY_ASPECTS, SAMPLE_METADATA)

    assert result.overall_pass is True
    assert result.readability is not None and result.readability.passed is True
    assert result.relevance is not None and result.relevance.passed is True
    assert result.compliance is not None and result.compliance.passed is True


def test_evaluate_draft_fails_on_any_evaluation_failure(monkeypatch) -> None:
    """If any evaluator fails, overall_pass should be False with specific feedback."""
    draft = "Draft with compliance issues."

    monkeypatch.setattr(
        rfp_response,
        "evaluate_readability",
        lambda _: ReadabilityResult(passed=True, score=10.0, details="Legible."),
    )
    monkeypatch.setattr(
        rfp_response,
        "evaluate_relevance",
        lambda *_: RelevanceResult(passed=True, missing_aspects=[], details="Pertinente."),
    )
    monkeypatch.setattr(
        rfp_response,
        "evaluate_compliance",
        lambda _: ComplianceResult(
            passed=False,
            rule_ids=["C004"],
            violations=["C004: Promete cero riesgo de contaminacion cruzada."],
            details="Violacion de reglas de cumplimiento.",
        ),
    )

    result = evaluate_draft(draft, "Operaciones de Restaurante", SAMPLE_KEY_ASPECTS, SAMPLE_METADATA)

    assert result.overall_pass is False
    assert result.feedback_for_generator != ""
    assert "C004" in result.feedback_for_generator or "incumplimiento" in result.feedback_for_generator.lower() or "violacion" in result.feedback_for_generator.lower() or "CUMPLIMIENTO" in result.feedback_for_generator


# ---------------------------------------------------------------------------
# Generator-evaluator loop test
# ---------------------------------------------------------------------------


def test_process_department_passes_after_iterations(monkeypatch) -> None:
    """A department should pass after the generator-evaluator loop."""
    call_count = [0]

    def fake_generate(*args, **kwargs) -> str:
        call_count[0] += 1
        return (
            "## Alcance del servicio\n"
            "Implementacion de sistema automatizado de pedidos.\n\n"
            "## Desglose de precios\n"
            "Total: 150.000 USD.\n\n"
            "## Cronograma de entregas\n"
            "Entrega en 8 semanas.\n\n"
            "## Condiciones comerciales\n"
            "Pago a 30 dias."
        )

    def fake_evaluate(*_, **__) -> EvaluationResult:
        # Pass on second attempt
        passed = call_count[0] >= 2
        return EvaluationResult(
            section_id="test",
            department_id="Operaciones de Restaurante",
            readability=ReadabilityResult(passed=True),
            relevance=RelevanceResult(passed=True),
            compliance=ComplianceResult(passed=True),
            overall_pass=passed,
            feedback_for_generator="" if passed else "Corregir formato.",
        )

    monkeypatch.setattr(rfp_response, "generate_department_draft", fake_generate)
    monkeypatch.setattr(rfp_response, "evaluate_draft", fake_evaluate)

    result = process_department(
        "Operaciones de Restaurante",
        SAMPLE_KEY_ASPECTS,
        SAMPLE_METADATA,
        "Handoff de prueba",
        "Felipe Guerrero",
    )

    assert result.needs_human_review is False
    assert result.evaluation is not None
    assert result.evaluation.overall_pass is True
    assert call_count[0] >= 2  # At least 2 iterations


def test_process_department_exhausts_iterations(monkeypatch) -> None:
    """When iterations are exhausted, the draft should be marked needs_human_review."""
    call_count = [0]

    def fake_generate(*args, **kwargs) -> str:
        call_count[0] += 1
        return (
            "## Alcance\nBorrador de prueba.\n\n"
            "## Precios\nConsultar.\n\n"
            "## Cronograma\nTBD.\n\n"
            "## Condiciones\nA convenir."
        )

    def fake_evaluate(*_, **__) -> EvaluationResult:
        return EvaluationResult(
            section_id="test",
            department_id="Operaciones de Restaurante",
            readability=ReadabilityResult(passed=False, score=18.0, details="Demasiado complejo."),
            relevance=RelevanceResult(passed=False, missing_aspects=["Sistema de pedidos"]),
            compliance=ComplianceResult(passed=False, rule_ids=["C001"], violations=["C001: Tono"]),
            overall_pass=False,
            feedback_for_generator="Corregir los problemas de legibilidad, pertinencia y cumplimiento.",
        )

    monkeypatch.setattr(rfp_response, "generate_department_draft", fake_generate)
    monkeypatch.setattr(rfp_response, "evaluate_draft", fake_evaluate)

    result = process_department(
        "Operaciones de Restaurante",
        SAMPLE_KEY_ASPECTS,
        SAMPLE_METADATA,
        "Handoff de prueba",
        "Felipe Guerrero",
    )

    assert result.needs_human_review is True
    assert result.evaluation is not None
    assert result.evaluation.overall_pass is False
    assert result.iteration == MAX_ITERATIONS
    assert call_count[0] == MAX_ITERATIONS


# ---------------------------------------------------------------------------
# EvaluationResult serialization tests
# ---------------------------------------------------------------------------


def test_evaluation_result_roundtrip() -> None:
    """EvaluationResult should serialize to dict and back correctly."""
    original = EvaluationResult(
        section_id="test-section",
        department_id="Test Dept",
        readability=ReadabilityResult(passed=True, score=8.2, details="Claro y conciso."),
        relevance=RelevanceResult(passed=True, missing_aspects=[], details="Cubre todo."),
        compliance=ComplianceResult(
            passed=False, rule_ids=["C004"], violations=["Promete cero riesgo"],
            details="Violacion de C004",
        ),
        overall_pass=False,
        feedback_for_generator="Eliminar referencias a riesgo cero.",
    )

    as_dict = original.to_dict()
    restored = EvaluationResult.from_dict(as_dict)

    assert restored.section_id == original.section_id
    assert restored.department_id == original.department_id
    assert restored.overall_pass == original.overall_pass
    assert restored.feedback_for_generator == original.feedback_for_generator
    assert restored.readability is not None and restored.readability.passed == original.readability.passed
    assert restored.relevance is not None and restored.relevance.passed == original.relevance.passed
    assert restored.compliance is not None and restored.compliance.passed == original.compliance.passed
    assert restored.compliance.rule_ids == ["C004"]


# ---------------------------------------------------------------------------
# DepartmentDraft tests
# ---------------------------------------------------------------------------


def test_department_draft_properties() -> None:
    """DepartmentDraft should correctly reflect needs_human_review."""
    draft_pass = DepartmentDraft(
        department="Test",
        iteration=1,
        content="Test content",
        evaluation=EvaluationResult(overall_pass=True),
    )
    assert draft_pass.needs_human_review is False

    draft_fail = DepartmentDraft(
        department="Test",
        iteration=3,
        content="Test content",
        evaluation=EvaluationResult(overall_pass=False),
    )
    assert draft_fail.needs_human_review is True


def test_department_draft_to_dict() -> None:
    """DepartmentDraft.to_dict should include all fields."""
    draft = DepartmentDraft(
        department="Test Dept",
        iteration=2,
        content="Some proposal content.",
        evaluation=EvaluationResult(
            overall_pass=True,
            feedback_for_generator="Todo correcto.",
        ),
    )

    result = draft.to_dict()
    assert result["department"] == "Test Dept"
    assert result["iteration"] == 2
    assert result["content"] == "Some proposal content."
    assert result["needs_human_review"] is False
    assert result["evaluation"]["overall_pass"] is True


# ---------------------------------------------------------------------------
# Compliance rules fixture test
# ---------------------------------------------------------------------------


def test_compliance_rules_include_all_categories() -> None:
    """Verify that compliance rules cover all required categories."""
    categories = {rule["category"] for rule in COMPLIANCE_RULES}
    assert "tone" in categories
    assert "pricing" in categories
    assert "timeline" in categories
    assert "allergens" in categories
    assert "loyalty" in categories
    assert "scope" in categories
    assert "format" in categories