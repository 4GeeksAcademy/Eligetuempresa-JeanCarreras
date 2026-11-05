"""Test de integración E2E: Parte 1 → Parte 2 → Parte 3.

Simula el flujo completo:
1. Handoff de entrada (Parte 1)
2. Generación y evaluación de borradores (Parte 2) con ask_model mockeado
3. Procesamiento de aprobaciones (Parte 3) con decisiones simuladas para
   los 7 departamentos
4. Arbitraje de conflictos
5. Síntesis del documento final consolidado
6. Trazabilidad completa

Este script es el enlace directo que se menciona en la descripción del PR
para reproducir el ejemplo completo de forma automatizada.
"""

from __future__ import annotations

import json
from pathlib import Path
import uuid
from unittest.mock import ANY

import pytest

from data.pipelines import rfp_response
from data.pipelines.rfp_approval import (
    ARBITER,
    DEPARTMENT_APPROVERS,
    process_rfp_approval,
    resume_approval,
    get_approval_state,
    render_final_document,
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
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_KNOWLEDGE_CONTEXT = (
    "Brasaland opera 14 locales en Colombia y 2 en Florida, EE.UU. "
    "Certificación HACCP obligatoria para todos los locales. "
    "Presupuesto total aproximado: 500.000 USD para el proyecto de transformación digital."
)


class InMemoryRepo:
    """Repositorio en memoria que soporta los métodos que usan P2 y P3."""

    def __init__(self):
        self.tickets: dict[str, dict] = {}
        self.handoffs: dict[str, dict] = {}
        self.approvals: dict[tuple[str, str], dict] = {}
        self.final_docs: dict[str, dict] = {}
        self.traces: list[dict] = []
        self.arbitrations: list[dict] = []

    # -- Part 2 methods --
    def update_ticket_status(self, ticket_id: str, status: str) -> None:
        self.tickets.setdefault(ticket_id, {})["status"] = status

    def save_response_draft(self, ticket_id: str, department: str, iteration: int, content: str) -> None:
        pass

    def save_evaluation_result(self, ticket_id: str, department: str, iteration: int, evaluation: dict) -> None:
        pass

    def save_response_handoff(self, ticket_id: str, handoff: dict) -> None:
        self.handoffs[ticket_id] = handoff

    def get_response_handoff(self, ticket_id: str) -> dict | None:
        row = self.handoffs.get(ticket_id)
        if row:
            return {"handoff": row}
        return None

    # -- Part 3 methods --
    def save_approval_status(self, ticket_id: str, department: str,
                             status: str, approver: str = "", comment: str = "") -> None:
        self.approvals[(ticket_id, department)] = {
            "ticket_id": ticket_id,
            "department": department,
            "status": status,
            "approver": approver,
            "comment": comment,
        }

    def get_approval_status_list(self, ticket_id: str) -> list[dict]:
        return [
            v for k, v in self.approvals.items()
            if k[0] == ticket_id
        ]

    def save_final_document(self, ticket_id: str, content: dict, rendered: str) -> None:
        self.final_docs[ticket_id] = {"content": content, "rendered": rendered}

    def get_final_document(self, ticket_id: str) -> dict | None:
        doc = self.final_docs.get(ticket_id)
        if doc:
            return {**doc, "ticket_id": ticket_id}
        return None

    def save_trace_entry(self, ticket_id: str, node_name: str, agent: str,
                         input_preview: str, output_preview: str,
                         full_input: dict | None, full_output: dict | None,
                         run_id: str, department: str | None = None) -> None:
        self.traces.append({
            "ticket_id": ticket_id,
            "node_name": node_name,
            "agent": agent,
            "department": department,
            "run_id": run_id,
        })

    def save_arbitration_record(self, ticket_id: str, conflict_id: str,
                                 departments_involved: list[str],
                                 description: str, resolution: str,
                                 resolved_by: str = ARBITER) -> None:
        self.arbitrations.append({
            "ticket_id": ticket_id,
            "conflict_id": conflict_id,
            "resolved_by": resolved_by,
        })


# ---------------------------------------------------------------------------
# Handoff de entrada simulado (Parte 1)
# ---------------------------------------------------------------------------

SALES_HANDOFF_TEXT = (
    "Cliente: Brasaland Corp. Solicita propuesta completa para la transformación "
    "digital de sus operaciones. Incluye automatización de pedidos a proveedores, "
    "gestión centralizada de compras, plataforma de fidelización multicanal, "
    "formación del personal en herramientas digitales, certificación HACCP, "
    "API centralizada con dashboard en tiempo real, y coordinación ejecutiva. "
    "Presupuesto estimado: 500.000 USD. Plazo de respuesta: 30 días."
)

WORKSTREAMS = [
    {
        "department": "Operaciones de Restaurante",
        "customer_name": "Brasaland Corp.",
        "request_title": "Automatización de pedidos a proveedores",
        "response_deadline": "2026-12-15",
        "estimated_value": 150000,
        "currency": "USD",
        "key_aspects": [
            {"aspect": "Sistema de pedidos", "request": "Implementar sistema automatizado de pedidos a proveedores para los 14 locales", "evidence": "necesitamos automatizar pedidos", "missing_information": []},
            {"aspect": "Alertas de stock", "request": "Alertas automáticas de stock mínimo", "evidence": "alertas de inventario", "missing_information": []},
            {"aspect": "Reportes", "request": "Dashboard de gestión de pedidos", "evidence": "reportes de operaciones", "missing_information": ["volumen mensual"]},
        ],
    },
    {
        "department": "Compras y Proveedores",
        "customer_name": "Brasaland Corp.",
        "request_title": "Gestión centralizada de compras",
        "response_deadline": "2026-12-15",
        "estimated_value": 80000,
        "currency": "USD",
        "key_aspects": [
            {"aspect": "Centralización", "request": "Sistema centralizado de compras con integración ERP", "evidence": "compras centralizadas", "missing_information": []},
            {"aspect": "Proveedores", "request": "Catálogo unificado de proveedores", "evidence": "gestión de proveedores", "missing_information": ["número de proveedores"]},
        ],
    },
    {
        "department": "Marketing y Experiencia Digital",
        "customer_name": "Brasaland Corp.",
        "request_title": "Plataforma de fidelización multicanal",
        "response_deadline": "2026-12-15",
        "estimated_value": 200000,
        "currency": "USD",
        "key_aspects": [
            {"aspect": "Fidelización", "request": "Plataforma multicanal de fidelización con app móvil", "evidence": "fidelización de clientes", "missing_information": []},
            {"aspect": "CRM", "request": "Integración con CRM existente", "evidence": "CRM marketing", "missing_information": ["plataforma CRM actual"]},
        ],
    },
    {
        "department": "Personas y Cultura",
        "customer_name": "Brasaland Corp.",
        "request_title": "Formación en herramientas digitales",
        "response_deadline": "2026-12-15",
        "estimated_value": 45000,
        "currency": "USD",
        "key_aspects": [
            {"aspect": "Capacitación", "request": "Programa de formación para 200 empleados en herramientas digitales", "evidence": "capacitación digital", "missing_information": []},
            {"aspect": "Onboarding", "request": "Plan de onboarding digital", "evidence": "inducción digital", "missing_information": ["rotación mensual"]},
        ],
    },
    {
        "department": "Formacion y Estandares de Calidad",
        "customer_name": "Brasaland Corp.",
        "request_title": "Certificación HACCP y capacitación",
        "response_deadline": "2026-12-15",
        "estimated_value": 35000,
        "currency": "USD",
        "key_aspects": [
            {"aspect": "HACCP", "request": "Certificación en estándares HACCP para todos los locales", "evidence": "certificación HACCP", "missing_information": []},
            {"aspect": "Manipulación", "request": "Capacitación en manipulación de alimentos", "evidence": "manipulación alimentos", "missing_information": []},
        ],
    },
    {
        "department": "Tecnologia",
        "customer_name": "Brasaland Corp.",
        "request_title": "API centralizada y dashboard",
        "response_deadline": "2026-12-15",
        "estimated_value": 120000,
        "currency": "USD",
        "key_aspects": [
            {"aspect": "API", "request": "API centralizada para integración de sistemas", "evidence": "API integración", "missing_information": []},
            {"aspect": "Dashboard", "request": "Dashboard de monitoreo en tiempo real", "evidence": "monitoreo tiempo real", "missing_information": ["infraestructura actual"]},
            {"aspect": "SLA", "request": "Soporte 24/7 con SLA de 2 horas", "evidence": "soporte técnico", "missing_information": []},
        ],
    },
    {
        "department": "Direccion Ejecutiva",
        "customer_name": "Brasaland Corp.",
        "request_title": "Coordinación ejecutiva",
        "response_deadline": "2026-12-15",
        "estimated_value": 25000,
        "currency": "USD",
        "key_aspects": [
            {"aspect": "Coordinación", "request": "Coordinación ejecutiva del proyecto y relación con el cliente", "evidence": "coordinación ejecutiva", "missing_information": []},
            {"aspect": "Reportes", "request": "Reportes semanales de avance", "evidence": "reportes dirección", "missing_information": []},
        ],
    },
]

PART1_HANDOFF = {
    "workstreams": WORKSTREAMS,
    "sales_handoff": SALES_HANDOFF_TEXT,
}


# ---------------------------------------------------------------------------
# Simulated LLM responses for Part 2
# ---------------------------------------------------------------------------

DEPARTMENT_DRAFTS_RESPONSES = {
    "Operaciones de Restaurante": (
        "## Alcance del servicio\n"
        "Se implementará un sistema automatizado de pedidos a proveedores para los 14 locales "
        "de Brasaland en Colombia y Florida. El sistema incluirá alertas automáticas de stock "
        "mínimo y un dashboard de gestión de pedidos en tiempo real.\n\n"
        "## Desglose de precios\n"
        "Inversión total estimada: 150.000 USD. Incluye licencias, implementación y capacitación.\n\n"
        "## Cronograma de entregas\n"
        "Fase 1: Diagnóstico (2 semanas). Fase 2: Implementación (6 semanas). "
        "Fase 3: Puesta en marcha (2 semanas).\n\n"
        "## Condiciones comerciales\n"
        "Pago: 50% al inicio, 50% contra entrega. Validez de la oferta: 30 días."
    ),
    "Compras y Proveedores": (
        "## Alcance del servicio\n"
        "Gestión centralizada de compras con integración al ERP corporativo. "
        "Catálogo unificado de proveedores y automatización de órdenes de compra.\n\n"
        "## Desglose de precios\n"
        "Inversión: 80.000 USD. Incluye plataforma, migración de datos y capacitación.\n\n"
        "## Cronograma de entregas\n"
        "Migración en 4 semanas. Capacitación en paralelo.\n\n"
        "## Condiciones comerciales\n"
        "Pago a 60 días. Descuento del 2% por pago anticipado."
    ),
    "Marketing y Experiencia Digital": (
        "## Alcance del servicio\n"
        "Desarrollo de plataforma de fidelización multicanal con app móvil, "
        "integración con CRM existente y campañas automatizadas.\n\n"
        "## Desglose de precios\n"
        "Presupuesto: 200.000 USD. Incluye desarrollo, integración y lanzamiento.\n\n"
        "## Cronograma de entregas\n"
        "MVP en 3 meses. Lanzamiento completo en 5 meses.\n\n"
        "## Condiciones comerciales\n"
        "Pago por hitos: 30% inicial, 40% al MVP, 30% al lanzamiento. Facturación mensual."
    ),
    "Personas y Cultura": (
        "## Alcance del servicio\n"
        "Programa de formación en herramientas digitales para 200 empleados, "
        "incluyendo onboarding digital y evaluaciones de desempeño.\n\n"
        "## Desglose de precios\n"
        "Inversión: 45.000 USD. Incluye plataforma LMS, contenido y certificaciones.\n\n"
        "## Cronograma de entregas\n"
        "Lanzamiento en 6 semanas. Ciclos trimestrales de formación.\n\n"
        "## Condiciones comerciales\n"
        "Pago trimestral. Renovación anual."
    ),
    "Formacion y Estandares de Calidad": (
        "## Alcance del servicio\n"
        "Certificación en estándares HACCP para los 14 locales de Colombia y 2 de Florida. "
        "Capacitación completa en manipulación de alimentos.\n\n"
        "## Desglose de precios\n"
        "Inversión: 35.000 USD. Incluye auditoría inicial, certificación y materiales.\n\n"
        "## Cronograma de entregas\n"
        "Auditoría inicial en 3 semanas. Certificación completa en 8 semanas.\n\n"
        "## Condiciones comerciales\n"
        "Pago contra certificación. Garantía de cumplimiento por 12 meses."
    ),
    "Tecnologia": (
        "## Alcance del servicio\n"
        "Implementación de API centralizada para integración de todos los sistemas, "
        "dashboard de monitoreo en tiempo real, y soporte 24/7 con SLA de 2 horas.\n\n"
        "## Desglose de precios\n"
        "Inversión: 120.000 USD. Incluye desarrollo, infraestructura cloud y soporte.\n\n"
        "## Cronograma de entregas\n"
        "MVP en 6 semanas. Implementación completa en 12 semanas.\n\n"
        "## Condiciones comerciales\n"
        "Soporte 24/7 incluido. SLA de 2 horas para incidentes críticos."
    ),
    "Direccion Ejecutiva": (
        "## Alcance del servicio\n"
        "Coordinación ejecutiva del proyecto, relación con el cliente, "
        "y reportes semanales de avance a la dirección.\n\n"
        "## Desglose de precios\n"
        "Fee de gestión: 25.000 USD anuales.\n\n"
        "## Cronograma de entregas\n"
        "Reuniones semanales de seguimiento. Reportes mensuales de avance.\n\n"
        "## Condiciones comerciales\n"
        "Facturación mensual. Contrato anual renovable."
    ),
}


def _make_fake_ask_model(department: str):
    """Crea un ask_model simulado para el departamento indicado."""
    draft_text = DEPARTMENT_DRAFTS_RESPONSES.get(department, "## Alcance del servicio\nContenido simulado.\n## Desglose de precios\nSimulado.\n## Cronograma de entregas\nSimulado.\n## Condiciones comerciales\nSimulado.")

    def fake_ask_model(system_prompt: str, user_prompt: str, response_format: str = "text") -> str:
        if response_format == "json":
            # Simulate readability evaluation
            return json.dumps({"score": 85, "feedback": "Buena legibilidad.", "passed": True})
        return draft_text

    return fake_ask_model


# ---------------------------------------------------------------------------
# E2E Test: Flujo completo Parte 1 → Parte 2 → Parte 3
# ---------------------------------------------------------------------------


class TestRfpE2EFullFlow:
    """Flujo completo de principio a fin con aprobaciones simuladas."""

    @pytest.fixture(autouse=True)
    def _clean_state(self):
        init_db()
        init_trace_db()
        yield
        # Clean checkpoints
        for cp in list_checkpoints():
            delete_checkpoint(cp["thread_id"])
        # Clean traces for our test threads
        import sqlite3
        from data.pipelines.rfp_approval.tracing import _get_trace_db_path
        if Path(_get_trace_db_path()).exists():
            try:
                with sqlite3.connect(str(Path(_get_trace_db_path()))) as conn:
                    conn.execute(f"DELETE FROM {"trace_entries"} WHERE thread_id LIKE 'rfp-e2e-%'")
                    conn.commit()
            except Exception:
                pass

    @pytest.fixture
    def repo(self):
        return InMemoryRepo()

    def _run_part2(self, ticket_id: str, repo: InMemoryRepo, monkeypatch):
        """Ejecuta process_rfp_response con ask_model mockeado."""
        # Necesitamos mockear ask_model para cada departamento
        # Usamos un side_effect que inspecciona el user_prompt para identificar el departamento
        original_ask = rfp_response.ask_model

        def side_effect_ask(system_prompt: str, user_prompt: str, response_format: str = "text") -> str:
            # Identificar departamento por el system_prompt
            for dept, draft in DEPARTMENT_DRAFTS_RESPONSES.items():
                if dept in system_prompt:
                    if response_format == "json":
                        return json.dumps({"score": 85, "feedback": "Buena legibilidad.", "passed": True})
                    return draft
            # Fallback
            if response_format == "json":
                return json.dumps({"score": 85, "feedback": "Ok.", "passed": True})
            return DEPARTMENT_DRAFTS_RESPONSES["Direccion Ejecutiva"]

        monkeypatch.setattr(rfp_response, "ask_model", side_effect_ask)

        # Also mock knowledge context retrieval
        monkeypatch.setattr(rfp_response, "retrieve_knowledge_context",
                            lambda: SAMPLE_KNOWLEDGE_CONTEXT)

        handoff = rfp_response.process_rfp_response(ticket_id, PART1_HANDOFF, repo)
        return handoff

    def test_full_e2e_flow(self, repo: InMemoryRepo, monkeypatch):
        """Simula RFP de entrada → 7 borradores → 7 aprobaciones → documento final."""
        ticket_id = f"e2e-test-{uuid.uuid4().hex[:8]}"

        # ---- Paso 1: Ejecutar Parte 2 (generación de borradores) ----
        part2_handoff = self._run_part2(ticket_id, repo, monkeypatch)

        # Verificar que Part 2 produjo resultados
        assert "drafts" in part2_handoff
        assert len(part2_handoff["drafts"]) == 7, (
            f"Esperado 7 departamentos, obtenido {len(part2_handoff['drafts'])}"
        )
        dept_names = ["Operaciones de Restaurante", "Compras y Proveedores",
                       "Marketing y Experiencia Digital", "Personas y Cultura",
                       "Formacion y Estandares de Calidad", "Tecnologia",
                       "Direccion Ejecutiva"]
        for dept in dept_names:
            assert dept in part2_handoff["drafts"], f"Falta borrador para {dept}"
            draft_data = part2_handoff["drafts"][dept]
            # Verificar que el draft incluye las 4 secciones requeridas
            content = draft_data.get("content", "")
            assert "Alcance del servicio" in content, f"{dept}: falta sección Alcance"
            assert "Desglose de precios" in content, f"{dept}: falta sección Precios"
            assert "Cronograma de entregas" in content, f"{dept}: falta sección Cronograma"
            assert "Condiciones comerciales" in content, f"{dept}: falta sección Condiciones"

        # ---- Paso 2: Ejecutar Parte 3 (iniciar flujo de aprobación) ----
        approval_state = process_rfp_approval(ticket_id, part2_handoff, repo)

        assert approval_state["phase"] == "approval"
        assert approval_state["ticket_id"] == ticket_id
        assert len(approval_state["departments"]) == 7

        # Verificar estado inicial: todos PENDING
        for dept_name, dept_data in approval_state["departments"].items():
            assert dept_data["status"] == "pending", (
                f"{dept_name}: esperado pending, obtenido {dept_data['status']}"
            )

        # ---- Paso 3: Aprobar departamentos uno por uno (simulando decisión humana) ----
        # (Incluyendo un rechazo y un changes_requested para probar todas las rutas)
        approval_sequence = [
            ("Operaciones de Restaurante", "approved",
             "Borrador completo y alineado con los requerimientos operativos."),
            ("Compras y Proveedores", "approved",
             "Cobertura adecuada de compras centralizadas. Aprobado."),
            ("Marketing y Experiencia Digital", "changes_requested",
             "Incluir plan de métricas de retención y estimación de usuarios activos."),
            # --- Simulamos que Marketing corrige y se aprueba ---
            ("Personas y Cultura", "approved",
             "Programa de formación completo. Aprobado."),
            ("Formacion y Estandares de Calidad", "rejected",
             "No se incluye la certificación para los 2 locales de Florida. Revisar alcance geográfico."),
            # --- Simulamos que Formación corrige ---
            ("Tecnologia", "approved",
             "API centralizada con SLA robusto. Aprobado."),
            ("Direccion Ejecutiva", "approved",
             "Coordinación ejecutiva según lo esperado. Aprobado."),
        ]

        # Procesar las primeras 3 aprobaciones
        for dept, decision, comment in approval_sequence[:3]:
            result = resume_approval(
                ticket_id=ticket_id,
                department=dept,
                decision=decision,
                comment=comment,
                repository=repo,
            )
            assert result["department"] == dept
            assert result["decision"] == decision
            assert result["phase"] == "approval"  # Aún no es la última

        # Verificar que Marketing quedó como changes_requested
        state_after_3 = get_approval_state(ticket_id) or {}
        depts = state_after_3.get("departments", {})
        assert depts["Marketing y Experiencia Digital"]["status"] == "changes_requested"

        # Aprobamos Marketing después de los cambios
        result_mkt = resume_approval(
            ticket_id=ticket_id,
            department="Marketing y Experiencia Digital",
            decision="approved",
            comment="Se agregaron métricas de retención. Aprobado.",
            repository=repo,
        )
        assert result_mkt["decision"] == "approved"

        # Procesamos Personas y Cultura (pendiente del paso anterior)
        result_personas = resume_approval(
            ticket_id=ticket_id,
            department="Personas y Cultura",
            decision="approved",
            comment="Programa de formación completo. Aprobado.",
            repository=repo,
        )
        assert result_personas["decision"] == "approved"
        assert result_personas["phase"] == "approval"

        # Procesamos el rechazo de Formación
        result_form = resume_approval(
            ticket_id=ticket_id,
            department="Formacion y Estandares de Calidad",
            decision="rejected",
            comment="No incluye Florida. Revisar.",
            repository=repo,
        )
        assert result_form["decision"] == "rejected"
        assert result_form["phase"] == "approval"

        # Aprobamos Formación después de la corrección simulada
        result_form2 = resume_approval(
            ticket_id=ticket_id,
            department="Formacion y Estandares de Calidad",
            decision="approved",
            comment="Alcance corregido: ahora incluye Florida. Aprobado.",
            repository=repo,
        )
        assert result_form2["decision"] == "approved"

        # Procesamos las 2 restantes
        for dept, decision, comment in approval_sequence[5:]:
            result = resume_approval(
                ticket_id=ticket_id,
                department=dept,
                decision=decision,
                comment=comment,
                repository=repo,
            )

        # ---- Paso 4: Verificar documento final ----
        state_final = get_approval_state(ticket_id) or {}
        assert state_final["phase"] == "completed", (
            f"Fase final: {state_final.get('phase')}, esperado 'completed'"
        )

        final_doc = state_final.get("final_document")
        assert final_doc is not None, "No se generó el documento final"
        assert final_doc["ticket_id"] == ticket_id
        assert len(final_doc["sections"]) == 7, (
            f"Esperado 7 secciones, obtenido {len(final_doc['sections'])}"
        )

        # Verificar que todos los departamentos están en el documento
        for dept in dept_names:
            assert dept in final_doc["sections"], f"Falta sección para {dept} en documento final"

        rendered = state_final.get("final_document", {}).get("rendered", "")
        assert rendered, "El documento final no tiene contenido rendered"
        assert "PROPUESTA COMERCIAL" in rendered, f"El rendered no contiene 'PROPUESTA COMERCIAL': {rendered[:200]}"
        assert "BRASALAND" in rendered, f"El rendered no contiene 'BRASALAND': {rendered[:200]}"

        # ---- Paso 5: Verificar trazabilidad ----
        trace = get_trace_for_thread(f"rfp-{ticket_id}")
        assert len(trace) >= 2, "Debe haber al menos 2 entradas de trace"
        node_names = [t["node_name"] for t in trace]
        assert "approval_init" in node_names
        assert "approval_resume" in node_names

        # Verificar que hay al menos una entrada de human_approval
        human_nodes = [t for t in trace if t["node_name"] == "human_approval"]
        assert len(human_nodes) >= 7, (
            f"Esperado al menos 7 human_approval, obtenido {len(human_nodes)}"
        )

        # ---- Paso 6: Verificar persistencia en repositorio ----
        persisted_doc = repo.get_final_document(ticket_id)
        assert persisted_doc is not None
        assert "rendered" in persisted_doc

        persisted_approvals = repo.get_approval_status_list(ticket_id)
        assert len(persisted_approvals) >= 7
        # Verificar que hay un approved para cada departamento
        approved_depts = {a["department"] for a in persisted_approvals
                          if a["status"] == "approved"}
        for dept in dept_names:
            assert dept in approved_depts, f"{dept} no está en approved_depts"

        # ---- Paso 7: Mostrar resumen del documento final (para depuración) ----
        print(f"\n\n===== DOCUMENTO FINAL GENERADO ({ticket_id}) =====")
        print(rendered[:2000])
        print(f"\n... [documento truncado, {len(rendered)} caracteres totales]")
        print(f"\n===== TRAZABILIDAD: {len(trace)} entradas =====")
        for entry in trace:
            print(f"  - {entry['node_name']} | agente: {entry['agent']} | run: {entry.get('run_id', 'N/A')}")

        # ---- Final: Verificar que el flujo completo es reproducible ----
        # Si llegamos aquí sin excepción, el test pasó completamente.

    def test_part2_handoff_structure(self, repo: InMemoryRepo, monkeypatch):
        """Verifica la estructura del handoff que produce Part 2."""
        ticket_id = f"e2e-structure-{uuid.uuid4().hex[:8]}"

        def fake_ask(system_prompt, user_prompt, response_format="text"):
            if response_format == "json":
                return json.dumps({"score": 85, "feedback": "Ok.", "passed": True})
            return "## Alcance del servicio\nSimulado.\n## Desglose de precios\nSimulado.\n## Cronograma de entregas\nSimulado.\n## Condiciones comerciales\nSimulado."

        monkeypatch.setattr(rfp_response, "ask_model", fake_ask)
        monkeypatch.setattr(rfp_response, "retrieve_knowledge_context",
                            lambda: SAMPLE_KNOWLEDGE_CONTEXT)

        handoff = rfp_response.process_rfp_response(ticket_id, PART1_HANDOFF, repo)

        # Estructura esperada
        assert "ticket_id" in handoff
        assert "drafts" in handoff
        assert "evaluation_summary" in handoff
        assert "needs_human_review" in handoff
        assert "part1_handoff" in handoff

        # Cada draft debe tener content, department, iteration
        for dept, draft in handoff["drafts"].items():
            assert "content" in draft
            assert "department" in draft
            assert draft["department"] == dept

    def test_approval_resume_after_interruption(self, repo: InMemoryRepo, monkeypatch):
        """Verifica que el checkpointer permite reanudar después de una interrupción."""
        ticket_id = f"e2e-interrupt-{uuid.uuid4().hex[:8]}"

        def fake_ask(system_prompt, user_prompt, response_format="text"):
            if response_format == "json":
                return json.dumps({"score": 85, "feedback": "Ok.", "passed": True})
            return "## Alcance del servicio\nSimulado.\n## Desglose de precios\nSimulado.\n## Cronograma de entregas\nSimulado.\n## Condiciones comerciales\nSimulado."

        monkeypatch.setattr(rfp_response, "ask_model", fake_ask)
        monkeypatch.setattr(rfp_response, "retrieve_knowledge_context",
                            lambda: SAMPLE_KNOWLEDGE_CONTEXT)

        handoff = rfp_response.process_rfp_response(ticket_id, PART1_HANDOFF, repo)

        # Iniciar aprobación
        process_rfp_approval(ticket_id, handoff, repo)

        # Aprobar 2 departamentos
        resume_approval(ticket_id=ticket_id, department="Operaciones de Restaurante",
                         decision="approved", comment="Ok.", repository=repo)
        resume_approval(ticket_id=ticket_id, department="Tecnologia",
                         decision="approved", comment="Ok.", repository=repo)

        # Simular interrupción: recargar estado desde checkpointer
        state_before = get_approval_state(ticket_id)
        assert state_before is not None
        # pending_departments no se guarda en checkpoint, lo computamos
        pending_before = [
            d for d, s in state_before.get("departments", {}).items()
            if s.get("status") == "pending"
        ]
        assert len(pending_before) == 5

        # Reanudar aprobando el resto
        for dept in DEPARTMENT_APPROVERS:
            state = get_approval_state(ticket_id)
            depts = state.get("departments", {})
            if dept in depts and depts[dept].get("status") == "pending":
                resume_approval(ticket_id=ticket_id, department=dept,
                                 decision="approved", comment="Ok.", repository=repo)

        state_final = get_approval_state(ticket_id)
        assert state_final["phase"] == "completed"
        assert state_final.get("final_document") is not None

    def test_rejected_department_excluded_from_document(self, repo: InMemoryRepo, monkeypatch):
        """Verifica que un departamento rechazado NO aparece en el documento final."""
        ticket_id = f"e2e-reject-{uuid.uuid4().hex[:8]}"

        def fake_ask(system_prompt, user_prompt, response_format="text"):
            if response_format == "json":
                return json.dumps({"score": 85, "feedback": "Ok.", "passed": True})
            return "## Alcance del servicio\nSimulado.\n## Desglose de precios\nSimulado.\n## Cronograma de entregas\nSimulado.\n## Condiciones comerciales\nSimulado."

        monkeypatch.setattr(rfp_response, "ask_model", fake_ask)
        monkeypatch.setattr(rfp_response, "retrieve_knowledge_context",
                            lambda: SAMPLE_KNOWLEDGE_CONTEXT)

        handoff = rfp_response.process_rfp_response(ticket_id, PART1_HANDOFF, repo)
        process_rfp_approval(ticket_id, handoff, repo)

        # Aprobar 6, rechazar 1 (Marketing)
        for dept, contact in DEPARTMENT_APPROVERS.items():
            if dept == "Marketing y Experiencia Digital":
                resume_approval(ticket_id=ticket_id, department=dept,
                                 decision="rejected", comment="No cumple.",
                                 repository=repo)
            else:
                resume_approval(ticket_id=ticket_id, department=dept,
                                 decision="approved", comment="Ok.",
                                 repository=repo)

        state = get_approval_state(ticket_id)
        assert state["phase"] == "completed"

        doc = state["final_document"]
        # Marketing debería estar excluido (rechazado)
        assert "Marketing y Experiencia Digital" not in doc["sections"], (
            "Marketing está rechazado y no debería estar en el documento final"
        )
        # Los demás deben estar
        for dept in DEPARTMENT_APPROVERS:
            if dept != "Marketing y Experiencia Digital":
                assert dept in doc["sections"], f"Falta {dept} en documento final"


# ---------------------------------------------------------------------------
# Ejecución directa: python tests/pipelines/test_rfp_e2e.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])