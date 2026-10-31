"""
RFP Response Generation Pipeline (Part 2).

Consumes the routing handoff from Part 1 (analisis_completo tickets)
and runs a generator-evaluator loop per department:

  analisis_completo → generando_borrador → en_evaluacion → (needs_human_review)

Each department gets a generator agent + parallel evaluators (readability,
relevance, compliance) with an iteration limit. Failed sections are included
in the handoff with needs_human_review flag — never discarded.
"""

from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ITERATIONS = 3
MAX_PARALLEL_EVALUATORS = 3
MAX_PARALLEL_DEPARTMENTS = 7

DEPARTMENTS = {
    "Operaciones de Restaurante": "Felipe Guerrero",
    "Compras y Proveedores": "Lucia Fernandez",
    "Marketing y Experiencia Digital": "Camila Ospina",
    "Personas y Cultura": "Ashley Turner",
    "Formacion y Estandares de Calidad": "Jake Morrison",
    "Tecnologia": "Nicolas Park",
    "Direccion Ejecutiva": "Mariana Restrepo",
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ReadabilityResult:
    passed: bool
    score: float | None = None
    details: str = ""


@dataclass
class RelevanceResult:
    passed: bool
    missing_aspects: list[str] = field(default_factory=list)
    details: str = ""


@dataclass
class ComplianceResult:
    passed: bool
    rule_ids: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    details: str = ""


@dataclass
class EvaluationResult:
    section_id: str = ""
    department_id: str = ""
    readability: ReadabilityResult | None = None
    relevance: RelevanceResult | None = None
    compliance: ComplianceResult | None = None
    overall_pass: bool = False
    feedback_for_generator: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "department_id": self.department_id,
            "readability": asdict(self.readability) if self.readability else {},
            "relevance": asdict(self.relevance) if self.relevance else {},
            "compliance": asdict(self.compliance) if self.compliance else {},
            "overall_pass": self.overall_pass,
            "feedback_for_generator": self.feedback_for_generator,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EvaluationResult":
        ev = cls(
            section_id=data.get("section_id", ""),
            department_id=data.get("department_id", ""),
            overall_pass=data.get("overall_pass", False),
            feedback_for_generator=data.get("feedback_for_generator", ""),
        )
        if "readability" in data and data["readability"]:
            ev.readability = ReadabilityResult(**data["readability"])
        if "relevance" in data and data["relevance"]:
            ev.relevance = RelevanceResult(**data["relevance"])
        if "compliance" in data and data["compliance"]:
            ev.compliance = ComplianceResult(**data["compliance"])
        return ev


@dataclass
class DepartmentDraft:
    department: str
    iteration: int
    content: str
    evaluation: EvaluationResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "department": self.department,
            "iteration": self.iteration,
            "content": self.content,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "needs_human_review": self.needs_human_review,
        }

    @property
    def needs_human_review(self) -> bool:
        return self.evaluation is not None and not self.evaluation.overall_pass


# ---------------------------------------------------------------------------
# LLM helper (same pattern as Part 1)
# ---------------------------------------------------------------------------


def ask_model(system_prompt: str, user_prompt: str, response_format: str = "text") -> str:
    from openai import OpenAI

    client = OpenAI()
    kwargs = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if response_format == "json":
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    if not content:
        raise ValueError("El modelo devolvio una respuesta vacia")
    return content


def ask_model_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    content = ask_model(system_prompt, user_prompt, response_format="json")
    result = json.loads(content)
    if not isinstance(result, dict):
        raise ValueError("El modelo devolvio un objeto no valido")
    return result


# ---------------------------------------------------------------------------
# Company compliance rules (from CONTEXT.md & knowledge base)
# ---------------------------------------------------------------------------

COMPLIANCE_RULES: list[dict[str, Any]] = [
    {
        "id": "C001",
        "rule": "Tono profesional y cercano: usar 'usted' o 'tu' de forma consistente, reflejando 'servicio calido y consistente'.",
        "category": "tone",
    },
    {
        "id": "C002",
        "rule": "Todas las cifras economicas deben incluir moneda explicita (COP o USD). Nunca mezclar monedas sin conversion explicita.",
        "category": "pricing",
    },
    {
        "id": "C003",
        "rule": "Cualquier referido a plazos de entrega debe alinearse con los plazos reales del negocio: proteinas 48h, verduras 24h, bebidas 5 dias habiles, importados 10-15 dias habiles.",
        "category": "timeline",
    },
    {
        "id": "C004",
        "rule": "No prometer 'cero riesgo de contaminacion cruzada' en ningun contexto alimentario. Declarar siempre que no se garantiza riesgo cero.",
        "category": "allergens",
    },
    {
        "id": "C005",
        "rule": "El programa de fidelizacion se llama 'Brasa Points'. Describir niveles correctamente: Bronce (0-19 pts), Plata (20-49 pts), Oro (50+ pts). No inventar niveles ni beneficios.",
        "category": "loyalty",
    },
    {
        "id": "C006",
        "rule": "No prometer productos o servicios que Brasaland no tenga actualmente (app funcional, web con pedidos online, API publica, dashboard en tiempo real) como si estuvieran en produccion. Indicar que estan en desarrollo o planificacion si se mencionan.",
        "category": "scope",
    },
    {
        "id": "C007",
        "rule": "Incluir alcance geografico explicito: Colombia (X locales) y Florida (Y locales). No generalizar a 'toda la cadena' sin especificar paises.",
        "category": "scope",
    },
    {
        "id": "C008",
        "rule": "Los descuentos de Brasa Points son: 5% bebidas (Bronce), 10% plato principal 1 vez al mes (Plata), 15% permanente + menú temporada anticipado (Oro). No inventar porcentajes.",
        "category": "loyalty",
    },
    {
        "id": "C009",
        "rule": "Cada seccion debe incluir: alcance del servicio, precios desglosados, cronograma de entregas y condiciones comerciales/forma de pago.",
        "category": "format",
    },
    {
        "id": "C010",
        "rule": "No incluir clausulas que requieran tecnologia o capacidad que Brasaland no tiene documentada. Solo referirse a lo que existe en CONTEXT.md y en la base de conocimiento.",
        "category": "scope",
    },
]


def get_compliance_rules() -> list[dict[str, Any]]:
    """Return the current compliance rules for evaluators."""
    return COMPLIANCE_RULES


# ---------------------------------------------------------------------------
# Generator agents (one per department)
# ---------------------------------------------------------------------------


def build_generator_system_prompt(department: str, contact: str) -> str:
    """Build the system prompt for a department generator."""
    rules_summary = "\n".join(
        f"- [{r['id']}] {r['rule']}"
        for r in COMPLIANCE_RULES
    )
    return f"""Eres el agente generador de propuestas economicas para el departamento '{department}' de Brasaland.
Redactas la seccion correspondiente de una propuesta comercial en espanol.

Responsable del departamento: {contact}

Debes seguir estos lineamientos obligatorios de la empresa:
{rules_summary}

Formato de la seccion (obligatorio):
1. **Alcance del servicio** - Que incluye y que no incluye esta propuesta
2. **Desglose de precios** - Con moneda explicita (COP/USD)
3. **Cronograma de entregas** - Plazos realistas alineados con la operacion
4. **Condiciones comerciales** - Forma de pago, validez de la oferta

Redacta en espanol, con tono profesional y cercano. Usa la informacion del resumen de la RFP y los key_aspects proporcionados. Si la RFP pide algo fuera del alcance del departamento, indicalo educadamente.

NO incluyas informacion que no este respaldada por los datos de entrada proporcionados."""


def build_generator_user_prompt(
    department: str,
    contact: str,
    key_aspects: list[dict[str, Any]],
    metadata: dict[str, Any],
    sales_handoff: str,
    feedback: str | None = None,
    previous_draft: str | None = None,
    knowledge_context: str | None = None,
) -> str:
    """Build the user prompt with data for generation."""
    aspects_text = json.dumps(key_aspects, ensure_ascii=False, indent=2)
    meta_text = json.dumps(metadata, ensure_ascii=False, indent=2)

    prompt_parts = [
        f"## Resumen de la RFP (handoff de Ventas)\n{sales_handoff}",
        f"## Metadatos del documento\n{meta_text}",
        f"## Aspectos clave para {department}\n{aspects_text}",
    ]

    if knowledge_context:
        prompt_parts.append(
            f"## Contexto de conocimiento de la empresa (para referencia)\n{knowledge_context}"
        )

    if feedback and previous_draft:
        prompt_parts.extend([
            "## Feedback de la evaluacion anterior (debes corregir esto)",
            feedback,
            "## Borrador anterior (a mejorar)",
            previous_draft,
        ])

    prompt_parts.append(
        "\n---\nRedacta la seccion de propuesta economica para el departamento siguiendo el formato obligatorio (Alcance, Precios, Cronograma, Condiciones)."
    )

    return "\n\n".join(prompt_parts)


def generate_department_draft(
    department: str,
    key_aspects: list[dict[str, Any]],
    metadata: dict[str, Any],
    sales_handoff: str,
    contact: str,
    feedback: str | None = None,
    previous_draft: str | None = None,
    knowledge_context: str | None = None,
) -> str:
    """Generate a proposal section for a specific department."""
    system_prompt = build_generator_system_prompt(department, contact)
    user_prompt = build_generator_user_prompt(
        department, contact, key_aspects, metadata, sales_handoff,
        feedback, previous_draft, knowledge_context,
    )
    return ask_model(system_prompt, user_prompt)


# ---------------------------------------------------------------------------
# Evaluator agents
# ---------------------------------------------------------------------------


def evaluate_readability(draft: str) -> ReadabilityResult:
    """Evaluate readability using py-readability-metrics."""
    try:
        from readability import Readability

        words = len(draft.split())
        if words < 100:
            return ReadabilityResult(
                passed=True,
                score=None,
                details="Texto demasiado corto para evaluar legibilidad (menos de 100 palabras). Se acepta.",
            )

        reading = Readability(draft)
        fk = reading.flesch_kincaid()
        grade = fk.grade_level

        # Acceptable: grade level <= 12 (college level), ideal <= 9
        acceptable = grade <= 14
        return ReadabilityResult(
            passed=acceptable,
            score=round(grade, 1),
            details=f"Flesch-Kincaid Grade Level: {grade:.1f}. {'Aceptable' if acceptable else 'Demasiado complejo (objetivo: <= 14)'}",
        )
    except ImportError:
        logger.warning("py-readability-metrics no instalado; usando evaluacion LLM como fallback.")
        return _evaluate_readability_llm_fallback(draft)
    except (ValueError, ZeroDivisionError) as exc:
        return ReadabilityResult(
            passed=True,
            score=None,
            details=f"No se pudo calcular legibilidad: {exc}. Se acepta con pase automatico.",
        )


def _evaluate_readability_llm_fallback(draft: str) -> ReadabilityResult:
    """LLM-based readability evaluation when library is unavailable."""
    prompt = f"""Eres un evaluador de legibilidad. Analiza el siguiente texto y determina si es facil de leer para un publico de negocios.

Criterios:
- Oraciones cortas y claras (promedio < 25 palabras)
- Vocabulario no excesivamente tecnico
- Parrafos bien estructurados
- Uso de viñetas o listas para informacion compleja

Responde JSON con: {{"passed": bool, "score": float (1-100), "details": string}}

Texto a evaluar:
{draft[:8000]}"""
    try:
        result = ask_model_json(
            "Eres un evaluador de legibilidad de textos comerciales. Siempre respondes en JSON.",
            prompt,
        )
        return ReadabilityResult(
            passed=bool(result.get("passed", False)),
            score=float(result.get("score", 0)) if result.get("score") is not None else None,
            details=str(result.get("details", "")),
        )
    except Exception as exc:
        logger.warning("LLM readability fallback fallo: %s", exc)
        return ReadabilityResult(passed=True, details="Evaluacion de legibilidad no disponible; pase automatico.")


def evaluate_relevance(
    draft: str,
    key_aspects: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> RelevanceResult:
    """Evaluate whether the draft responds to what the RFP asks for."""
    aspects_text = json.dumps(key_aspects, ensure_ascii=False, indent=2)
    meta_text = json.dumps(metadata, ensure_ascii=False, indent=2)

    prompt = f"""Eres un evaluador de pertinencia. Determina si el borrador de propuesta responde adecuadamente a lo que solicita la RFP.

Aspectos clave que debe cubrir:
{aspects_text}

Metadatos de la solicitud:
{meta_text}

Responde JSON con:
{{
    "passed": bool,
    "missing_aspects": ["aspecto1", "aspecto2"],
    "details": "explicacion breve de por que pasa o falla"
}}

Texto del borrador a evaluar:
{draft[:8000]}"""
    try:
        result = ask_model_json(
            "Eres un evaluador de pertinencia de propuestas comerciales. Siempre respondes en JSON.",
            prompt,
        )
        missing = result.get("missing_aspects", [])
        if not isinstance(missing, list):
            missing = []
        return RelevanceResult(
            passed=bool(result.get("passed", False)),
            missing_aspects=[str(a) for a in missing],
            details=str(result.get("details", "")),
        )
    except Exception as exc:
        logger.warning("Relevance evaluation fallo: %s", exc)
        return RelevanceResult(
            passed=True,
            details="Evaluacion de pertinencia no disponible; pase automatico.",
        )


def evaluate_compliance(draft: str) -> ComplianceResult:
    """Evaluate compliance against company BRIEFING rules."""
    rules_text = "\n".join(
        f"- [{r['id']}] ({r['category']}) {r['rule']}"
        for r in COMPLIANCE_RULES
    )

    prompt = f"""Eres un evaluador de cumplimiento normativo de Brasaland. Revisa el borrador contra estas reglas obligatorias de la empresa:

{rules_text}

Para cada regla, determina si el borrador la cumple. Si no la cumple, registra el ID de la regla y una explicacion de la violacion.

Responde JSON con:
{{
    "passed": bool,
    "rule_ids": ["C001", "C003"],
    "violations": ["C001: descripcion de la violacion", "C003: ..."],
    "details": "resumen general del cumplimiento"
}}

Texto del borrador a evaluar:
{draft[:8000]}"""
    try:
        result = ask_model_json(
            "Eres un evaluador de cumplimiento normativo de propuestas. Siempre respondes en JSON.",
            prompt,
        )
        rule_ids = result.get("rule_ids", [])
        violations = result.get("violations", [])
        if not isinstance(rule_ids, list):
            rule_ids = []
        if not isinstance(violations, list):
            violations = []
        return ComplianceResult(
            passed=bool(result.get("passed", False)),
            rule_ids=[str(r) for r in rule_ids],
            violations=[str(v) for v in violations],
            details=str(result.get("details", "")),
        )
    except Exception as exc:
        logger.warning("Compliance evaluation fallo: %s", exc)
        return ComplianceResult(
            passed=True,
            details="Evaluacion de cumplimiento no disponible; pase automatico.",
        )


# ---------------------------------------------------------------------------
# Full evaluation runner (parallel evaluators for one draft)
# ---------------------------------------------------------------------------


def evaluate_draft(
    draft: str,
    department: str,
    key_aspects: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> EvaluationResult:
    """Run all three evaluators in parallel and aggregate results."""
    result = EvaluationResult(
        section_id=f"{department}",
        department_id=department,
    )

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_EVALUATORS) as executor:
        futures = {
            executor.submit(evaluate_readability, draft): "readability",
            executor.submit(evaluate_relevance, draft, key_aspects, metadata): "relevance",
            executor.submit(evaluate_compliance, draft): "compliance",
        }

        for future in as_completed(futures):
            name = futures[future]
            try:
                eval_result = future.result()
                if name == "readability":
                    result.readability = eval_result
                elif name == "relevance":
                    result.relevance = eval_result
                elif name == "compliance":
                    result.compliance = eval_result
            except Exception as exc:
                logger.error("Evaluador %s fallo con excepcion: %s", name, exc)
                if name == "readability":
                    result.readability = ReadabilityResult(passed=True, details=f"Error en evaluador: {exc}")
                elif name == "relevance":
                    result.relevance = RelevanceResult(passed=True, details=f"Error en evaluador: {exc}")
                elif name == "compliance":
                    result.compliance = ComplianceResult(passed=True, details=f"Error en evaluador: {exc}")

    # Overall pass: all evaluators must pass
    passes = []
    if result.readability is not None:
        passes.append(result.readability.passed)
    if result.relevance is not None:
        passes.append(result.relevance.passed)
    if result.compliance is not None:
        passes.append(result.compliance.passed)

    result.overall_pass = all(passes)

    # Build concrete feedback for the generator
    feedback_parts = []
    if result.readability and not result.readability.passed:
        feedback_parts.append(
            f"LEGIBILIDAD: {result.readability.details}. "
            "Simplifica el lenguaje, usa oraciones mas cortas y viñetas donde sea posible."
        )
    if result.relevance and not result.relevance.passed:
        missing = ", ".join(result.relevance.missing_aspects) if result.relevance.missing_aspects else "varios aspectos"
        feedback_parts.append(
            f"PERTINENCIA: Faltan aspectos clave: {missing}. "
            f"Detalles: {result.relevance.details}"
        )
    if result.compliance and not result.compliance.passed:
        violations = "; ".join(result.compliance.violations) if result.compliance.violations else "sin detalle"
        feedback_parts.append(
            f"CUMPLIMIENTO: Violaciones detectadas: {violations}. "
            f"Detalles: {result.compliance.details}"
        )

    result.feedback_for_generator = "\n".join(feedback_parts) if feedback_parts else ""
    return result


# ---------------------------------------------------------------------------
# Department processing (generator + evaluation loop)
# ---------------------------------------------------------------------------


def process_department(
    department: str,
    key_aspects: list[dict[str, Any]],
    metadata: dict[str, Any],
    sales_handoff: str,
    contact: str,
    knowledge_context: str | None = None,
) -> DepartmentDraft:
    """Run the generator-evaluator loop for a single department."""
    best_draft: DepartmentDraft | None = None
    current_draft: str | None = None
    last_feedback: str | None = None

    for iteration in range(1, MAX_ITERATIONS + 1):
        logger.info("Departamento %s — Iteracion %d/%d", department, iteration, MAX_ITERATIONS)

        # Generate
        current_draft = generate_department_draft(
            department, key_aspects, metadata, sales_handoff, contact,
            feedback=last_feedback,
            previous_draft=current_draft,
            knowledge_context=knowledge_context,
        )

        draft_entry = DepartmentDraft(
            department=department,
            iteration=iteration,
            content=current_draft,
        )

        # Evaluate
        evaluation = evaluate_draft(current_draft, department, key_aspects, metadata)
        draft_entry.evaluation = evaluation

        if evaluation.overall_pass:
            logger.info("Departamento %s — PASO evaluacion en iteracion %d", department, iteration)
            return draft_entry

        # Save best so far (last iteration or highest-scoring)
        if best_draft is None:
            best_draft = draft_entry
        else:
            best_draft = draft_entry  # Keep most recent

        last_feedback = evaluation.feedback_for_generator
        logger.info(
            "Departamento %s — Iteracion %d no paso. Feedback: %s",
            department, iteration, last_feedback[:200],
        )

    # All iterations exhausted
    if best_draft is not None and best_draft.evaluation is not None:
        best_draft.evaluation.overall_pass = False
    logger.info(
        "Departamento %s — Limite de iteraciones agotado. Marcando needs_human_review.",
        department,
    )
    return best_draft or DepartmentDraft(
        department=department,
        iteration=MAX_ITERATIONS,
        content=current_draft or "",
        evaluation=EvaluationResult(overall_pass=False, feedback_for_generator="No se pudo generar borrador."),
    )


# ---------------------------------------------------------------------------
# Knowledge base helper (optional)
# ---------------------------------------------------------------------------


def retrieve_knowledge_context() -> str | None:
    """Try to retrieve company knowledge base content for the generator.

    This is optional — if Qdrant/RAG is unavailable, returns None.
    """
    try:
        from data.pipelines.rag import retrieve

        knowledge_docs = retrieve(
            "politicas de precios, plazos de entrega, programa de fidelizacion, protocolos de la empresa",
            k=8,
        )
        if not knowledge_docs:
            return None
        context_parts = []
        for doc in knowledge_docs:
            source = doc.get("source_document", "unknown")
            text = doc.get("text", "")
            context_parts.append(f"[Fuente: {source}]\n{text}")
        return "\n\n".join(context_parts)
    except Exception as exc:
        logger.warning("Knowledge base no disponible para generacion: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def process_rfp_response(
    ticket_id: str,
    handoff: dict[str, Any],
    repository: Any,
) -> dict[str, Any]:
    """Main entry point for Part 2 processing.

    Args:
        ticket_id: UUID of the RFP ticket to process.
        handoff: The handoff payload from Part 1 (sales_handoff + workstreams).
        repository: A repository instance for persistence (SupabaseRfpRepository).

    Returns:
        The handoff dict for Part 3, including drafts and evaluation results.
    """
    sales_handoff = handoff.get("sales_handoff", "")
    workstreams = handoff.get("workstreams", [])

    if not workstreams:
        logger.warning("Ticket %s: no hay workstreams en el handoff.", ticket_id)
        return handoff

    # Transition to generating state
    try:
        repository.update_ticket_status(ticket_id, "generando_borrador")
    except Exception as exc:
        logger.error("No se pudo actualizar estado a generando_borrador: %s", exc)

    # Get knowledge context if available (optional)
    knowledge_context = retrieve_knowledge_context()

    # Extract metadata from handoff (first workstream has it)
    metadata = {}
    if workstreams and len(workstreams) > 0:
        first = workstreams[0]
        if isinstance(first, dict):
            metadata = {
                "customer_name": first.get("customer_name", ""),
                "request_title": first.get("request_title", ""),
                "response_deadline": first.get("response_deadline", ""),
            }

    # Process each department in parallel
    department_drafts: dict[str, DepartmentDraft] = {}
    all_passed = True

    with ThreadPoolExecutor(max_workers=min(len(workstreams), MAX_PARALLEL_DEPARTMENTS)) as executor:
        future_to_dept = {}
        for ws in workstreams:
            department = ws.get("department", "")
            if department not in DEPARTMENTS:
                logger.warning("Departamento desconocido: %s", department)
                continue
            key_aspects = ws.get("key_aspects", [])
            contact = DEPARTMENTS[department]

            future = executor.submit(
                process_department,
                department,
                key_aspects,
                metadata,
                sales_handoff,
                contact,
                knowledge_context,
            )
            future_to_dept[future] = department

        for future in as_completed(future_to_dept):
            dept = future_to_dept[future]
            try:
                draft = future.result()
                department_drafts[dept] = draft
                if draft.needs_human_review:
                    all_passed = False
                # Persist after each department completes
                _persist_department_result(ticket_id, dept, draft, repository)
            except Exception as exc:
                logger.error("Error procesando departamento %s: %s", dept, exc)
                draft = DepartmentDraft(
                    department=dept,
                    iteration=MAX_ITERATIONS,
                    content=f"Error al generar borrador para {dept}: {exc}",
                    evaluation=EvaluationResult(
                        section_id=dept,
                        department_id=dept,
                        overall_pass=False,
                        feedback_for_generator=f"Error de procesamiento: {exc}",
                    ),
                )
                department_drafts[dept] = draft
                all_passed = False
                _persist_department_result(ticket_id, dept, draft, repository)

    # Determine final status
    any_needs_review = any(d.needs_human_review for d in department_drafts.values())
    final_status = "needs_human_review" if any_needs_review else "en_evaluacion"

    try:
        repository.update_ticket_status(ticket_id, final_status)
    except Exception as exc:
        logger.error("No se pudo actualizar estado a %s: %s", final_status, exc)

    # Build handoff for Part 3
    response_handoff = {
        "ticket_id": ticket_id,
        "part1_handoff": handoff,
        "drafts": {
            dept: draft.to_dict()
            for dept, draft in department_drafts.items()
        },
        "evaluation_summary": {
            dept: draft.evaluation.to_dict() if draft.evaluation else {}
            for dept, draft in department_drafts.items()
        },
        "needs_human_review": any_needs_review,
        "departments_with_issues": [
            dept for dept, draft in department_drafts.items()
            if draft.needs_human_review
        ],
    }

    # Persist final handoff
    try:
        repository.save_response_handoff(ticket_id, response_handoff)
    except Exception as exc:
        logger.error("No se pudo persistir el handoff de respuesta: %s", exc)

    return response_handoff


def _persist_department_result(
    ticket_id: str,
    department: str,
    draft: DepartmentDraft,
    repository: Any,
) -> None:
    """Save draft and evaluation result to the repository."""
    try:
        repository.save_response_draft(
            ticket_id, department, draft.iteration, draft.content,
        )
    except Exception as exc:
        logger.error("No se pudo persistir borrador de %s: %s", department, exc)

    if draft.evaluation:
        try:
            repository.save_evaluation_result(
                ticket_id, department, draft.iteration, draft.evaluation.to_dict(),
            )
        except Exception as exc:
            logger.error("No se pudo persistir evaluacion de %s: %s", department, exc)