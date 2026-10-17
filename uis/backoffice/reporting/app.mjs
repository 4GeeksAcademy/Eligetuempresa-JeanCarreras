import { fetchReportingKpis } from "./client.mjs";

const form = document.querySelector("#filters");
const results = document.querySelector("#results");
const status = document.querySelector("#status");
const period = document.querySelector("#period");
const warning = document.querySelector("#warning");
const updated = document.querySelector("#updated");
const params = new URLSearchParams(location.search);
const preview = location.hostname.match(/^(.*)-\d+(\.(?:app\.)?github\.dev)$/);
const apiBase = params.get("apiBase") || (preview
  ? `${location.protocol}//${preview[1]}-8000${preview[2]}`
  : `${location.protocol}//${location.hostname}:8000`);
const numberFormat = new Intl.NumberFormat("es-CO", { maximumSignificantDigits: 12 });
const dateFormat = new Intl.DateTimeFormat("es-CO", { timeZone: "UTC", dateStyle: "medium" });
const dimensions = new Set(["id", "metric_date", "store_id", "country", "currency", "run_id", "created_at", "updated_at"]);
let activeRequest;

const lastMonday = new Date();
lastMonday.setUTCHours(0, 0, 0, 0);
lastMonday.setUTCDate(lastMonday.getUTCDate() - ((lastMonday.getUTCDay() + 6) % 7) - 7);
const lastSunday = new Date(lastMonday);
lastSunday.setUTCDate(lastSunday.getUTCDate() + 6);
form.elements.startDate.value = lastMonday.toISOString().slice(0, 10);
form.elements.endDate.value = lastSunday.toISOString().slice(0, 10);

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function displayDate(value) {
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? value : dateFormat.format(date);
}

function renderMetricTables(rows, periodLabel) {
  const metricNames = [...new Set(rows.flatMap((row) => Object.keys(row)))].filter((key) =>
    !dimensions.has(key) && rows.some((row) => typeof row[key] === "number"));
  const fragment = document.createDocumentFragment();
  for (const key of metricNames) {
    const title = key.replaceAll("_", " ");
    const heading = title.charAt(0).toUpperCase() + title.slice(1);
    const section = element("section", undefined, "metric");
    section.append(element("h2", heading), element("p", periodLabel, "metric-period"));
    const scroll = element("div", undefined, "table-scroll");
    scroll.tabIndex = 0;
    scroll.setAttribute("role", "region");
    scroll.setAttribute("aria-label", heading);
    const table = element("table");
    const tableHead = element("thead");
    const headerRow = element("tr");
    for (const label of ["Fecha", "Local", "Pais", "Moneda", "Valor diario"]) {
      const cell = element("th", label);
      cell.scope = "col";
      headerRow.append(cell);
    }
    tableHead.append(headerRow);
    const body = element("tbody");
    for (const row of rows) {
      const line = element("tr");
      const value = typeof row[key] === "number" && Number.isFinite(row[key])
        ? numberFormat.format(row[key]) : "Sin informacion";
      const cells = [displayDate(row.metric_date), row.store_id,
        row.country === "CO" ? "Colombia" : "Estados Unidos", row.currency || "No indicada", value];
      for (const cell of cells) line.append(element("td", cell));
      body.append(line);
    }
    table.append(tableHead, body);
    scroll.append(table);
    section.append(scroll);
    fragment.append(section);
  }
  results.replaceChildren(fragment);
  return metricNames.length;
}

async function loadReport(event) {
  event?.preventDefault();
  activeRequest?.abort();
  const controller = new AbortController();
  activeRequest = controller;
  const timeout = setTimeout(() => controller.abort(), 15000);
  const filters = Object.fromEntries(new FormData(form));
  const periodLabel = `${displayDate(filters.startDate)} al ${displayDate(filters.endDate)}`;
  period.textContent = periodLabel;
  results.replaceChildren();
  results.setAttribute("aria-busy", "true");
  warning.hidden = true;
  updated.textContent = "";
  status.className = "status";
  status.textContent = "Consultando informe...";
  form.querySelector("button").disabled = true;
  try {
    let token;
    try { token = localStorage.getItem("brasaland_token"); } catch {}
    const report = await fetchReportingKpis(apiBase, filters, { token, signal: controller.signal });
    if (activeRequest !== controller) return;
    const metricCount = renderMetricTables(report.rows, periodLabel);
    warning.hidden = !report.possiblyTruncated;
    status.textContent = !report.rows.length ? "No hay datos publicados para este periodo y pais."
      : !metricCount ? "El informe no contiene indicadores numericos."
        : `${metricCount} indicadores · ${report.rows.length} registros diarios`;
    updated.textContent = `Consulta: ${new Intl.DateTimeFormat("es-CO", { dateStyle: "short", timeStyle: "short" }).format(new Date())}`;
  } catch (error) {
    if (activeRequest !== controller) return;
    status.className = "status error";
    status.textContent = error.name === "AbortError" ? "La consulta tardo demasiado. Intenta de nuevo."
      : error instanceof TypeError ? "No se pudo conectar con el servicio de informes."
        : error.message;
  } finally {
    clearTimeout(timeout);
    if (activeRequest === controller) {
      results.setAttribute("aria-busy", "false");
      form.querySelector("button").disabled = false;
    }
  }
}

document.querySelector("#login").href = `../../auth/?${new URLSearchParams({ apiBase })}`;
form.addEventListener("submit", loadReport);
loadReport();