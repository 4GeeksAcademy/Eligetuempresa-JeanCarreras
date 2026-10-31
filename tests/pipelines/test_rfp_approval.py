"""Tests para el pipeline de aprobacion y cierre de RFP (Parte 3).

Cubre:
- Interrupción y reanudación (checkpointer)
- Rechazo y solicitud de cambios
- Detección y arbitraje de conflictos
- Síntesis del documento final
- Trazabilidad (trace) de cada nodo
- Límite de iteraciones
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import ANY

import pytest

from data.pipelines.rfp_approval import (
    ARBITER,
    ARBITER_ROLE,
    CONFLICT_TRIGGERS,
    DEPARTMENT_APPROVERS,
    MAX_ITERATIONS,
    ApprovalDecision,
    ApprovalRecord,
    ArbitrationRecord,
    DepartmentApprovalStatus,
    FinalDocument,
    check_iteration_limit,
    detect_conflicts,
    get_approval_state,
    process_rfp_approval,
    render_final_document,
    resume_approval,
    synthesize_final_document,
    ticket_thread_id,
    department_thread_id,
)
from data.pipelines.rfp_approval.checkpointer import (
    init_db,
    save_checkpoint,
    load_checkpoint,
    delete_checkpoint,
    list_checkpoints,
)
from data.pipelines.rfp_approval.tracing import (
    init_trace_db,
    record_trace_entry,
    get_trace_for_thread,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_checkpoints() -> None:
    """Clean checkpoints and traces before each test."""
    init_db()
    init_trace_db()
    yield
    # Clean up
    for cp in list_checkpoints():
        delete_checkpoint(cp["thread_id"])


@pytest.fixture
def sample_handoff() -> dict:
    """Simulate a Part 2 handoff with drafts for all 7 departments."""
    return {
        "drafts": {
            "Operaciones de Restaurante": {
                "content": (
                    "## Alcance del servicio\n"
                    "Automatizacion de pedidos a proveedores para los 14 locales.\n\n"
                    "## Desglose de precios\n"
                    "Inversion total: 150.000 USD.\n\n"
                    "## Cronograma de entregas\n"
                    "Fase 1: Diagnostico (2 semanas). Fase 2: Implementacion (6 semanas).\n\n"
                    "## Condiciones comerciales\n"
                    "Pago: 50% inicial, 50% contra entrega. Validez: 30 dias."
                ),
                "evaluation": {"overall_pass": True},
                "iteration": 2,
            },
            "Compras y Proveedores": {
                "content": (
                    "## Alcance del servicio\n"
                    "Gestion centralizada de compras con integracion ERP.\n\n"
                    "## Desglose de precios\n"
                    "Inversion: 80.000 USD.\n\n"
                    "## Cronograma de entregas\n"
                    "Migracion en 4 semanas.\n\n"
                    "## Condiciones comerciales\n"
                    "Pago a 60 dias. Descuento 2% por pago anticipado."
                ),
                "evaluation": {"overall_pass": True},
                "iteration": 1,
            },
            "Marketing y Experiencia Digital": {
                "content": (
                    "## Alcance del servicio\n"
                    "Desarrollo de plataforma de fidelizacion multicanal.\n\n"
                    "## Desglose de precios\n"
                    "Presupuesto: 200.000 USD.\n\n"
                    "## Cronograma de entregas\n"
                    "MVP en 3 meses.\n\n"
                    "## Condiciones comerciales\n"
                    "Pago por hitos. Facturacion mensual."
                ),
                "evaluation": {"overall_pass": True},
                "iteration": 2,
            },
            "Personas y Cultura": {
                "content": (
                    "## Alcance del servicio\n"
                    "Programa de formacion en herramientas digitales para 200 empleados.\n\n"
                    "## Desglose de precios\n"
                    "Inversion: 45.000 USD.\n\n"
                    "## Cronograma de entregas\n"
                    "Lanzamiento en 6 semanas.\n\n"
                    "## Condiciones comerciales\n"
                    "Pago trimestral."
                ),
                "evaluation": {"overall_pass": True},
                "iteration": 1,
            },
            "Formacion y Estandares de Calidad": {
                "content": (
                    "## Alcance del servicio\n"
                    "Certificacion de estandares HACCP y capacitacion en manipulacion de alimentos.\n\n"
                    "## Desglose de precios\n"
                    "Inversion: 35.000 USD.\n\n"
                    "## Cronograma de entregas\n"
                    "Auditoria inicial en 3 semanas.\n\n"
                    "## Condiciones comerciales\n"
                    "Pago contra certificacion."
                ),
                "evaluation": {"overall_pass": True},
                "iteration": 1,
            },
            "Tecnologia": {
                "content": (
                    "## Alcance del servicio\n"
                    "Implementacion de API centralizada y dashboard de monitoreo en tiempo real.\n\n"
                    "## Desglose de precios\n"
                    "Inversion: 120.000 USD.\n\n"
                    "## Cronograma de entregas\n"
                    "MVP en 6 semanas.\n\n"
                    "## Condiciones comerciales\n"
                    "Soporte 24/7 incluido. SLA de 2 horas."
                ),
                "evaluation": {"overall_pass": True},
                "iteration": 2,
            },
            "Direccion Ejecutiva": {
                "content": (
                    "## Alcance del servicio\n"
                    "Coordinacion ejecutiva del proyecto y relacion con el cliente.\n\n"
                    "## Desglose de precios\n"
                    "Fee de gestion: 25.000 USD.\n\n"
                    "## Cronograma de entregas\n"
                    "Reuniones semanales de seguimiento.\n\n"
                    "## Condiciones comerciales\n"
                    "Facturacion mensual. Contrato anual."
                ),
                "evaluation": {"overall_pass": True},
                "iteration": 1,
            },
        },
        "evaluation_summary": {
            "total_departments": 7,
            "passed": 7,
            "needs_human_review": False,
        },
        "needs_human_review": False,
        "part1_handoff": {
            "workstreams": [
                {"customer_name": "Brasaland Corp."},
            ],
        },
    }


@pytest.fixture
def in_memory_repository():
    """A simple in-memory repository for testing."""
    class InMemoryRepo:
        def __init__(self):
            self.tickets = {}
            self.handoffs = {}
            self.approvals = {}
            self.final_docs = {}

        def update_ticket_status(self, ticket_id, status):
            self.tickets.setdefault(ticket_id, {})["status"] = status

        def save_response_handoff(self, ticket_id, handoff):
            self.handoffs[ticket_id] = handoff

        def get_response_handoff(self, ticket_id):
            row = self.handoffs.get(ticket_id)
            if row:
                return {"handoff": row}
            return None

        def save_approval_status(self, ticket_id, department, status, approver="", comment=""):
            self.approvals[(ticket_id, department)] = {
                "ticket_id": ticket_id,
                "department": department,
                "status": status,
                "approver": approver,
                "comment": comment,
            }

        def get_approval_status_list(self, ticket_id):
            return [
                v for k, v in self.approvals.items()
                if k[0] == ticket_id
            ]

        def save_final_document(self, ticket_id, content, rendered):
            self.final_docs[ticket_id] = {"content": content, "rendered": rendered}

        def get_final_document(self, ticket_id):
            doc = self.final_docs.get(ticket_id)
            if doc:
                return {**doc, "ticket_id": ticket_id}
            return None

        def save_trace_entry(self, *args, **kwargs):
            pass

        def save_arbitration_record(self, *args, **kwargs):
            pass

    return InMemoryRepo()


# ---------------------------------------------------------------------------
# Checkpointer tests
# ---------------------------------------------------------------------------


def test_checkpointer_save_and_load() -> None:
    """Verify save_checkpoint and load_checkpoint roundtrip."""
    thread_id = "rfp-test-ticket-123"
    state = {"ticket_id": "test-123", "phase": "approval", "departments": {}}

    save_checkpoint(thread_id, state)
    loaded = load_checkpoint(thread_id)

    assert loaded is not None
    assert loaded["ticket_id"] == "test-123"
    assert loaded["phase"] == "approval"


def test_checkpointer_namespacing() -> None:
    """Verify thread_id namespacing for ticket and department levels."""
    ticket_tid = ticket_thread_id("ticket-456")
    dept_tid = department_thread_id("ticket-456", "Operaciones de Restaurante")

    assert ticket_tid == "rfp-ticket-456"
    assert dept_tid == "rfp-ticket-456:Operaciones_de_Restaurante"


def test_checkpointer_delete_and_list() -> None:
    """Verify delete_checkpoint removes state and list_checkpoints works."""
    save_checkpoint("rfp-ticket-a", {"data": "A"})
    save_checkpoint("rfp-ticket-b", {"data": "B"})

    all_cps = list_checkpoints()
    assert len(all_cps) >= 2

    delete_checkpoint("rfp-ticket-a")
    assert load_checkpoint("rfp-ticket-a") is None
    assert load_checkpoint("rfp-ticket-b") is not None


# ---------------------------------------------------------------------------
# Tracing tests
# ---------------------------------------------------------------------------


def test_trace_record_and_retrieve() -> None:
    """Verify trace entries are recorded and retrievable."""
    thread_id = "rfp-trace-test"
    run_id = "run-001"

    # Delete any existing trace entries for this thread+run
    from data.pipelines.rfp_approval.tracing import _get_trace_db_path
    if Path(_get_trace_db_path()).exists():
        import sqlite3
        with sqlite3.connect(str(Path(_get_trace_db_path()))) as conn:
            conn.execute(f"DELETE FROM {"trace_entries"} WHERE thread_id = ? AND run_id = ?", (thread_id, run_id))
            conn.commit()

    record_trace_entry(thread_id, "approval_init", "orchestrator",
                       {"input": "test"}, {"output": "ok"}, run_id)
    record_trace_entry(thread_id, "human_approval", "Felipe Guerrero",
                       {"department": "Operaciones"}, {"decision": "approved"}, run_id)

    entries = get_trace_for_thread(thread_id, run_id)
    assert len(entries) == 2
    assert entries[0]["node_name"] == "approval_init"
    assert entries[1]["node_name"] == "human_approval"
    assert entries[1]["agent"] == "Felipe Guerrero"


# ---------------------------------------------------------------------------
# Approval data model tests
# ---------------------------------------------------------------------------


def test_approval_record_roundtrip() -> None:
    """Verify ApprovalRecord serialization."""
    record = ApprovalRecord(
        department="Test",
        approver="Test User",
        decision=ApprovalDecision.APPROVED,
        comment="Looks good.",
        timestamp="2026-01-01T00:00:00+00:00",
        run_id="run-001",
    )
    as_dict = record.to_dict()
    restored = ApprovalRecord.from_dict(as_dict)

    assert restored.department == "Test"
    assert restored.decision == ApprovalDecision.APPROVED
    assert restored.approver == "Test User"
    assert restored.comment == "Looks good."


def test_arbitration_record_defaults() -> None:
    """Verify ArbitrationRecord uses ARBITER as default resolved_by."""
    record = ArbitrationRecord(
        conflict_id="CONF-001",
        departments_involved=["Dept A", "Dept B"],
        description="Conflict test",
    )
    assert record.resolved_by == ARBITER


# ---------------------------------------------------------------------------
# process_rfp_approval tests
# ---------------------------------------------------------------------------


def test_process_rfp_approval_creates_checkpoint(sample_handoff, in_memory_repository) -> None:
    """Verify process_rfp_approval creates a checkpoint and transitions status."""
    ticket_id = "test-approval-001"

    result = process_rfp_approval(ticket_id, sample_handoff, in_memory_repository)

    assert result["phase"] == "approval"
    assert result["ticket_id"] == ticket_id
    assert "departments" in result
    assert len(result["departments"]) == 7

    # Checkpoint should be loadable
    state = load_checkpoint(ticket_thread_id(ticket_id))
    assert state is not None
    assert state["phase"] == "approval"

    # Status should be esperando_aprobacion
    assert in_memory_repository.tickets.get(ticket_id, {}).get("status") == "esperando_aprobacion"


def test_process_rfp_approval_initial_state_all_pending(sample_handoff, in_memory_repository) -> None:
    """Verify all departments start in PENDING status."""
    ticket_id = "test-approval-002"
    result = process_rfp_approval(ticket_id, sample_handoff, in_memory_repository)

    for dept_name, dept_data in result["departments"].items():
        assert dept_data["status"] == DepartmentApprovalStatus.PENDING.value, \
            f"Department {dept_name} should be pending"


# ---------------------------------------------------------------------------
# Resume approval tests
# ---------------------------------------------------------------------------


def test_approve_department_proceeds(sample_handoff, in_memory_repository) -> None:
    """Verify approving a department updates its status to approved."""
    ticket_id = "test-approve-001"
    process_rfp_approval(ticket_id, sample_handoff, in_memory_repository)

    result = resume_approval(
        ticket_id=ticket_id,
        department="Operaciones de Restaurante",
        decision="approved",
        comment="Borrador aprobado.",
        repository=in_memory_repository,
    )

    assert result["department"] == "Operaciones de Restaurante"
    assert result["decision"] == "approved"
    assert result["phase"] == "approval"  # Still waiting for other depts
    assert "Operaciones de Restaurante" not in result["pending_departments"]


def test_reject_department_returns_to_pending(sample_handoff, in_memory_repository) -> None:
    """Verify rejecting a department sets its status to rejected."""
    ticket_id = "test-reject-001"
    process_rfp_approval(ticket_id, sample_handoff, in_memory_repository)

    result = resume_approval(
        ticket_id=ticket_id,
        department="Marketing y Experiencia Digital",
        decision="rejected",
        comment="Presupuesto excede el limite. Revisar y reducir.",
        repository=in_memory_repository,
    )

    assert result["decision"] == "rejected"
    status = result["departments"]["Marketing y Experiencia Digital"]["status"]
    assert status == DepartmentApprovalStatus.REJECTED.value


def test_approve_all_departments_generates_final_document(sample_handoff, in_memory_repository) -> None:
    """Verify approving all 7 departments generates the final document."""
    ticket_id = "test-final-001"
    process_rfp_approval(ticket_id, sample_handoff, in_memory_repository)

    all_depts = list(sample_handoff["drafts"].keys())

    for i, dept in enumerate(all_depts):
        result = resume_approval(
            ticket_id=ticket_id,
            department=dept,
            decision="approved",
            comment="Aprobado.",
            repository=in_memory_repository,
        )

    # After last approval, all should be resolved
    assert result["all_resolved"] is True
    assert result["phase"] == "completed"
    assert "final_document" in result
    assert "rendered" in result

    # Verify final document structure
    doc = result["final_document"]
    assert doc["ticket_id"] == ticket_id
    assert len(doc["sections"]) == 7  # All 7 departments approved


# ---------------------------------------------------------------------------
# Conflict detection tests
# ---------------------------------------------------------------------------


def test_detect_budget_conflict() -> None:
    """Verify budget conflict is detected when total exceeds threshold."""
    drafts = {
        "Marketing y Experiencia Digital": {
            "content": "Presupuesto: 800.000 USD para plataforma de fidelizacion."
        },
        "Tecnologia": {
            "content": "Inversion total de 500.000 USD en infraestructura."
        },
    }

    conflicts = detect_conflicts(drafts)
    conflict_ids = [c["trigger_id"] for c in conflicts]

    assert "CONF-002" in conflict_ids


def test_detect_scope_overlap() -> None:
    """Verify scope overlap conflict when multiple departments claim tech."""
    drafts = {
        "Marketing": {
            "content": "Desarrollar una app movil para clientes."
        },
        "Tecnologia": {
            "content": "Implementar API centralizada y dashboard."
        },
    }

    conflicts = detect_conflicts(drafts)
    conflict_ids = [c["trigger_id"] for c in conflicts]
    assert "CONF-001" in conflict_ids  # scope overlap via tech keywords


def test_no_conflicts_with_small_budget() -> None:
    """Verify no false positive conflicts with well-scoped budgets."""
    drafts = {
        "Operaciones": {
            "content": "Inversion: 10.000 USD en equipos."
        },
        "Personas": {
            "content": "Presupuesto: 5.000 USD formacion."
        },
    }

    conflicts = detect_conflicts(drafts)
    assert len(conflicts) == 0


# ---------------------------------------------------------------------------
# Arbitration tests
# ---------------------------------------------------------------------------


def test_arbitration_deterministic_resolution(sample_handoff, in_memory_repository) -> None:
    """Verify that arbitration uses deterministic rules, not LLM calls."""
    from data.pipelines.rfp_approval import resolve_conflicts
    import uuid

    # Create an artificial budget conflict
    drafts = {
        "Marketing y Experiencia Digital": {
            "content": "Presupuesto: 2.000.000 USD."
        },
        "Tecnologia": {
            "content": "Inversion: 1.500.000 USD."
        },
    }

    conflicts = detect_conflicts(drafts)
    assert len(conflicts) > 0

    thread_id = ticket_thread_id("test-arb")
    run_id = str(uuid.uuid4())
    resolutions = resolve_conflicts(conflicts, run_id, thread_id)

    assert len(resolutions) > 0
    for rec in resolutions:
        assert rec.resolved_by == ARBITER
        assert rec.resolution != ""
        assert rec.conflict_id in ["CONF-001", "CONF-002", "CONF-003"]


# ---------------------------------------------------------------------------
# Final document synthesis tests
# ---------------------------------------------------------------------------


def test_synthesize_final_document_includes_all_approved_sections() -> None:
    """Verify final document contains all approved department sections."""
    department_drafts = {
        "Operaciones de Restaurante": {
            "department": "Operaciones de Restaurante",
            "content": "## Alcance\nSistema de pedidos automatizados.",
            "status": DepartmentApprovalStatus.APPROVED.value,
        },
        "Tecnologia": {
            "department": "Tecnologia",
            "content": "## Alcance\nAPI centralizada.",
            "status": DepartmentApprovalStatus.APPROVED.value,
        },
        "Marketing": {
            "department": "Marketing",
            "content": "## Alcance\nPlataforma de fidelizacion.",
            "status": DepartmentApprovalStatus.REJECTED.value,  # Should NOT be included
        },
    }

    import uuid
    run_id = str(uuid.uuid4())
    thread_id = ticket_thread_id("test-synth")

    doc = synthesize_final_document(
        ticket_id="test-synth",
        customer_name="Brasaland Corp.",
        department_drafts=department_drafts,
        arbitrations=[],
        run_id=run_id,
        thread_id=thread_id,
    )

    assert doc.ticket_id == "test-synth"
    assert "Operaciones de Restaurante" in doc.sections
    assert "Tecnologia" in doc.sections
    assert "Marketing" not in doc.sections  # Rejected, should be excluded


def test_render_final_document_format() -> None:
    """Verify rendered document has expected sections and headers."""
    doc = FinalDocument(
        ticket_id="render-test",
        customer_name="Test Corp",
        sections={
            "Operaciones": "## Alcance\nTest content.",
        },
        arbitrations=[
            ArbitrationRecord(
                conflict_id="CONF-002",
                departments_involved=["A", "B"],
                description="Budget conflict",
                resolution="Cap at 1M",
                timestamp="2026-01-01T00:00:00+00:00",
            ),
        ],
        generated_at="2026-01-01T00:00:00+00:00",
    )

    rendered = render_final_document(doc)

    assert "PROPUESTA COMERCIAL" in rendered
    assert "BRASALAND" in rendered
    assert "Test Corp" in rendered
    assert "Operaciones" in rendered
    assert "CONF-002" in rendered
    assert "Mariana Restrepo" in rendered
    assert "Resolución de Conflictos" in rendered


# ---------------------------------------------------------------------------
# Iteration limit tests
# ---------------------------------------------------------------------------


def test_check_iteration_within_limit() -> None:
    """Verify check_iteration_limit returns True within bounds."""
    assert check_iteration_limit("Test", 1) is True
    assert check_iteration_limit("Test", MAX_ITERATIONS) is True


def test_check_iteration_exhausted() -> None:
    """Verify check_iteration_limit returns False when exhausted."""
    assert check_iteration_limit("Test", MAX_ITERATIONS + 1) is False
    assert check_iteration_limit("Test", 999) is False


# ---------------------------------------------------------------------------
# Department approvers mapping tests
# ---------------------------------------------------------------------------


def test_department_approvers_include_all_departments() -> None:
    """Verify every department has a designated approver."""
    assert DEPARTMENT_APPROVERS["Operaciones de Restaurante"] == "Felipe Guerrero"
    assert DEPARTMENT_APPROVERS["Compras y Proveedores"] == "Lucia Fernandez"
    assert DEPARTMENT_APPROVERS["Marketing y Experiencia Digital"] == "Camila Ospina"
    assert DEPARTMENT_APPROVERS["Personas y Cultura"] == "Ashley Turner"
    assert DEPARTMENT_APPROVERS["Formacion y Estandares de Calidad"] == "Jake Morrison"
    assert DEPARTMENT_APPROVERS["Tecnologia"] == "Nicolas Park"
    assert DEPARTMENT_APPROVERS["Direccion Ejecutiva"] == "Mariana Restrepo"
    assert ARBITER == "Mariana Restrepo"


# ---------------------------------------------------------------------------
# Conflict triggers fixture tests
# ---------------------------------------------------------------------------


def test_conflict_triggers_include_all_categories() -> None:
    """Verify that conflict triggers cover all defined categories."""
    categories = {t["category"] for t in CONFLICT_TRIGGERS}
    assert "scope_overlap" in categories
    assert "budget" in categories
    assert "timeline" in categories
    assert "technical" in categories
    assert "multimarket" in categories


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_approve_nonexistent_department(sample_handoff, in_memory_repository) -> None:
    """Verify error handling when approving a non-existent department."""
    ticket_id = "test-edge-001"
    process_rfp_approval(ticket_id, sample_handoff, in_memory_repository)

    with pytest.raises(ValueError, match="not found in approval state"):
        resume_approval(
            ticket_id=ticket_id,
            department="Departamento Inexistente",
            decision="approved",
            repository=in_memory_repository,
        )


def test_approve_already_approved_department(sample_handoff, in_memory_repository) -> None:
    """Verify error handling when approving an already approved department."""
    ticket_id = "test-edge-002"
    process_rfp_approval(ticket_id, sample_handoff, in_memory_repository)

    resume_approval(
        ticket_id=ticket_id,
        department="Operaciones de Restaurante",
        decision="approved",
        repository=in_memory_repository,
    )

    with pytest.raises(ValueError, match="not pending"):
        resume_approval(
            ticket_id=ticket_id,
            department="Operaciones de Restaurante",
            decision="approved",
            repository=in_memory_repository,
        )


def test_invalid_decision(sample_handoff, in_memory_repository) -> None:
    """Verify error handling for invalid approval decisions."""
    ticket_id = "test-edge-003"
    process_rfp_approval(ticket_id, sample_handoff, in_memory_repository)

    with pytest.raises(ValueError):
        resume_approval(
            ticket_id=ticket_id,
            department="Operaciones de Restaurante",
            decision="invalid_decision",
            repository=in_memory_repository,
        )


def test_process_without_checkpoint_raises_error() -> None:
    """Verify resume_approval without a checkpoint raises ValueError."""
    with pytest.raises(ValueError, match="No checkpoint found"):
        resume_approval(
            ticket_id="nonexistent-ticket",
            department="Test",
            decision="approved",
        )


def test_approve_with_changes_requested(sample_handoff, in_memory_repository) -> None:
    """Verify requesting changes sets the correct status."""
    ticket_id = "test-changes-001"
    process_rfp_approval(ticket_id, sample_handoff, in_memory_repository)

    result = resume_approval(
        ticket_id=ticket_id,
        department="Personas y Cultura",
        decision="changes_requested",
        comment="Agregar programa de onboarding digital.",
        repository=in_memory_repository,
    )

    status = result["departments"]["Personas y Cultura"]["status"]
    assert status == DepartmentApprovalStatus.CHANGES_REQUESTED.value


def test_pending_departments_list(sample_handoff, in_memory_repository) -> None:
    """Verify pending_departments shrinks as approvals happen."""
    ticket_id = "test-pending-001"
    process_rfp_approval(ticket_id, sample_handoff, in_memory_repository)

    r1 = resume_approval(ticket_id=ticket_id, department="Operaciones de Restaurante",
                          decision="approved", repository=in_memory_repository)
    assert len(r1["pending_departments"]) == 6

    r2 = resume_approval(ticket_id=ticket_id, department="Tecnologia",
                          decision="approved", repository=in_memory_repository)
    assert len(r2["pending_departments"]) == 5


def test_trace_records_all_human_approvals(sample_handoff, in_memory_repository) -> None:
    """Verify that each human approval creates a trace entry."""
    ticket_id = "test-trace-001"

    # Clean existing trace entries for this ticket
    thread_id = ticket_thread_id(ticket_id)
    from data.pipelines.rfp_approval.tracing import _get_trace_db_path
    if Path(_get_trace_db_path()).exists():
        import sqlite3
        with sqlite3.connect(str(Path(_get_trace_db_path()))) as conn:
            conn.execute(f"DELETE FROM {"trace_entries"} WHERE thread_id = ?", (thread_id,))
            conn.commit()

    process_rfp_approval(ticket_id, sample_handoff, in_memory_repository)

    resume_approval(
        ticket_id=ticket_id,
        department="Operaciones de Restaurante",
        decision="approved",
        comment="Aprobado.",
        repository=in_memory_repository,
    )
    resume_approval(
        ticket_id=ticket_id,
        department="Tecnologia",
        decision="approved",
        comment="Ok.",
        repository=in_memory_repository,
    )

    trace = get_trace_for_thread(thread_id)
    trace_nodes = [t["node_name"] for t in trace]
    assert "approval_init" in trace_nodes
    assert "human_approval" in trace_nodes
    assert "approval_resume" in trace_nodes

    # Count human_approval entries
    human_entries = [t for t in trace if t["node_name"] == "human_approval"]
    assert len(human_entries) == 2


def test_arbiter_fixed_constant() -> None:
    """Verify ARBITER is consistently Mariana Restrepo."""
    assert ARBITER == "Mariana Restrepo"
    assert DEPARTMENT_APPROVERS["Direccion Ejecutiva"] == ARBITER


def test_department_thread_id_safe_naming() -> None:
    """Verify department_thread_id handles spaces and special chars."""
    tid = department_thread_id("t-123", "Marketing y Experiencia Digital")
    assert " " not in tid
    assert ":" in tid
    assert tid.endswith("Marketing_y_Experiencia_Digital")