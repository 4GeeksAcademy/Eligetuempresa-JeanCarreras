const params = new URLSearchParams(location.search);
const preview = location.hostname.match(/^(.*)-\d+(\.(?:app\.)?github\.dev)$/);
const apiBase = params.get("apiBase") || window.BRASALAND_API_BASE || (preview
  ? `${location.protocol}//${preview[1]}-8000${preview[2]}`
  : `${location.protocol}//${location.hostname}:8000`);
const form = document.querySelector("#upload-form");
const fileInput = document.querySelector("#rfp-file");
const uploadStatus = document.querySelector("#upload-status");
const queueStatus = document.querySelector("#queue-status");
const ticketList = document.querySelector("#ticket-list");
const detailStatus = document.querySelector("#detail-status");
const detail = document.querySelector("#ticket-detail");
const statusBadge = document.querySelector("#ticket-status");
const title = document.querySelector("#detail-title");
let activeTicketId;
let pollTimer;

function node(tag, text, className) {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (className) result.className = className;
  return result;
}

function token() {
  try { return localStorage.getItem("brasaland_token"); } catch { return null; }
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const response = await fetch(`${apiBase.replace(/\/$/, "")}${path}`, {
    ...options,
    headers: window.BrasalandSecurity.authHeaders(apiBase, headers),
    credentials: "same-origin",
    cache: "no-store",
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) throw new Error("Inicia sesion desde Mi cuenta para consultar el intake.");
    throw new Error(payload.detail || "No se pudo completar la solicitud.");
  }
  return payload;
}

function statusLabel(status) {
  return ({
    analizando: "Analizando",
    analisis_completo: "Analisis completo",
    descartado: "Descartado",
    generando_borrador: "Generando borrador",
    en_evaluacion: "En evaluacion",
    needs_human_review: "Requiere revision humana",
    esperando_aprobacion: "Esperando aprobacion",
    terminado: "Terminado",
  })[status] || status;
}

function renderTicketList(tickets) {
  const fragment = document.createDocumentFragment();
  for (const ticket of tickets) {
    const item = node("li", undefined, "ticket-item");
    const button = node("button", undefined, "ticket-choice");
    button.type = "button";
    button.setAttribute("aria-current", ticket.id === activeTicketId ? "true" : "false");
    const name = node("strong", ticket.original_filename || "RFP sin nombre");
    const metadata = node("span", `${statusLabel(ticket.status)} · ${new Date(ticket.created_at).toLocaleString("es-CO")}`);
    button.append(name, metadata);
    button.addEventListener("click", () => loadTicket(ticket.id));
    item.append(button);
    fragment.append(item);
  }
  ticketList.replaceChildren(fragment);
  queueStatus.textContent = tickets.length ? `${tickets.length} tickets` : "Todavia no hay tickets.";
}

async function loadTickets() {
  queueStatus.textContent = "Actualizando tickets...";
  try {
    renderTicketList(await api("/rfp-intake/tickets?limit=50"));
  } catch (error) {
    queueStatus.textContent = error.message;
    queueStatus.className = "status error";
  }
}

function renderMetadata(documentData) {
  const metadata = documentData?.metadata;
  if (!metadata || !Object.keys(metadata).length) return null;
  const section = node("section", undefined, "result-section");
  section.append(node("h3", "Datos de la solicitud"));
  const list = node("dl", undefined, "metadata-list");
  const labels = {
    customer_name: "Cliente", request_title: "Solicitud", response_deadline: "Fecha limite",
    currency: "Moneda", estimated_value: "Valor estimado", submission_instructions: "Instrucciones",
    requested_deliverables: "Entregables",
  };
  for (const [key, label] of Object.entries(labels)) {
    const value = metadata[key];
    if (value === null || value === undefined || value === "") continue;
    list.append(node("dt", label), node("dd", Array.isArray(value) ? value.join(", ") : String(value)));
  }
  section.append(list);
  const metrics = documentData.readability_metrics || {};
  const metricEntries = Object.entries(metrics);
  if (metricEntries.length) {
    section.append(node("h3", "Legibilidad y costo estimado"));
    const metricList = node("dl", undefined, "metadata-list metrics-list");
    for (const [key, value] of metricEntries) {
      metricList.append(node("dt", key.replaceAll("_", " ")), node("dd", String(value)));
    }
    section.append(metricList);
  }
  return section;
}

function renderSections(sections = []) {
  const wrapper = node("section", undefined, "result-section");
  wrapper.append(node("h3", "Workstreams por departamento"));
  if (!sections.length) {
    wrapper.append(node("p", "No se detectaron workstreams departamentales."));
    return wrapper;
  }
  for (const section of sections) {
    const department = node("section", undefined, "department");
    department.append(node("h4", `${section.department} · ${section.contact}`));
    const aspects = node("ul");
    for (const aspect of section.key_aspects || []) {
      const item = node("li");
      item.append(node("strong", aspect.aspect));
      if (aspect.request) item.append(node("p", aspect.request));
      if (aspect.evidence) item.append(node("blockquote", `Evidencia: “${aspect.evidence}”`));
      if (aspect.missing_information?.length) {
        item.append(node("p", `Informacion faltante: ${aspect.missing_information.join(", ")}`, "missing"));
      }
      aspects.append(item);
    }
    department.append(aspects);
    wrapper.append(department);
  }
  return wrapper;
}

function renderTicket(ticket) {
  activeTicketId = ticket.id;
  title.textContent = ticket.original_filename || ticket.id;
  statusBadge.hidden = false;
  statusBadge.textContent = statusLabel(ticket.status);
  statusBadge.dataset.status = ticket.status;
  detailStatus.className = ticket.processing_error ? "status error" : "status";
  detailStatus.textContent = ticket.processing_error
    ? `Error de procesamiento: ${ticket.processing_error}`
    : `Ticket ${ticket.id}`;
  const content = document.createDocumentFragment();
  const doc = ticket.document;
  const metadata = renderMetadata(doc);
  if (metadata) content.append(metadata);
  if (doc?.classification?.rationale) {
    content.append(node("p", `Clasificacion: ${doc.classification.rationale}`, "classification"));
  }
  if (ticket.classification_reason) {
    content.append(node("p", `Motivo de descarte: ${ticket.classification_reason}`, "classification"));
  }
  if (ticket.handoff?.sales_handoff) {
    const handoff = node("section", undefined, "handoff");
    handoff.append(node("p", "Siguiente paso para Ventas", "eyebrow"), node("p", ticket.handoff.sales_handoff));
    content.append(handoff);
  }
  if (ticket.status === "analisis_completo" || ticket.status === "descartado") {
    content.append(renderSections(ticket.department_sections));
  }
  if (ticket.status === "analisis_completo" && ticket.handoff) {
    const generate = node("button", "Generar respuesta");
    generate.type = "button";
    generate.addEventListener("click", async () => {
      generate.disabled = true;
      try {
        await api(`/rfp-intake/tickets/${encodeURIComponent(ticket.id)}/generate-response`, { method: "POST" });
        renderTicket({ ...ticket, status: "generando_borrador" });
      } catch (error) {
        detailStatus.textContent = error.message;
        detailStatus.className = "status error";
        generate.disabled = false;
      }
    });
    content.append(generate);
  }
  // Part 2/3: Response status and approval UI
  if (["generando_borrador", "en_evaluacion", "needs_human_review", "esperando_aprobacion", "terminado"].includes(ticket.status)) {
    content.append(renderResponseStatus(ticket.id));
  }
  if (["esperando_aprobacion", "terminado"].includes(ticket.status)) {
    content.append(renderApprovalUI(ticket.id, ticket.status === "terminado"));
  }
  detail.replaceChildren(content);
  detail.setAttribute("aria-busy", ticket.status === "analizando" && !ticket.processing_error ? "true" : "false");
  loadTickets();
  clearTimeout(pollTimer);
  if (["analizando", "generando_borrador", "en_evaluacion"].includes(ticket.status) && !ticket.processing_error) {
    pollTimer = setTimeout(() => loadTicket(ticket.id), 2500);
  }
}

function renderResponseStatus(ticketId) {
  const section = node("section", undefined, "result-section");
  section.append(node("h3", "Borradores y evaluacion"));
  const result = node("div", "Consultando respuesta...");
  section.append(result);
  api(`/rfp-intake/tickets/${encodeURIComponent(ticketId)}/response`).then((response) => {
    result.replaceChildren();
    const drafts = new Map();
    for (const draft of response.drafts || []) {
      const previous = drafts.get(draft.department);
      if (!previous || Number(draft.iteration) >= Number(previous.iteration)) drafts.set(draft.department, draft);
    }
    if (!drafts.size) result.append(node("p", "Aun no hay borradores disponibles."));
    for (const draft of drafts.values()) {
      result.append(node("h4", draft.department), node("pre", draft.content || "Contenido no disponible."));
    }
    if (response.evaluation_results?.length) {
      const evaluations = node("details");
      evaluations.append(node("summary", "Evaluaciones"), node("pre", JSON.stringify(response.evaluation_results, null, 2)));
      result.append(evaluations);
    }
  }).catch((error) => { result.textContent = error.message; });
  const trace = node("button", "Ver trazabilidad");
  trace.type = "button";
  trace.addEventListener("click", async () => {
    trace.disabled = true;
    try {
      const rows = await api(`/rfp-intake/tickets/${encodeURIComponent(ticketId)}/trace`);
      result.append(node("pre", JSON.stringify(rows, null, 2)));
    } catch (error) { result.append(node("p", error.message, "status error")); }
    finally { trace.disabled = false; }
  });
  section.append(trace);
  return section;
}

function renderApprovalUI(ticketId, completed = false) {
  const section = node("section", undefined, "result-section");
  section.append(node("h3", "Revision y aprobacion"));
  const result = node("div", "Consultando aprobaciones...");
  section.append(result);
  Promise.all([
    api(`/rfp-intake/tickets/${encodeURIComponent(ticketId)}/approval-status`),
    api(`/rfp-intake/tickets/${encodeURIComponent(ticketId)}/response`),
  ]).then(([approval, response]) => {
    result.replaceChildren();
    const rows = approval.persisted_approvals || [];
    const departments = new Set([...Object.keys(approval.state?.departments || {}), ...rows.map((row) => row.department), ...(response.drafts || []).map((draft) => draft.department)].filter(Boolean));
    if (!departments.size) result.append(node("p", "No hay departamentos disponibles para revision."));
    for (const department of departments) {
      const persisted = rows.find((row) => row.department === department) || approval.state?.departments?.[department];
      const decisionForm = node("form", undefined, "department approval-form");
      decisionForm.append(node("h4", department), node("p", persisted?.status || "Pendiente"));
      if (!completed && persisted?.status !== "approved") {
        const decisionLabel = node("label", "Decision");
        const decision = node("select");
        decision.setAttribute("aria-label", `Decision de ${department}`);
        for (const [value, label] of [["approve", "Aprobar"], ["request-changes", "Solicitar cambios"], ["reject", "Rechazar"]]) {
          const option = node("option", label);
          option.value = value;
          decision.append(option);
        }
        decisionLabel.append(decision);
        const commentLabel = node("label", "Comentario");
        const comment = node("textarea");
        comment.maxLength = 10000;
        comment.setAttribute("aria-label", `Comentario para ${department}`);
        commentLabel.append(comment);
        const submit = node("button", "Confirmar decision");
        submit.type = "submit";
        const feedback = node("p", undefined, "status");
        feedback.setAttribute("role", "status");
        decisionForm.append(decisionLabel, commentLabel, submit, feedback);
        decisionForm.addEventListener("submit", async (event) => {
          event.preventDefault();
          if (decision.value !== "approve" && !comment.value.trim()) {
            feedback.textContent = "Indica el motivo de la decision.";
            return;
          }
          if (!window.confirm(`Confirmar la decision para ${department}?`)) return;
          submit.disabled = true;
          try {
            await api(`/rfp-intake/tickets/${encodeURIComponent(ticketId)}/${decision.value}-department`, {
              method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ department, comment: comment.value.trim() }),
            });
            await loadTicket(ticketId);
          } catch (error) { feedback.textContent = error.message; submit.disabled = false; }
        });
      }
      result.append(decisionForm);
    }
  }).catch((error) => { result.textContent = error.message; });
  if (!completed) {
    const arbitrate = node("button", "Revisar conflictos entre departamentos");
    arbitrate.type = "button";
    arbitrate.addEventListener("click", async () => {
      if (!window.confirm("Solicitar arbitraje sobre los borradores aprobados?")) return;
      arbitrate.disabled = true;
      try {
        const arbitration = await api(`/rfp-intake/tickets/${encodeURIComponent(ticketId)}/arbitrate`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}),
        });
        result.append(node("pre", JSON.stringify(arbitration, null, 2)));
        await loadTicket(ticketId);
      } catch (error) { result.append(node("p", error.message, "status error")); }
      finally { arbitrate.disabled = false; }
    });
    section.append(arbitrate);
  }
  if (completed) {
    const download = node("button", "Descargar documento final (JSON)");
    download.type = "button";
    download.addEventListener("click", async () => {
      download.disabled = true;
      try {
        const documentData = await api(`/rfp-intake/tickets/${encodeURIComponent(ticketId)}/final-document`);
        const url = URL.createObjectURL(new Blob([JSON.stringify(documentData, null, 2)], { type: "application/json" }));
        const link = node("a");
        link.href = url;
        link.download = `rfp-${ticketId}.json`;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      } catch (error) { result.append(node("p", error.message, "status error")); }
      finally { download.disabled = false; }
    });
    section.append(download);
  }
  return section;
}

async function loadTicket(ticketId) {
  activeTicketId = ticketId;
  detailStatus.className = "status";
  detailStatus.textContent = "Consultando estado...";
  try {
    renderTicket(await api(`/rfp-intake/tickets/${encodeURIComponent(ticketId)}`));
  } catch (error) {
    detailStatus.className = "status error";
    detailStatus.textContent = error.message;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files?.[0];
  if (!file) return;
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    uploadStatus.className = "status error";
    uploadStatus.textContent = "Selecciona un archivo PDF.";
    return;
  }
  const button = form.querySelector("button");
  button.disabled = true;
  uploadStatus.className = "status";
  uploadStatus.textContent = "Creando ticket...";
  try {
    const payload = new FormData();
    payload.append("file", file);
    const result = await api("/rfp-intake/tickets", { method: "POST", body: payload });
    uploadStatus.textContent = `Ticket ${result.ticket_id} creado. El analisis continua en segundo plano.`;
    form.reset();
    await loadTicket(result.ticket_id);
  } catch (error) {
    uploadStatus.className = "status error";
    uploadStatus.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#refresh").addEventListener("click", loadTickets);
document.querySelector("#login").href = `../../auth/?${new URLSearchParams({ apiBase, next: location.pathname + location.search })}`;
loadTickets();