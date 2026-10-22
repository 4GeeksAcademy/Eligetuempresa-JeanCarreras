const query = new URLSearchParams(window.location.search);

function resolveApiBase() {
  const configured = query.get("apiBase") || window.BRASALAND_API_BASE;
  if (configured) return configured.replace(/\/$/, "");

  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return `${window.location.protocol}//${host}:8000`;
  }
  const match = host.match(/^(.*)-\d+(\.(?:app\.)?github\.dev)$/);
  return match ? `${window.location.protocol}//${match[1]}-8000${match[2]}` : "http://localhost:8000";
}

const apiBase = resolveApiBase();
const statusElement = document.getElementById("reportStatus");
const periodElement = document.getElementById("reportPeriod");
const refreshButton = document.getElementById("refreshReport");

function utcBoundary(dateValue, includeFollowingDay = false) {
  const [year, month, day] = dateValue.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + Number(includeFollowingDay))).toISOString();
}

function appendRows(body, rows, columns) {
  body.replaceChildren();
  if (!rows.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = columns.length;
    cell.className = "telemetry-empty";
    cell.textContent = "Sin eventos para este período";
    row.append(cell);
    body.append(row);
    return;
  }

  rows.forEach((item) => {
    const row = document.createElement("tr");
    columns.forEach(([field, format]) => {
      const cell = document.createElement("td");
      cell.textContent = format ? format(item[field]) : String(item[field] ?? "-");
      row.append(cell);
    });
    body.append(row);
  });
}

function number(value) {
  return Number(value ?? 0).toLocaleString("es-CO", { maximumFractionDigits: 2 });
}

function percent(value) {
  return `${number(value)}%`;
}

function formatPeriod(period) {
  const format = new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  });
  return `${format.format(new Date(period.from))} - ${format.format(new Date(period.to))} UTC`;
}

async function loadReport() {
  refreshButton.disabled = true;
  statusElement.textContent = "Consultando reporte técnico...";
  const parameters = new URLSearchParams();
  const start = document.getElementById("startDate").value;
  const end = document.getElementById("endDate").value;
  if (start) parameters.set("start_date", utcBoundary(start));
  if (end) parameters.set("end_date", utcBoundary(end, true));

  try {
    const response = await fetch(`${apiBase}/telemetry/report?${parameters}`);
    const report = await response.json();
    if (!response.ok) throw new Error(report.detail || "No se pudo consultar el reporte.");

    periodElement.textContent = formatPeriod(report.period);
    const metrics = report.metrics;
    appendRows(document.getElementById("eventsRows"), metrics.events_per_day, [
      ["date"], ["event_type"], ["event_count", number],
    ]);
    appendRows(document.getElementById("latencyRows"), metrics.api_latency_by_day, [
      ["date"], ["route_template"], ["request_count", number], ["mean_latency_ms", number],
    ]);
    appendRows(document.getElementById("errorRows"), metrics.error_rate_by_type, [
      ["date"], ["route_template"], ["error_count", number], ["request_count", number], ["error_rate_pct", percent],
    ]);
    appendRows(document.getElementById("authRows"), metrics.auth_failure_rate, [
      ["date"], ["failed_attempts", number], ["total_attempts", number], ["failure_rate_pct", percent],
    ]);
    appendRows(document.getElementById("availabilityRows"), metrics.availability_by_day_and_source, [
      ["date"], ["source_system"], ["event_count", number], ["online_count", number], ["availability_pct", percent],
    ]);
    statusElement.textContent = "Reporte actualizado";
  } catch (error) {
    statusElement.textContent = error.message;
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener("click", loadReport);
loadReport();