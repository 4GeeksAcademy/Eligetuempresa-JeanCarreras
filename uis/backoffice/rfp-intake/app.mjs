const params = new URLSearchParams(location.search);
const preview = location.hostname.match(/^(.*)-\d+(\.(?:app\.)?github\.dev)$/);
const apiBase = params.get("apiBase") || (preview
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
  const accessToken = token();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(new URL(path, apiBase), {
    ...options,
    headers,
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
  // Part 2/3: Response status and approval UI
  if (["generando_borrador", "en_evaluacion", "needs_human_review", "esperando_aprobacion", "terminado"].includes(ticket.status)) {
    content.append(renderResponseStatus(ticket.id));
  }
  if (["esperando_aprobacion", "terminado"].includes(ticket.status)) {
    content.append(renderApprovalUI(ticket.id));
  }
  detail.replaceChildren(content);
  detail.setAttribute("aria-busy", ticket.status === "analizando" && !ticket.processing_error ? "true" : "false");
  loadTickets();
  clearTimeout(pollTimer);
  if (ticket.status === "analizando" && !ticket.processing_error) {
    pollTimer = setTimeout(() => loadTicket(ticket.id), 2500);
  }
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
document.querySelector("#login").href = `../../auth/?${new URLSearchParams({ apiBase })}`;
loadTickets();