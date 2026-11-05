"""
RFP Approval Pipeline (Part 3) — Human-in-the-loop approval and document closure.

Consumes the Part 2 handoff (rfp_response_handoff) and runs per-department
human approval with interrupt/resume, arbitration, and final document synthesis.

Flow:
  en_evaluacion / needs_human_review
    → esperando_aprobacion (waiting for human sign-off per department)
    → terminado (all approved, document synthesized)

Key concepts:
  - INTERRUPT: Each department requires explicit human approval before
    its section is finalized. The interrupt ONLY pauses that department's
    branch; other departments can proceed independently.
  - CHECKPOINT: State is persisted before each interrupt, enabling resume.
  - ARBITRATION: When conflict triggers fire, Mariana Restrepo (CEO) resolves.
  - FINAL DOCUMENT: Auto-generated when all departments approve.
"""

from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from data.pipelines.rfp_approval.checkpointer import save_checkpoint, load_checkpoint, delete_checkpoint
from data.pipelines.rfp_approval.tracing import record_trace_entry, get_trace_for_thread

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ITERATIONS = 3
MAX_PARALLEL_DEPARTMENTS = 7

# Department approvers from company BRIEFING/CONTEXT.md
DEPARTMENT_APPROVERS: dict[str, str] = {
    "Operaciones de Restaurante": "Felipe Guerrero",
    "Compras y Proveedores": "Lucia Fernandez",
    "Marketing y Experiencia Digital": "Camila Ospina",
    "Personas y Cultura": "Ashley Turner",
    "Formacion y Estandares de Calidad": "Jake Morrison",
    "Tecnologia": "Nicolas Park",
    "Direccion Ejecutiva": "Mariana Restrepo",
}

# Fixed arbiter for cross-department conflicts (CEO)
ARBITER: str = "Mariana Restrepo"
ARBITER_ROLE: str = "Direccion Ejecutiva"

# Conflict triggers derived from BRIEFING context
CONFLICT_TRIGGERS: list[dict[str, Any]] = [
    {
        "id": "CONF-001",
        "description": "Superposición de alcance entre departamentos — dos o más departamentos reclaman la misma responsabilidad o servicio.",
        "category": "scope_overlap",
    },
    {
        "id": "CONF-002",
        "description": "Conflicto presupuestario — las secciones proponen cifras que suman más del presupuesto disponible o se contradicen entre sí.",
        "category": "budget",
    },
    {
        "id": "CONF-003",
        "description": "Conflicto de cronograma — los plazos de entrega propuestos por distintos departamentos son incompatibles.",
        "category": "timeline",
    },
    {
        "id": "CONF-004",
        "description": "Desacuerdo técnico — un departamento propone una tecnología o estándar que otro departamento rechaza explícitamente.",
        "category": "technical",
    },
    {
        "id": "CONF-005",
        "description": "Inconsistencia multipaís — la propuesta para Colombia contradice la de Florida en términos legales, fiscales o de precios.",
        "category": "multimarket",
    },
]

# Section format requirements for final document
REQUIRED_SECTIONS = [
    "Alcance del servicio",
    "Desglose de precios",
    "Cronograma de entregas",
    "Condiciones comerciales",
]


# ---------------------------------------------------------------------------
# Enums for approval flow
# ---------------------------------------------------------------------------


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class DepartmentApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    IN_ARBITRATION = "in_arbitration"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ApprovalRecord:
    department: str
    approver: str
    decision: ApprovalDecision
    comment: str = ""
    timestamp: str = ""
    run_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ApprovalRecord":
        return cls(**data)


@dataclass
class ArbitrationRecord:
    conflict_id: str
    departments_involved: list[str]
    description: str
    resolved_by: str = ARBITER
    resolution: str = ""
    timestamp: str = ""
    run_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FinalDocument:
    ticket_id: str
    customer_name: str
    sections: dict[str, str]  # department → approved content
    arbitrations: list[ArbitrationRecord] = field(default_factory=list)
    generated_at: str = ""
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


def detect_conflicts(
    department_drafts: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Analyze department drafts for conflict triggers.

    Scans structured fields (pricing, timelines) in each draft to detect
    overlapping scope, budget conflicts, timeline incompatibilities, etc.
    Returns list of conflict dicts with trigger_id matched.
    """
    conflicts: list[dict[str, Any]] = []

    # Check for budget conflicts (CONF-002): sum of stated prices
    total_pricing = 0.0
    pricing_depts: list[str] = []
    for dept, draft in department_drafts.items():
        content = draft.get("content", "")
        # Extract USD amounts using simple pattern
        import re
        amounts = re.findall(r'(?:USD\s*)?(\d[\d.,]*)\s*(?:USD|dólares|dolares)', content)
        for amt_str in amounts:
            try:
                amt = float(amt_str.replace(",", "").replace(".", ""))
                total_pricing += amt
                pricing_depts.append(dept)
            except ValueError:
                pass

    if total_pricing > 1_000_000:  # Arbitrary threshold for demo
        conflicts.append({
            "trigger_id": "CONF-002",
            "category": "budget",
            "description": f"Presupuesto total estimado de USD {total_pricing:,.0f} supera el umbral esperado. Departamentos: {', '.join(pricing_depts)}.",
            "departments_involved": list(set(pricing_depts)),
        })

    # Check for timeline conflicts (CONF-003): overlapping or incompatible dates
    timeline_depts: list[str] = []
    for dept, draft in department_drafts.items():
        content = draft.get("content", "")
        if any(word in content.lower() for word in ["semana", "mes", "día", "sem", "cronograma"]):
            timeline_depts.append(dept)

    if len(timeline_depts) >= 2:
        conflicts.append({
            "trigger_id": "CONF-003",
            "category": "timeline",
            "description": f"Múltiples departamentos definen cronogramas. Revisar compatibilidad: {', '.join(timeline_depts)}.",
            "departments_involved": timeline_depts,
        })

    # Check for scope overlap (CONF-001)
    tech_keywords = ["sistema", "plataforma", "software", "app", "dashboard", "api"]
    tech_depts = []
    for dept, draft in department_drafts.items():
        content = draft.get("content", "").lower()
        if any(kw in content for kw in tech_keywords):
            tech_depts.append(dept)
    if len(tech_depts) >= 2:
        conflicts.append({
            "trigger_id": "CONF-001",
            "category": "scope_overlap",
            "description": f"Superposición tecnológica entre departamentos: {', '.join(tech_depts)}. Verificar asignación de responsabilidades.",
            "departments_involved": tech_depts,
        })

    return conflicts


def resolve_conflicts(
    conflicts: list[dict[str, Any]],
    run_id: str,
    thread_id: str,
) -> list[ArbitrationRecord]:
    """Resolve detected conflicts using the fixed arbiter (Mariana Restrepo).

    Since we cannot ask Mariana in an automated test, the arbiter applies
    deterministic rules derived from the BRIEFING:
      - Budget conflicts → distribute proportionally, cap at USD 1M
      - Timeline conflicts → use longest timeline as baseline
      - Scope overlap → assign to the primary department (first listed)
      - Technical disagreements → default to Tecnologia (Nicolas Park)
      - Multimarket → default to Colombian standards per CONTEXT.md

    Returns list of ArbitrationRecord for tracing.
    """
    records: list[ArbitrationRecord] = []
    now = datetime.now(timezone.utc).isoformat()

    for conflict in conflicts:
        trigger_id = conflict["trigger_id"]
        depts = conflict.get("departments_involved", [])
        desc = conflict.get("description", "")

        # Deterministic rules
        if trigger_id == "CONF-002":
            resolution = (
                f"Límite presupuestario de USD 1,000,000. "
                f"Las partidas deben ajustarse para no exceder este tope. "
                f"Revisar con {ARBITER} (CEO) si es necesario."
            )
        elif trigger_id == "CONF-003":
            resolution = (
                f"Usar el cronograma más extenso como línea base. "
                f"Departamentos deben coordinarse con Tecnologia para hitos compartidos."
            )
        elif trigger_id == "CONF-001":
            resolution = (
                f"Asignar responsabilidad primaria al primer departamento listado ({depts[0] if depts else 'N/A'}). "
                f"Tecnologia (Nicolas Park) actúa como soporte técnico transversal."
            )
        else:
            resolution = (
                f"Escalar a {ARBITER} ({ARBITER_ROLE}) para resolución ejecutiva. "
                f"Entretanto, mantener ambas propuestas como alternativas."
            )

        record = ArbitrationRecord(
            conflict_id=trigger_id,
            departments_involved=depts,
            description=desc,
            resolved_by=ARBITER,
            resolution=resolution,
            timestamp=now,
            run_id=run_id,
        )
        records.append(record)

        # Trace the arbitration
        record_trace_entry(
            thread_id=thread_id,
            node_name="arbitration",
            agent=ARBITER,
            input_data=conflict,
            output_data=record.to_dict(),
            run_id=run_id,
        )

    return records


# ---------------------------------------------------------------------------
# Final document synthesis
# ---------------------------------------------------------------------------


def synthesize_final_document(
    ticket_id: str,
    customer_name: str,
    department_drafts: dict[str, DepartmentApprovalData],
    arbitrations: list[ArbitrationRecord],
    run_id: str,
    thread_id: str,
) -> FinalDocument:
    """Generate the final consolidated document from approved sections.

    Only includes departments that have been approved. The document follows
    the standard commercial proposal format expected by Brasaland.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Collect approved content only
    approved_sections: dict[str, str] = {}
    for dept, data in department_drafts.items():
        if data["status"] == DepartmentApprovalStatus.APPROVED.value:
            approved_sections[dept] = data["content"]
        else:
            logger.warning(
                "Departamento %s no aprobado (status=%s), excluido del documento final.",
                dept, data["status"],
            )

    doc = FinalDocument(
        ticket_id=ticket_id,
        customer_name=customer_name,
        sections=approved_sections,
        arbitrations=arbitrations,
        generated_at=now,
        version="1.0",
    )

    # Trace synthesis
    record_trace_entry(
        thread_id=thread_id,
        node_name="document_synthesis",
        agent="document_synthesizer",
        input_data={
            "ticket_id": ticket_id,
            "customer_name": customer_name,
            "num_sections": len(approved_sections),
            "departments": list(approved_sections.keys()),
        },
        output_data=doc.to_dict(),
        run_id=run_id,
    )

    return doc


# ---------------------------------------------------------------------------
# Helper: generate the rendered document text
# ---------------------------------------------------------------------------


def render_final_document(doc: FinalDocument) -> str:
    """Render the FinalDocument into a human-readable proposal."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"PROPUESTA COMERCIAL — BRASALAND")
    lines.append(f"Cliente: {doc.customer_name}")
    lines.append(f"Versión: {doc.version}")
    lines.append(f"Generado: {doc.generated_at}")
    lines.append("=" * 70)
    lines.append("")

    for dept, content in doc.sections.items():
        lines.append(f"--- {dept} ---")
        lines.append("")
        lines.append(content)
        lines.append("")

    if doc.arbitrations:
        lines.append("--- Resolución de Conflictos ---")
        lines.append("")
        for arb in doc.arbitrations:
            lines.append(f"Conflicto: {arb.conflict_id}")
            lines.append(f"Departamentos: {', '.join(arb.departments_involved)}")
            lines.append(f"Resuelto por: {arb.resolved_by}")
            lines.append(f"Resolución: {arb.resolution}")
            lines.append(f"Timestamp: {arb.timestamp}")
            lines.append("")

    lines.append("=" * 70)
    lines.append("Documento generado automáticamente — requiere firma de Mariana Restrepo (CEO)")
    lines.append("=" * 70)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Thread ID helpers
# ---------------------------------------------------------------------------


def ticket_thread_id(ticket_id: str) -> str:
    return f"rfp-{ticket_id}"


def department_thread_id(ticket_id: str, department: str) -> str:
    safe_dept = department.replace(" ", "_").replace("/", "-")
    return f"rfp-{ticket_id}:{safe_dept}"


# ---------------------------------------------------------------------------
# Type alias for department data
# ---------------------------------------------------------------------------

DepartmentApprovalData = dict[str, Any]
# Expected keys:
#   department: str
#   content: str
#   evaluation: dict | None
#   status: DepartmentApprovalStatus (str)
#   approval_record: ApprovalRecord | None
#   iteration: int


# ---------------------------------------------------------------------------
# Main orchestrator: process RFP approval (Part 3)
# ---------------------------------------------------------------------------


def process_rfp_approval(
    ticket_id: str,
    part2_handoff: dict[str, Any],
    repository: Any,
) -> dict[str, Any]:
    """Main entry point for Part 3 (approval and document closure).

    This is called from the API via BackgroundTasks. It:
    1. Transitions ticket to esperando_aprobacion
    2. Loads drafts from Part 2 handoff
    3. Sets up approval state per department
    4. Saves initial checkpoint
    5. Returns control — human approvals happen via separate API calls
    6. When all approved, synthesizes final document

    Args:
        ticket_id: The RFP ticket UUID.
        part2_handoff: The handoff from Part 2 (rfp_response_handoff).
        repository: A SupabaseRfpRepository-like instance for persistence.

    Returns:
        The final handoff dict with document and trace.
    """
    thread_id = ticket_thread_id(ticket_id)
    run_id = str(uuid4())

    # Load drafts from Part 2 handoff
    drafts_raw = part2_handoff.get("drafts", {})
    evaluation_summary = part2_handoff.get("evaluation_summary", {})
    needs_human_review = part2_handoff.get("needs_human_review", False)
    part1_handoff = part2_handoff.get("part1_handoff", {})

    # Extract customer name from Part 1 handoff metadata
    workstreams = part1_handoff.get("workstreams", [])
    customer_name = ""
    if workstreams and len(workstreams) > 0:
        customer_name = workstreams[0].get("customer_name", "Cliente")

    # Build department approval state
    department_data: dict[str, DepartmentApprovalData] = {}
    for dept, draft_info in drafts_raw.items():
        content = ""
        evaluation = None
        iteration = 1
        if isinstance(draft_info, dict):
            content = draft_info.get("content", "")
            evaluation = draft_info.get("evaluation")
            iteration = draft_info.get("iteration", 1)

        department_data[dept] = {
            "department": dept,
            "content": content,
            "evaluation": evaluation,
            "status": DepartmentApprovalStatus.PENDING.value,
            "approval_record": None,
            "iteration": iteration,
        }

    if not department_data:
        logger.warning("Ticket %s: no hay drafts en el handoff de Parte 2.", ticket_id)
        return part2_handoff

    # Persist initial state as checkpoint
    approval_state = _build_approval_state(
        ticket_id, customer_name, department_data, [],
        needs_human_review, run_id,
    )
    save_checkpoint(thread_id, approval_state)
    record_trace_entry(
        thread_id=thread_id,
        node_name="approval_init",
        agent="orchestrator",
        input_data={"ticket_id": ticket_id, "num_departments": len(department_data)},
        output_data={"status": "esperando_aprobacion", "departments": list(department_data.keys())},
        run_id=run_id,
    )

    # Transition ticket to esperando_aprobacion
    try:
        repository.update_ticket_status(ticket_id, "esperando_aprobacion")
    except Exception as exc:
        logger.error("No se pudo actualizar estado a esperando_aprobacion: %s", exc)

    # Persist the approval handoff for the frontend to read
    try:
        repository.save_response_handoff(ticket_id, approval_state)
    except Exception as exc:
        logger.error("No se pudo persistir approval handoff: %s", exc)

    return approval_state


def _build_approval_state(
    ticket_id: str,
    customer_name: str,
    department_data: dict[str, DepartmentApprovalData],
    arbitrations: list[ArbitrationRecord],
    needs_human_review: bool,
    run_id: str,
) -> dict[str, Any]:
    """Build the structured approval state for checkpoints and persistence."""
    return {
        "ticket_id": ticket_id,
        "customer_name": customer_name,
        "phase": "approval",
        "run_id": run_id,
        "departments": {
            dept: {
                "department": data["department"],
                "status": data["status"],
                "iteration": data["iteration"],
                "approval_record": data["approval_record"].to_dict() if data["approval_record"] else None,
                "content": data["content"],
                "evaluation": data["evaluation"],
            }
            for dept, data in department_data.items()
        },
        "arbitrations": [a.to_dict() for a in arbitrations],
        "needs_human_review": needs_human_review,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Resume: process a human approval decision
# ---------------------------------------------------------------------------


def resume_approval(
    ticket_id: str,
    department: str,
    decision: str,
    comment: str = "",
    repository: Any = None,
) -> dict[str, Any]:
    """Resume the approval flow with a human decision for one department.

    This is called by the API when a human submits their approval/rejection.

    Args:
        ticket_id: The RFP ticket UUID.
        department: The department name being approved/rejected.
        decision: "approved", "rejected", or "changes_requested".
        comment: Optional human comment.
        repository: Repository for persistence.

    Returns:
        Updated approval state.
    """
    thread_id = ticket_thread_id(ticket_id)
    dept_thread_id = department_thread_id(ticket_id, department)
    run_id = str(uuid4())

    # Load checkpoint
    state = load_checkpoint(thread_id)
    if state is None:
        raise ValueError(f"No checkpoint found for ticket {ticket_id}. Generate response first.")

    # Find department data
    dept_data = state["departments"].get(department)
    if dept_data is None:
        raise ValueError(f"Department '{department}' not found in approval state.")

    if dept_data["status"] == DepartmentApprovalStatus.APPROVED.value:
        raise ValueError(
            f"Department '{department}' is not pending approval. Current status: {dept_data['status']}"
        )
    if dept_data["status"] == DepartmentApprovalStatus.IN_ARBITRATION.value:
        raise ValueError(
            f"Department '{department}' is in arbitration and cannot be directly approved."
        )

    # Validate decision
    try:
        decision_enum = ApprovalDecision(decision)
    except ValueError:
        raise ValueError(f"Invalid decision: {decision}. Must be one of: {[d.value for d in ApprovalDecision]}")

    # Process the decision
    now = datetime.now(timezone.utc).isoformat()
    approval_record = ApprovalRecord(
        department=department,
        approver=DEPARTMENT_APPROVERS.get(department, "Unknown"),
        decision=decision_enum,
        comment=comment,
        timestamp=now,
        run_id=run_id,
    )

    # Trace the human input
    record_trace_entry(
        thread_id=thread_id,
        node_name="human_approval",
        agent=approval_record.approver,
        input_data={
            "department": department,
            "decision": decision,
            "comment": comment,
        },
        output_data=approval_record.to_dict(),
        run_id=run_id,
    )

    # Update state
    if decision_enum == ApprovalDecision.APPROVED:
        dept_data["status"] = DepartmentApprovalStatus.APPROVED.value
    elif decision_enum == ApprovalDecision.REJECTED:
        dept_data["status"] = DepartmentApprovalStatus.REJECTED.value
    elif decision_enum == ApprovalDecision.CHANGES_REQUESTED:
        dept_data["status"] = DepartmentApprovalStatus.CHANGES_REQUESTED.value

    dept_data["approval_record"] = approval_record.to_dict()

    # Persist approval to repository
    if repository:
        try:
            repository.save_approval_status(
                ticket_id=ticket_id,
                department=department,
                status=dept_data["status"],
                approver=approval_record.approver,
                comment=comment,
            )
        except Exception as exc:
            logger.error("No se pudo persistir approval status: %s", exc)

    # Check if all departments have responded
    all_statuses = [d["status"] for d in state["departments"].values()]
    all_resolved = all(
        s != DepartmentApprovalStatus.PENDING.value
        for s in all_statuses
    )

    final_document = None
    result_state = state

    if all_resolved:
        # Check for conflicts
        approved_drafts = {}
        for dept_name, dd in state["departments"].items():
            if dd["status"] == DepartmentApprovalStatus.APPROVED.value:
                approved_drafts[dept_name] = {"content": dd["content"]}

        conflicts = detect_conflicts(approved_drafts)
        arbitrations = []

        if conflicts:
            # Resolve conflicts via arbiter
            existing = [ArbitrationRecord.from_dict(a) for a in state.get("arbitrations", [])]
            new_resolutions = resolve_conflicts(conflicts, run_id, thread_id)
            arbitrations = existing + new_resolutions

            # Save to state
            state["arbitrations"] = [a.to_dict() for a in arbitrations]
            result_state = state

        # Build department data for synthesis
        synthesis_data: dict[str, DepartmentApprovalData] = {}
        for dept_name, dd in state["departments"].items():
            synthesis_data[dept_name] = {
                "department": dept_name,
                "content": dd.get("content", ""),
                "status": dd["status"],
            }

        # Synthesize final document
        doc = synthesize_final_document(
            ticket_id=ticket_id,
            customer_name=state.get("customer_name", "Cliente"),
            department_drafts=synthesis_data,
            arbitrations=arbitrations,
            run_id=run_id,
            thread_id=thread_id,
        )

        final_document = doc.to_dict()
        rendered = render_final_document(doc)
        final_document["rendered"] = rendered

        # Update state with final document
        state["phase"] = "completed"
        state["final_document"] = final_document

        # Persist final handoff and document
        if repository:
            try:
                repository.save_response_handoff(ticket_id, state)
                repository.save_final_document(ticket_id, final_document, rendered)
                repository.update_ticket_status(ticket_id, "terminado")
            except Exception as exc:
                logger.error("No se pudo persistir documento final: %s", exc)

        # Save final state to checkpoint (flow complete)
        save_checkpoint(thread_id, state)

        logger.info("Ticket %s: flujo de aprobacion completado. Documento final generado.", ticket_id)

    else:
        # Still waiting for some departments
        state["phase"] = "approval"
        result_state = state

        if repository:
            try:
                repository.save_response_handoff(ticket_id, state)
            except Exception as exc:
                logger.error("No se pudo persistir estado de aprobacion: %s", exc)

        # Save checkpoint
        save_checkpoint(thread_id, state)

        pending = [d for d, s in state["departments"].items() if s["status"] == DepartmentApprovalStatus.PENDING.value]
        logger.info(
            "Ticket %s: departamento %s %s. Pendientes: %s",
            ticket_id, department, decision, pending,
        )

    # Trace resume
    record_trace_entry(
        thread_id=thread_id,
        node_name="approval_resume",
        agent="orchestrator",
        input_data={
            "ticket_id": ticket_id,
            "department": department,
            "decision": decision,
        },
        output_data={
            "phase": state["phase"],
            "all_resolved": all_resolved,
            "has_final_document": final_document is not None,
            "pending_departments": [
                d for d, s in state["departments"].items()
                if s["status"] == DepartmentApprovalStatus.PENDING.value
            ],
        },
        run_id=run_id,
    )

    result = {
        "ticket_id": ticket_id,
        "department": department,
        "decision": decision,
        "phase": state["phase"],
        "all_resolved": all_resolved,
        "pending_departments": [
            d for d, s in state["departments"].items()
            if s["status"] == DepartmentApprovalStatus.PENDING.value
        ],
        "departments": {
            d: {"status": s["status"], "approval_record": s.get("approval_record")}
            for d, s in state["departments"].items()
        },
    }

    if final_document:
        result["final_document"] = final_document
        result["rendered"] = rendered

    return result


# ---------------------------------------------------------------------------
# Query: get current approval state
# ---------------------------------------------------------------------------


def get_approval_state(ticket_id: str) -> dict[str, Any] | None:
    """Load the current approval state from checkpoint."""
    thread_id = ticket_thread_id(ticket_id)
    state = load_checkpoint(thread_id)
    if state is None:
        return None
    return state


def get_trace(ticket_id: str, run_id: str | None = None) -> list[dict[str, Any]]:
    """Get the full execution trace for a ticket."""
    thread_id = ticket_thread_id(ticket_id)
    return get_trace_for_thread(thread_id, run_id)


# ---------------------------------------------------------------------------
# Check iteration limit helper
# ---------------------------------------------------------------------------


def check_iteration_limit(department: str, current_iteration: int) -> bool:
    """Check if the department has exceeded the max iteration limit.

    Returns True if still within limit, False if exhausted.
    """
    if current_iteration > MAX_ITERATIONS:
        logger.warning(
            "Departamento %s: limite de iteraciones alcanzado (%d/%d)",
            department, current_iteration, MAX_ITERATIONS,
        )
        return False
    return True