const DEFAULT_API_BASE = "http://localhost:8000";

function resolveApiBase() {
  const params = new URLSearchParams(window.location.search);
  const queryApiBase = params.get("apiBase");
  if (queryApiBase) {
    return queryApiBase.replace(/\/$/, "");
  }

  if (typeof window.BRASALAND_API_BASE === "string" && window.BRASALAND_API_BASE.trim()) {
    return window.BRASALAND_API_BASE.trim().replace(/\/$/, "");
  }

  if (window.location.protocol === "file:") {
    // When opening index.html directly as a file, default to demo mode unless apiBase is explicit.
    return null;
  }

  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return `${window.location.protocol}//${host}:8000`;
  }

  // Codespaces/preview domains often expose each service by port in the hostname.
  const hostMatch = host.match(/^(.*)-\d+(\.(?:app\.)?github\.dev)$/);
  if (hostMatch) {
    return `${window.location.protocol}//${hostMatch[1]}-8000${hostMatch[2]}`;
  }

  return DEFAULT_API_BASE;
}

const API_BASE = resolveApiBase();
const DEFAULT_CURRENCY = "USD";
const FINANCE_ROLE = "executive";
const FINANCE_TOKEN = "brasaland-executive-token";
const ALERTS_ROLE = "executive";
const ALERTS_TOKEN = "brasaland-executive-token";
const ALERT_ACTION_ROLE = "operations";
const ALERT_ACTION_TOKEN = "brasaland-operations-token";
const RECEIPTS_ROLE = "operations";
const RECEIPTS_TOKEN = "brasaland-operations-token";

const statusText = document.getElementById("statusText");
const weeklySalesEl = document.getElementById("weeklySales");
const avgTicketEl = document.getElementById("avgTicket");
const activeStoresEl = document.getElementById("activeStores");
const inactiveStoresEl = document.getElementById("inactiveStores");
const inactivityRowsEl = document.getElementById("inactivityRows");
const reorderRowsEl = document.getElementById("reorderRows");
const receiptFormEl = document.getElementById("receiptForm");
const receiptStoreIdEl = document.getElementById("receiptStoreId");
const receiptSkuEl = document.getElementById("receiptSku");
const receiptQtyEl = document.getElementById("receiptQty");
const receiptUnitCostEl = document.getElementById("receiptUnitCost");
const receiptCurrencyEl = document.getElementById("receiptCurrency");
const receiptNoteEl = document.getElementById("receiptNote");
const receiptSubmitEl = document.getElementById("receiptSubmit");
const receiptStatusEl = document.getElementById("receiptStatus");
const receiptRowsEl = document.getElementById("receiptRows");
const receiptLoadMoreEl = document.getElementById("receiptLoadMore");
const storeRowsEl = document.getElementById("storeRows");
const countryFilterEl = document.getElementById("countryFilter");
const currencyFilterEl = document.getElementById("currencyFilter");
const refreshIntervalEl = document.getElementById("refreshInterval");
const startDateEl = document.getElementById("startDate");
const endDateEl = document.getElementById("endDate");
const applyFiltersButton = document.getElementById("applyFilters");
const salesCurrencyDetailEl = document.getElementById("salesCurrencyDetail");
const trendBarsEl = document.getElementById("trendBars");
const marketGridEl = document.getElementById("marketGrid");
const financeRevenueEl = document.getElementById("financeRevenue");
const financeCogsEl = document.getElementById("financeCogs");
const financeProfitEl = document.getElementById("financeProfit");
const financeMarginEl = document.getElementById("financeMargin");
const alertsSlaEl = document.getElementById("alertsSla");
const chainSalesUsdEl = document.getElementById("chainSalesUsd");
const chainSalesCopEl = document.getElementById("chainSalesCop");
const ceoMonthlyTopTicketEl = document.getElementById("ceoMonthlyTopTicket");
const executiveAskFormEl = document.getElementById("executiveAskForm");
const executiveAskInputEl = document.getElementById("executiveAskInput");
const executiveAskSubmitEl = document.getElementById("executiveAskSubmit");
const executiveAskStatusEl = document.getElementById("executiveAskStatus");
const executiveAskAnswerEl = document.getElementById("executiveAskAnswer");
const executiveAskSourcesEl = document.getElementById("executiveAskSources");
const weeklyReportGeneratedAtEl = document.getElementById("weeklyReportGeneratedAt");
const weeklyReportSummaryEl = document.getElementById("weeklyReportSummary");
const weeklyReportMarketsEl = document.getElementById("weeklyReportMarkets");
const weeklyReportRefreshEl = document.getElementById("weeklyReportRefresh");
const supplierConsolidatedRowsEl = document.getElementById("supplierConsolidatedRows");
const supplierPricesRowsEl = document.getElementById("supplierPricesRows");
const supplierAlertsRowsEl = document.getElementById("supplierAlertsRows");
const crmOverviewRowsEl = document.getElementById("crmOverviewRows");
const crmCustomersRowsEl = document.getElementById("crmCustomersRows");
const personalizationRowsEl = document.getElementById("personalizationRows");
const hrKpisRowsEl = document.getElementById("hrKpisRows");
const hrRequestsRowsEl = document.getElementById("hrRequestsRows");
const hrOnboardingRowsEl = document.getElementById("hrOnboardingRows");
const hrRequestFormEl = document.getElementById("hrRequestForm");
const hrRequestEmployeeIdEl = document.getElementById("hrRequestEmployeeId");
const hrRequestTypeEl = document.getElementById("hrRequestType");
const hrRequestStartDateEl = document.getElementById("hrRequestStartDate");
const hrRequestEndDateEl = document.getElementById("hrRequestEndDate");
const hrRequestReasonEl = document.getElementById("hrRequestReason");
const hrRequestSubmitEl = document.getElementById("hrRequestSubmit");
const hrRequestStatusEl = document.getElementById("hrRequestStatus");
const hrOnboardingFormEl = document.getElementById("hrOnboardingForm");
const hrOnboardingEmployeeIdEl = document.getElementById("hrOnboardingEmployeeId");
const hrOnboardingPositionEl = document.getElementById("hrOnboardingPosition");
const hrOnboardingMentorEl = document.getElementById("hrOnboardingMentor");
const hrOnboardingSubmitEl = document.getElementById("hrOnboardingSubmit");
const hrOnboardingStatusEl = document.getElementById("hrOnboardingStatus");
const trainingCatalogRowsEl = document.getElementById("trainingCatalogRows");
const trainingItinerariesRowsEl = document.getElementById("trainingItinerariesRows");
const trainingUpdatesRowsEl = document.getElementById("trainingUpdatesRows");
const trainingSearchFormEl = document.getElementById("trainingSearchForm");
const trainingSearchQueryEl = document.getElementById("trainingSearchQuery");
const trainingLocaleFilterEl = document.getElementById("trainingLocaleFilter");
const trainingSearchSubmitEl = document.getElementById("trainingSearchSubmit");
const trainingSearchStatusEl = document.getElementById("trainingSearchStatus");
const trainingUpdateFormEl = document.getElementById("trainingUpdateForm");
const trainingUpdateResourceIdEl = document.getElementById("trainingUpdateResourceId");
const trainingUpdateLocaleEl = document.getElementById("trainingUpdateLocale");
const trainingUpdateSummaryEl = document.getElementById("trainingUpdateSummary");
const trainingUpdateSubmitEl = document.getElementById("trainingUpdateSubmit");
const trainingUpdateStatusEl = document.getElementById("trainingUpdateStatus");
let refreshTimerId = null;
const RECEIPTS_PAGE_SIZE = 8;
let receiptsOffset = 0;

function monthStartIsoDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function renderExecutiveSalesDual(summaryUsd, summaryCop) {
  if (!chainSalesUsdEl || !chainSalesCopEl) {
    return;
  }

  if (!summaryUsd || !summaryCop) {
    chainSalesUsdEl.textContent = "-";
    chainSalesCopEl.textContent = "-";
    return;
  }

  chainSalesUsdEl.textContent = getFormatter("USD").format(Number(summaryUsd.total_sales || 0));
  chainSalesCopEl.textContent = getFormatter("COP").format(Number(summaryCop.total_sales || 0));
}

function renderMonthlyTopTicket(stores, currency) {
  if (!ceoMonthlyTopTicketEl) {
    return;
  }

  if (!Array.isArray(stores) || stores.length === 0) {
    ceoMonthlyTopTicketEl.textContent = "Local top ticket mensual: informacion insuficiente";
    return;
  }

  const best = [...stores].sort((a, b) => Number(b.average_ticket || 0) - Number(a.average_ticket || 0))[0];
  const avgTicket = getFormatter(currency).format(Number(best.average_ticket || 0));
  ceoMonthlyTopTicketEl.textContent = `Local top ticket mensual: ${best.store_name} (${best.market}) con ${avgTicket}`;
}

function renderWeeklyReportPreview(weeklyReport) {
  if (!weeklyReportGeneratedAtEl || !weeklyReportSummaryEl || !weeklyReportMarketsEl) {
    return;
  }

  if (!weeklyReport || !weeklyReport.summary) {
    weeklyReportGeneratedAtEl.textContent = "Generado: informacion insuficiente";
    weeklyReportSummaryEl.textContent = "Resumen semanal: -";
    weeklyReportMarketsEl.textContent = "Mercados: -";
    return;
  }

  const generatedAt = weeklyReport.generated_at
    ? new Date(weeklyReport.generated_at).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" })
    : "N/A";
  const format = getFormatter(weeklyReport.currency || DEFAULT_CURRENCY);
  const summary = weeklyReport.summary;
  const markets = Array.isArray(weeklyReport.markets) ? weeklyReport.markets : [];
  const marketLine = markets
    .map((item) => `${item.market}: ${format.format(Number(item.sales || 0))}`)
    .join(" | ");

  weeklyReportGeneratedAtEl.textContent = `Generado: ${generatedAt} (${weeklyReport.currency})`;
  weeklyReportSummaryEl.textContent = `Resumen semanal: ventas ${format.format(Number(summary.total_sales || 0))}, ticket promedio ${format.format(Number(summary.average_ticket || 0))}`;
  weeklyReportMarketsEl.textContent = marketLine ? `Mercados: ${marketLine}` : "Mercados: sin datos";
}

async function submitExecutiveAsk(event) {
  event.preventDefault();
  if (!executiveAskInputEl || !executiveAskSubmitEl || !executiveAskStatusEl || !executiveAskAnswerEl || !executiveAskSourcesEl) {
    return;
  }

  const question = (executiveAskInputEl.value || "").trim();
  if (!question) {
    executiveAskStatusEl.textContent = "Debes escribir una pregunta.";
    return;
  }

  executiveAskSubmitEl.disabled = true;
  executiveAskStatusEl.textContent = "Consultando asistente IA...";

  try {
    const selectedCurrency = currencyFilterEl?.value || DEFAULT_CURRENCY;
    const payload = await fetchJsonWithHeaders(
      `/api/v1/executive/ask?question=${encodeURIComponent(question)}&currency=${selectedCurrency}`,
      {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      },
    );

    executiveAskAnswerEl.textContent = payload.answer || "Sin respuesta";
    executiveAskSourcesEl.textContent = `Fuentes: ${(payload.sources || []).join(", ") || "N/A"}`;
    executiveAskStatusEl.textContent = payload.requires_follow_up
      ? "Respuesta parcial: se recomiendan preguntas de seguimiento."
      : "Respuesta generada con trazabilidad.";
  } catch (error) {
    executiveAskStatusEl.textContent = `No fue posible consultar: ${error.message}`;
  } finally {
    executiveAskSubmitEl.disabled = false;
  }
}

async function refreshWeeklyReportPreview() {
  if (!weeklyReportRefreshEl) {
    return;
  }
  weeklyReportRefreshEl.disabled = true;
  statusText.textContent = "Actualizando vista de reporte semanal...";
  try {
    const selectedCurrency = currencyFilterEl?.value || DEFAULT_CURRENCY;
    const weeklyReport = await fetchJsonWithHeaders(
      `/api/v1/executive/weekly-report?currency=${selectedCurrency}`,
      {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      },
    );
    renderWeeklyReportPreview(weeklyReport);
  } catch (error) {
    statusText.textContent = `No fue posible actualizar reporte semanal: ${error.message}`;
  } finally {
    weeklyReportRefreshEl.disabled = false;
  }
}

function getIsoDateOffset(days) {
  const base = new Date();
  base.setDate(base.getDate() + days);
  return base.toISOString().slice(0, 10);
}

function setDefaultHrDates() {
  if (hrRequestStartDateEl && hrRequestEndDateEl) {
    hrRequestStartDateEl.value = getIsoDateOffset(14);
    hrRequestEndDateEl.value = getIsoDateOffset(16);
  }
}

function populateHrEmployeeOptions(employees) {
  if (!Array.isArray(employees) || !employees.length) {
    return;
  }

  const options = employees
    .map((employee) => `<option value="${employee.id}">${employee.full_name} · ${employee.store_id} · ${employee.country}</option>`)
    .join("");

  if (hrRequestEmployeeIdEl) {
    const previous = hrRequestEmployeeIdEl.value;
    hrRequestEmployeeIdEl.innerHTML = options;
    if (previous && employees.some((employee) => employee.id === previous)) {
      hrRequestEmployeeIdEl.value = previous;
    }
  }

  if (hrOnboardingEmployeeIdEl) {
    const previous = hrOnboardingEmployeeIdEl.value;
    hrOnboardingEmployeeIdEl.innerHTML = options;
    if (previous && employees.some((employee) => employee.id === previous)) {
      hrOnboardingEmployeeIdEl.value = previous;
    }
  }
}

function renderHrKpis(summary) {
  if (!hrKpisRowsEl) {
    return;
  }

  if (!summary || !Array.isArray(summary.by_country)) {
    hrKpisRowsEl.innerHTML = '<p class="alerts-empty">Sin KPIs de RRHH para este filtro.</p>';
    return;
  }

  const countriesRows = summary.by_country
    .map(
      (item) => `
        <article class="supplier-row">
          <p class="alert-store">${item.market}</p>
          <p class="alert-meta">Headcount activo ${item.active_headcount} · vacantes abiertas ${item.open_vacancies}</p>
          <p class="alert-action">Rotacion ${Number(item.turnover_rate_pct || 0).toFixed(2)}% · absentismo ${Number(item.absenteeism_rate_pct || 0).toFixed(3)}%</p>
          <p class="alert-meta">Tiempo cobertura ${Number(item.avg_time_to_fill_days || 0).toFixed(1)} dias · onboarding activo ${item.active_onboarding_cases}</p>
        </article>
      `,
    )
    .join("");

  hrKpisRowsEl.innerHTML = `
    <article class="supplier-row">
      <p class="alert-store">Cadena (${summary.period_days} dias)</p>
      <p class="alert-meta">Headcount activo ${summary.total_active_headcount} · bajas ${summary.total_terminations}</p>
      <p class="alert-action">Rotacion ${Number(summary.overall_turnover_rate_pct || 0).toFixed(2)}% · absentismo ${Number(summary.overall_absenteeism_rate_pct || 0).toFixed(3)}%</p>
      <p class="alert-meta">Cobertura vacantes ${Number(summary.overall_avg_time_to_fill_days || 0).toFixed(1)} dias</p>
    </article>
    ${countriesRows}
  `;
}

function renderHrRequests(rows) {
  if (!hrRequestsRowsEl) {
    return;
  }

  if (!rows || !rows.length) {
    hrRequestsRowsEl.innerHTML = '<p class="alerts-empty">Sin solicitudes pendientes.</p>';
    return;
  }

  hrRequestsRowsEl.innerHTML = rows
    .map((item) => {
      const dateRange = `${String(item.start_date || "").slice(0, 10)} a ${String(item.end_date || "").slice(0, 10)}`;
      const statusLabel = String(item.status || "pending").toUpperCase();
      const pending = item.status === "pending";
      return `
        <article class="supplier-row">
          <p class="alert-store">${item.employee_name} · ${item.market}</p>
          <p class="alert-meta">${item.request_type} · ${dateRange} · ${item.total_days} dias</p>
          <p class="alert-action">${item.reason}</p>
          <p class="alert-severity">Estado ${statusLabel}</p>
          <div class="hr-action-row">
            <button class="hr-action-btn" type="button" data-hr-request-action="approved" data-hr-request-id="${item.id}" ${pending ? "" : "disabled"}>APROBAR</button>
            <button class="hr-action-btn" type="button" data-hr-request-action="rejected" data-hr-request-id="${item.id}" ${pending ? "" : "disabled"}>RECHAZAR</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderHrOnboarding(rows) {
  if (!hrOnboardingRowsEl) {
    return;
  }

  if (!rows || !rows.length) {
    hrOnboardingRowsEl.innerHTML = '<p class="alerts-empty">Sin onboarding activo para este filtro.</p>';
    return;
  }

  hrOnboardingRowsEl.innerHTML = rows
    .map((item) => {
      const completed = Number(item.completed_steps || 0);
      const total = Number(item.total_steps || 0);
      const canAdvance = item.status === "active" && completed < total;
      return `
        <article class="supplier-row">
          <p class="alert-store">${item.employee_name} · ${item.market}</p>
          <p class="alert-meta">${item.position_title} · mentor ${item.mentor_name}</p>
          <p class="alert-action">Progreso ${completed}/${total} · ultimo paso ${item.last_step_key || "N/A"}</p>
          <p class="alert-meta">Estado ${String(item.status).toUpperCase()}</p>
          <div class="hr-action-row">
            <button class="hr-action-btn" type="button" data-hr-onboarding-advance="station_training" data-hr-case-id="${item.id}" ${canAdvance ? "" : "disabled"}>AVANZAR</button>
          </div>
        </article>
      `;
    })
    .join("");
}

async function submitHrRequest(event) {
  event.preventDefault();
  if (!hrRequestEmployeeIdEl || !hrRequestTypeEl || !hrRequestStartDateEl || !hrRequestEndDateEl || !hrRequestReasonEl || !hrRequestStatusEl || !hrRequestSubmitEl) {
    return;
  }

  const reason = (hrRequestReasonEl.value || "").trim();
  if (!reason) {
    hrRequestStatusEl.textContent = "Debes escribir un motivo para la solicitud.";
    return;
  }

  hrRequestSubmitEl.disabled = true;
  hrRequestStatusEl.textContent = "Creando solicitud RRHH...";
  try {
    await postJsonWithHeaders(
      "/api/v1/hr/time-off/requests",
      {
        employee_id: hrRequestEmployeeIdEl.value,
        request_type: hrRequestTypeEl.value,
        start_date: hrRequestStartDateEl.value,
        end_date: hrRequestEndDateEl.value,
        reason,
      },
      {
        "X-API-Role": ALERT_ACTION_ROLE,
        "X-API-Token": ALERT_ACTION_TOKEN,
      },
    );
    hrRequestStatusEl.textContent = "Solicitud creada correctamente.";
    await loadDashboard();
  } catch (error) {
    hrRequestStatusEl.textContent = `Error al crear solicitud: ${error.message}`;
  } finally {
    hrRequestSubmitEl.disabled = false;
  }
}

async function submitOnboardingCase(event) {
  event.preventDefault();
  if (!hrOnboardingEmployeeIdEl || !hrOnboardingPositionEl || !hrOnboardingMentorEl || !hrOnboardingStatusEl || !hrOnboardingSubmitEl) {
    return;
  }

  hrOnboardingSubmitEl.disabled = true;
  hrOnboardingStatusEl.textContent = "Iniciando onboarding...";
  try {
    await postJsonWithHeaders(
      "/api/v1/hr/onboarding/cases/start",
      {
        employee_id: hrOnboardingEmployeeIdEl.value,
        position_title: (hrOnboardingPositionEl.value || "").trim() || "Kitchen Operator",
        mentor_name: (hrOnboardingMentorEl.value || "").trim() || "Ashley Turner",
      },
      {
        "X-API-Role": ALERT_ACTION_ROLE,
        "X-API-Token": ALERT_ACTION_TOKEN,
      },
    );
    hrOnboardingStatusEl.textContent = "Onboarding iniciado.";
    await loadDashboard();
  } catch (error) {
    hrOnboardingStatusEl.textContent = `Error al iniciar onboarding: ${error.message}`;
  } finally {
    hrOnboardingSubmitEl.disabled = false;
  }
}

async function onHrRequestActionClick(event) {
  const actionButton = event.target.closest("[data-hr-request-action]");
  if (!actionButton) {
    return;
  }

  const status = actionButton.getAttribute("data-hr-request-action");
  const requestId = actionButton.getAttribute("data-hr-request-id");
  if (!status || !requestId) {
    return;
  }

  actionButton.disabled = true;
  statusText.textContent = `Actualizando solicitud RRHH ${requestId}...`;
  try {
    await postJsonWithHeaders(
      `/api/v1/hr/time-off/requests/${requestId}/action`,
      {
        status,
        note: status === "approved" ? "Aprobada desde portal RRHH" : "Rechazada desde portal RRHH",
      },
      {
        "X-API-Role": ALERT_ACTION_ROLE,
        "X-API-Token": ALERT_ACTION_TOKEN,
      },
    );
    await loadDashboard();
    statusText.textContent = `Solicitud ${requestId} ${status === "approved" ? "aprobada" : "rechazada"}.`;
  } catch (error) {
    actionButton.disabled = false;
    statusText.textContent = `No fue posible actualizar solicitud ${requestId}: ${error.message}`;
  }
}

async function onHrOnboardingAdvanceClick(event) {
  const actionButton = event.target.closest("[data-hr-onboarding-advance]");
  if (!actionButton) {
    return;
  }

  const caseId = actionButton.getAttribute("data-hr-case-id");
  if (!caseId) {
    return;
  }

  actionButton.disabled = true;
  statusText.textContent = `Avanzando onboarding ${caseId}...`;
  try {
    await postJsonWithHeaders(
      `/api/v1/hr/onboarding/cases/${caseId}/advance`,
      {
        step_key: "station_training",
        note: "Avance registrado desde dashboard RRHH",
      },
      {
        "X-API-Role": ALERT_ACTION_ROLE,
        "X-API-Token": ALERT_ACTION_TOKEN,
      },
    );
    await loadDashboard();
    statusText.textContent = `Onboarding ${caseId} actualizado.`;
  } catch (error) {
    actionButton.disabled = false;
    statusText.textContent = `No fue posible avanzar onboarding ${caseId}: ${error.message}`;
  }
}

function populateTrainingResourceOptions(resources) {
  if (!trainingUpdateResourceIdEl || !Array.isArray(resources) || !resources.length) {
    return;
  }

  const options = resources
    .map((resource) => `<option value="${resource.id}">${resource.title} · ${resource.locale} · ${resource.version}</option>`)
    .join("");
  if (!options) {
    return;
  }

  const previous = trainingUpdateResourceIdEl.value;
  trainingUpdateResourceIdEl.innerHTML = options;
  if (previous && resources.some((resource) => resource.id === previous)) {
    trainingUpdateResourceIdEl.value = previous;
  }
}

function renderTrainingCatalog(items) {
  if (!trainingCatalogRowsEl) {
    return;
  }

  if (!items || !items.length) {
    trainingCatalogRowsEl.innerHTML = '<p class="alerts-empty">Sin recetas para este criterio de busqueda.</p>';
    return;
  }

  trainingCatalogRowsEl.innerHTML = items
    .slice(0, 8)
    .map((item) => {
      const tags = (item.tags || []).join(", ") || "sin tags";
      const updated = item.updated_at
        ? new Date(item.updated_at).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" })
        : "N/A";
      return `
        <article class="supplier-row">
          <p class="alert-store">${item.title}</p>
          <p class="alert-meta">${String(item.locale).toUpperCase()} · version ${item.version}</p>
          <p class="alert-action">${tags}</p>
          <p class="alert-meta">Actualizada: ${updated}</p>
        </article>
      `;
    })
    .join("");
}

function renderTrainingItineraries(items) {
  if (!trainingItinerariesRowsEl) {
    return;
  }

  if (!items || !items.length) {
    trainingItinerariesRowsEl.innerHTML = '<p class="alerts-empty">Sin itinerarios activos.</p>';
    return;
  }

  trainingItinerariesRowsEl.innerHTML = items
    .slice(0, 6)
    .map((item) => `
      <article class="supplier-row">
        <p class="alert-store">${item.title}</p>
        <p class="alert-meta">${item.role_target} · ${String(item.locale).toUpperCase()}</p>
        <p class="alert-action">${item.steps_count} pasos · version ${item.version}</p>
      </article>
    `)
    .join("");
}

function renderTrainingUpdates(items) {
  if (!trainingUpdatesRowsEl) {
    return;
  }

  if (!items || !items.length) {
    trainingUpdatesRowsEl.innerHTML = '<p class="alerts-empty">Sin actualizaciones de receta recientes.</p>';
    return;
  }

  trainingUpdatesRowsEl.innerHTML = items
    .slice(0, 6)
    .map((item) => `
      <article class="supplier-row">
        <p class="alert-store">${item.resource_title}</p>
        <p class="alert-meta">Update #${item.update_id} · ${String(item.locale).toUpperCase()} · version ${item.version}</p>
        <p class="alert-action">${item.change_summary}</p>
        <p class="alert-meta">Entregado ${item.delivered_stores} · ACK ${item.acknowledged_stores} · Pendiente ${item.pending_stores}</p>
      </article>
    `)
    .join("");
}

async function submitTrainingSearch(event) {
  event.preventDefault();
  if (!trainingSearchSubmitEl || !trainingSearchStatusEl) {
    return;
  }

  const query = encodeURIComponent((trainingSearchQueryEl?.value || "").trim());
  const locale = trainingLocaleFilterEl?.value || "";
  const localeParam = locale ? `&locale=${locale}` : "";
  trainingSearchSubmitEl.disabled = true;
  trainingSearchStatusEl.textContent = "Buscando en catalogo de recetas...";
  try {
    const result = await fetchJsonWithHeaders(
      `/api/v1/training/recipes/search?q=${query}${localeParam}&limit=20`,
      {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      },
    );
    renderTrainingCatalog(result.resources || []);
    populateTrainingResourceOptions(result.resources || []);
    trainingSearchStatusEl.textContent = `Busqueda completada: ${Number(result.total_results || 0)} recetas.`;
  } catch (error) {
    trainingSearchStatusEl.textContent = `No fue posible buscar recetas: ${error.message}`;
  } finally {
    trainingSearchSubmitEl.disabled = false;
  }
}

async function submitTrainingUpdate(event) {
  event.preventDefault();
  if (!trainingUpdateResourceIdEl || !trainingUpdateSummaryEl || !trainingUpdateSubmitEl || !trainingUpdateStatusEl) {
    return;
  }

  const summary = (trainingUpdateSummaryEl.value || "").trim();
  if (!summary) {
    trainingUpdateStatusEl.textContent = "Debes escribir el cambio a distribuir.";
    return;
  }

  trainingUpdateSubmitEl.disabled = true;
  trainingUpdateStatusEl.textContent = "Publicando actualizacion simultanea...";
  try {
    const result = await postJsonWithHeaders(
      "/api/v1/training/recipes/updates/publish",
      {
        resource_id: trainingUpdateResourceIdEl.value,
        change_summary: summary,
        locale: (trainingUpdateLocaleEl?.value || "") || null,
        mandatory: true,
      },
      {
        "X-API-Role": ALERT_ACTION_ROLE,
        "X-API-Token": ALERT_ACTION_TOKEN,
      },
    );
    trainingUpdateStatusEl.textContent = `Update #${result.update.update_id} publicado para ${result.update.delivered_stores} locales.`;
    await loadDashboard();
  } catch (error) {
    trainingUpdateStatusEl.textContent = `No fue posible publicar: ${error.message}`;
  } finally {
    trainingUpdateSubmitEl.disabled = false;
  }
}

function getFormatter(currency) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  });
}

function renderStores(stores, currency) {
  const formatter = getFormatter(currency);
  storeRowsEl.innerHTML = stores
    .map(
      (store) => `
        <tr>
          <td>${store.store_name}</td>
          <td>${store.market}</td>
          <td>${formatter.format(store.total_sales)}</td>
          <td>${formatter.format(store.average_ticket)}</td>
          <td>${store.tickets}</td>
        </tr>
      `,
    )
    .join("");
}

function populateReceiptStoreOptions(stores) {
  if (!receiptStoreIdEl || !Array.isArray(stores) || stores.length === 0) {
    return;
  }

  const options = stores
    .filter((store) => store.store_id && store.store_name)
    .map((store) => `<option value="${store.store_id}">${store.store_name}</option>`)
    .join("");

  if (!options) {
    return;
  }

  const previousValue = receiptStoreIdEl.value;
  receiptStoreIdEl.innerHTML = options;
  if (previousValue && stores.some((store) => store.store_id === previousValue)) {
    receiptStoreIdEl.value = previousValue;
  }
}

function renderDashboard(summary, alerts, stores) {
  const formatter = getFormatter(summary.currency);
  weeklySalesEl.textContent = formatter.format(summary.total_sales);
  avgTicketEl.textContent = formatter.format(summary.average_ticket);
  activeStoresEl.textContent = `${alerts.active_stores}/${alerts.total_stores}`;
  inactiveStoresEl.textContent = `${alerts.total_alerts} alertas · ${alerts.critical_alerts} criticas · riesgo ${Number(alerts.critical_ratio_pct || 0).toFixed(1)}% · nivel ${String(alerts.risk_level || "low").toUpperCase()}`;
  populateReceiptStoreOptions(stores);
  renderStores(stores, summary.currency);
  renderInactivity(alerts.alerts);
}

function renderInactivity(alertRows) {
  if (!alertRows.length) {
    inactivityRowsEl.innerHTML = "<p class=\"alerts-empty\">Sin alertas de inactividad en este rango.</p>";
    return;
  }

  inactivityRowsEl.innerHTML = alertRows
    .map((item) => {
      const severityClass = item.severity === "critical" ? "critical" : "warning";
      const severityLabel = item.severity === "critical" ? "Critica" : "Advertencia";
      const lifecycleLabel =
        item.alert_status === "acknowledged"
          ? "ACKNOWLEDGED"
          : item.alert_status === "resolved"
            ? "RESOLVED"
            : "NEW";
      const lastSaleLocal = item.last_sale_local
        ? new Date(item.last_sale_local).toLocaleString("es-CO", {
            dateStyle: "short",
            timeStyle: "short",
          })
        : "Sin registro";
      const canAcknowledge = item.alert_status !== "resolved";
      const canResolve = item.alert_status !== "resolved";
      return `
        <article class="alert-row ${severityClass}">
          <p class="alert-store">${item.store_name}</p>
          <p class="alert-meta">${item.market} · ${item.minutes_without_sales} min sin ventas · TZ ${item.store_timezone}</p>
          <p class="alert-meta">Ultima venta local: ${lastSaleLocal}</p>
          <p class="alert-action">${item.recommended_action || "Validar operacion del local"}</p>
          <p class="alert-meta">Estado: ${lifecycleLabel}</p>
          <div class="alert-controls">
            <button class="alert-btn" type="button" data-alert-action="acknowledged" data-store-id="${item.store_id}" ${canAcknowledge ? "" : "disabled"}>ACK</button>
            <button class="alert-btn" type="button" data-alert-action="resolved" data-store-id="${item.store_id}" ${canResolve ? "" : "disabled"}>RESOLVER</button>
          </div>
          <p class="alert-severity">${severityLabel}</p>
        </article>
      `;
    })
    .join("");
}

async function registerAlertAction(storeId, status) {
  const note =
    status === "resolved"
      ? "Resuelta desde dashboard ejecutivo"
      : "Acusada desde dashboard ejecutivo";
  return postJsonWithHeaders(
    "/api/v1/alerts/inactivity/actions",
    {
      store_id: storeId,
      status,
      owner: "dashboard-ops",
      note,
    },
    {
      "X-API-Role": ALERT_ACTION_ROLE,
      "X-API-Token": ALERT_ACTION_TOKEN,
    },
  );
}

async function onAlertActionClick(event) {
  const actionButton = event.target.closest("[data-alert-action]");
  if (!actionButton) {
    return;
  }

  const status = actionButton.getAttribute("data-alert-action");
  const storeId = actionButton.getAttribute("data-store-id");
  if (!status || !storeId) {
    return;
  }

  actionButton.disabled = true;
  statusText.textContent = `Actualizando alerta ${storeId}...`;

  try {
    await registerAlertAction(storeId, status);
    await loadDashboard();
    const actionText = status === "resolved" ? "resuelta" : "acusada";
    statusText.textContent = `Alerta de ${storeId} ${actionText} correctamente.`;
  } catch (error) {
    actionButton.disabled = false;
    statusText.textContent = `No fue posible actualizar ${storeId}: ${error.message}`;
  }
}

function renderSmartOrders(rows, currency) {
  if (!rows.length) {
    reorderRowsEl.innerHTML = "<p class=\"alerts-empty\">Sin pedidos urgentes en el rango actual.</p>";
    return;
  }

  const formatter = getFormatter(currency);
  reorderRowsEl.innerHTML = rows
    .map((item) => {
      const riskClass = item.risk_level === "critical" ? "critical" : item.risk_level === "warning" ? "warning" : "ok";
      const costLabel = item.estimated_order_cost != null
        ? formatter.format(item.estimated_order_cost)
        : "Sin costo estimado";
      return `
        <article class="order-row ${riskClass}">
          <p class="alert-store">${item.store_name} · ${item.item_name}</p>
          <p class="alert-meta">SKU ${item.sku} · stock ${item.current_stock.toFixed(1)} ${item.unit} · consumo diario ${item.expected_daily_usage.toFixed(1)} ${item.unit}</p>
          <p class="alert-meta">Cobertura ${item.projected_days_of_cover.toFixed(1)} dias · objetivo ${item.target_days_of_cover} dias</p>
          <p class="alert-action">Sugerido pedir ${item.recommended_order_qty.toFixed(1)} ${item.unit} · costo estimado ${costLabel}</p>
          <p class="alert-severity">Riesgo ${String(item.risk_level).toUpperCase()}</p>
        </article>
      `;
    })
    .join("");
}

function renderReceipts(rows, append = false) {
  if (!rows.length && !append) {
    receiptRowsEl.innerHTML = "<tr><td colspan=\"6\">Sin recepciones recientes.</td></tr>";
    receiptLoadMoreEl.disabled = true;
    return;
  }

  const htmlRows = rows
    .map((item) => {
      const timeLabel = item.received_at
        ? new Date(item.received_at).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" })
        : "N/A";
      const unitCost = item.unit_cost == null ? "-" : getFormatter(item.currency).format(item.unit_cost);
      return `
        <tr>
          <td>${timeLabel}</td>
          <td>${item.store_name}</td>
          <td>${item.sku}</td>
          <td>${Number(item.received_qty).toFixed(1)}</td>
          <td>${unitCost}</td>
          <td>${item.currency}</td>
        </tr>
      `;
    })
    .join("");

  if (append && receiptRowsEl.innerHTML && !receiptRowsEl.innerHTML.includes("Sin recepciones recientes")) {
    receiptRowsEl.innerHTML += htmlRows;
  } else {
    receiptRowsEl.innerHTML = htmlRows;
  }

  receiptLoadMoreEl.disabled = rows.length < RECEIPTS_PAGE_SIZE;
}

async function fetchReceiptsPage(offset) {
  const countryParam = countryFilterEl.value ? `&country=${countryFilterEl.value}` : "";
  return fetchJsonWithHeaders(`/api/v1/inventory/receipts?limit=${RECEIPTS_PAGE_SIZE}&offset=${offset}${countryParam}`, {
    "X-API-Role": ALERTS_ROLE,
    "X-API-Token": ALERTS_TOKEN,
  });
}

async function loadMoreReceipts() {
  receiptLoadMoreEl.disabled = true;
  receiptStatusEl.textContent = "Cargando mas recepciones...";
  try {
    const nextOffset = receiptsOffset + RECEIPTS_PAGE_SIZE;
    const rows = await fetchReceiptsPage(nextOffset);
    if (!rows.length) {
      receiptStatusEl.textContent = "No hay mas recepciones para mostrar.";
      return;
    }
    receiptsOffset = nextOffset;
    renderReceipts(rows, true);
    receiptStatusEl.textContent = "Recepciones actualizadas.";
  } catch (error) {
    receiptStatusEl.textContent = `Error al cargar mas recepciones: ${error.message}`;
  }
}

function renderMarkets(markets, currency) {
  const formatter = getFormatter(currency);
  marketGridEl.innerHTML = markets
    .map((market) => {
      const wow = Number(market.wow_variation_pct || 0);
      const wowClass = wow >= 0 ? "positive" : "negative";
      const wowPrefix = wow >= 0 ? "+" : "";
      return `
        <article class="market-card">
          <p class="market-title">${market.market}</p>
          <p class="market-sales">${formatter.format(market.sales)}</p>
          <p class="market-wow ${wowClass}">WoW ${wowPrefix}${wow.toFixed(2)}%</p>
        </article>
      `;
    })
    .join("");
}

function renderTrend(trend, currency) {
  if (!trend.length) {
    trendBarsEl.innerHTML = "<p>Sin datos para el rango seleccionado.</p>";
    return;
  }

  const formatter = getFormatter(currency);
  const maxSales = Math.max(...trend.map((point) => point.total_sales), 1);
  trendBarsEl.innerHTML = trend
    .map((point) => {
      const pct = Math.max((point.total_sales / maxSales) * 100, 4);
      const day = point.day.slice(5);
      return `
        <div class="trend-bar">
          <span class="trend-bar-value">${formatter.format(point.total_sales)}</span>
          <div class="trend-bar-fill" style="height:${pct}%;"></div>
          <span class="trend-bar-label">${day}</span>
        </div>
      `;
    })
    .join("");
}

async function fetchJson(path) {
  if (!API_BASE) {
    throw new Error("API base no configurada");
  }
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json();
}

async function fetchJsonWithHeaders(path, headers) {
  if (!API_BASE) {
    throw new Error("API base no configurada");
  }
  const response = await fetch(`${API_BASE}${path}`, { headers });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json();
}

async function postJsonWithHeaders(path, payload, headers) {
  if (!API_BASE) {
    throw new Error("API base no configurada");
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let detail = "No fue posible registrar la recepcion";
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (error) {
      detail = `${detail} (${response.status})`;
    }
    throw new Error(detail);
  }
  return response.json();
}

function renderFinance(finance, currency) {
  const formatter = getFormatter(currency);
  financeRevenueEl.textContent = formatter.format(finance.total_revenue);
  financeCogsEl.textContent = formatter.format(finance.estimated_cogs);
  financeProfitEl.textContent = formatter.format(finance.estimated_gross_profit);
  financeMarginEl.textContent = `${Number(finance.gross_margin_pct).toFixed(2)}%`;
}

function renderAlertsSla(sla) {
  alertsSlaEl.textContent = `${Number(sla.resolved_within_sla_pct || 0).toFixed(1)}%`;
}

function renderSupplierPrices(rows, currency) {
  if (!supplierPricesRowsEl) {
    return;
  }

  if (!rows.length) {
    supplierPricesRowsEl.innerHTML = "<p class=\"alerts-empty\">Sin registros de precios para este filtro.</p>";
    return;
  }

  const formatter = getFormatter(currency);
  supplierPricesRowsEl.innerHTML = rows
    .map((item) => {
      const validFrom = item.valid_from
        ? new Date(item.valid_from).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" })
        : "N/A";
      return `
        <article class="supplier-row">
          <p class="alert-store">${item.supplier_name} · ${item.item_name}</p>
          <p class="alert-meta">SKU ${item.sku} · ${item.country} · ${item.currency}</p>
          <p class="alert-action">Precio actual: ${formatter.format(Number(item.price || 0))}</p>
          <p class="alert-meta">Vigente desde: ${validFrom}</p>
        </article>
      `;
    })
    .join("");
}

function renderSupplierConsolidated(summary, currency) {
  if (!supplierConsolidatedRowsEl) {
    return;
  }

  if (!summary || !Array.isArray(summary.by_country) || !Array.isArray(summary.by_supplier)) {
    supplierConsolidatedRowsEl.innerHTML = "<p class=\"alerts-empty\">Sin consolidado de compras disponible.</p>";
    return;
  }

  const formatter = getFormatter(currency);
  const countryRows = summary.by_country.length
    ? summary.by_country
        .map(
          (item) => `
        <article class="supplier-row">
          <p class="alert-store">${item.market}</p>
          <p class="alert-meta">${item.receipts_count} recepciones · ${item.suppliers_count} proveedores</p>
          <p class="alert-action">Gasto consolidado: ${formatter.format(Number(item.total_spend || 0))}</p>
        </article>
      `,
        )
        .join("")
    : "<p class=\"alerts-empty\">Sin recepciones en el periodo seleccionado.</p>";

  const topSuppliers = summary.by_supplier.slice(0, 3);
  const suppliersRows = topSuppliers.length
    ? topSuppliers
        .map(
          (item) => `
        <article class="supplier-row">
          <p class="alert-store">${item.supplier_name}</p>
          <p class="alert-meta">${item.market} · ${item.receipts_count} recepciones</p>
          <p class="alert-action">Top gasto: ${formatter.format(Number(item.total_spend || 0))}</p>
        </article>
      `,
        )
        .join("")
    : "";

  supplierConsolidatedRowsEl.innerHTML = `
    <article class="supplier-row">
      <p class="alert-store">Total cadena (${summary.period_days} dias)</p>
      <p class="alert-meta">${summary.total_receipts} recepciones · ${summary.total_suppliers} proveedores</p>
      <p class="alert-action">${formatter.format(Number(summary.total_spend || 0))}</p>
    </article>
    ${countryRows}
    ${suppliersRows}
  `;
}

function renderSupplierAlerts(rows, currency) {
  if (!supplierAlertsRowsEl) {
    return;
  }

  if (!rows.length) {
    supplierAlertsRowsEl.innerHTML = "<p class=\"alerts-empty\">Sin alertas de variacion para este filtro.</p>";
    return;
  }

  const formatter = getFormatter(currency);
  supplierAlertsRowsEl.innerHTML = rows
    .map((item) => {
      const validFrom = item.valid_from
        ? new Date(item.valid_from).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" })
        : "N/A";
      const changePct = Number(item.change_pct || 0);
      const changeClass = changePct >= 0 ? "positive" : "negative";
      const prefix = changePct >= 0 ? "+" : "";
      return `
        <article class="supplier-row ${changeClass}">
          <p class="alert-store">${item.supplier_name} · ${item.item_name}</p>
          <p class="alert-meta">SKU ${item.sku} · ${item.country} · ${item.currency}</p>
          <p class="alert-action">${formatter.format(Number(item.previous_price || 0))} -> ${formatter.format(Number(item.current_price || 0))}</p>
          <p class="alert-severity">Variacion ${prefix}${changePct.toFixed(2)}%</p>
          <p class="alert-meta">Detectada: ${validFrom}</p>
        </article>
      `;
    })
    .join("");
}

function buildSuppliersQuery(limit) {
  const params = new URLSearchParams({
    currency: currencyFilterEl?.value || DEFAULT_CURRENCY,
    limit: String(limit),
  });
  if (countryFilterEl?.value) {
    params.set("country", countryFilterEl.value);
  }
  return params.toString();
}

function resolveMarketingCustomerId() {
  if (countryFilterEl?.value === "US") {
    return "cus-us-001";
  }
  return "cus-co-001";
}

function renderCrmOverview(overview, currency) {
  if (!crmOverviewRowsEl) {
    return;
  }
  if (!overview) {
    crmOverviewRowsEl.innerHTML = "<p class=\"alerts-empty\">Sin datos CRM para este filtro.</p>";
    return;
  }

  const formatter = getFormatter(currency);
  crmOverviewRowsEl.innerHTML = `
    <article class="supplier-row">
      <p class="alert-store">Clientes activos</p>
      <p class="alert-meta">${overview.active_customers}/${overview.total_customers} en ${overview.period_days} dias</p>
      <p class="alert-action">Pedidos: ${overview.total_orders}</p>
    </article>
    <article class="supplier-row">
      <p class="alert-store">Revenue digital</p>
      <p class="alert-meta">Canal app/web periodo ${overview.period_days} dias</p>
      <p class="alert-action">${formatter.format(Number(overview.total_revenue || 0))}</p>
    </article>
  `;
}

function renderCrmCustomers(rows, currency) {
  if (!crmCustomersRowsEl) {
    return;
  }
  if (!rows || !rows.length) {
    crmCustomersRowsEl.innerHTML = "<p class=\"alerts-empty\">Sin clientes CRM para este filtro.</p>";
    return;
  }

  const formatter = getFormatter(currency);
  crmCustomersRowsEl.innerHTML = rows.slice(0, 4).map((item) => {
    const lastOrder = item.last_order_at
      ? new Date(item.last_order_at).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" })
      : "Sin pedido";
    return `
      <article class="supplier-row">
        <p class="alert-store">${item.full_name} · ${String(item.segment).toUpperCase()}</p>
        <p class="alert-meta">Pedidos ${item.orders_count} · puntos ${item.points_balance}</p>
        <p class="alert-action">${formatter.format(Number(item.total_spend || 0))} · favorito ${item.favorite_item || "N/A"}</p>
        <p class="alert-meta">Ultimo pedido: ${lastOrder}</p>
      </article>
    `;
  }).join("");
}

function renderPersonalization(rows, currency, customerId) {
  if (!personalizationRowsEl) {
    return;
  }
  if (!rows || !rows.length) {
    personalizationRowsEl.innerHTML = "<p class=\"alerts-empty\">Sin recomendaciones disponibles.</p>";
    return;
  }

  const formatter = getFormatter(currency);
  personalizationRowsEl.innerHTML = rows.slice(0, 4).map((item) => `
      <article class="supplier-row">
        <p class="alert-store">${item.name}</p>
        <p class="alert-meta">Cliente objetivo: ${customerId}</p>
        <p class="alert-action">${formatter.format(Number(item.expected_price || 0))} · score ${Number(item.score || 0).toFixed(2)}</p>
        <p class="alert-meta">${item.reason}</p>
      </article>
    `).join("");
}

function getFallbackData() {
  return {
    summary: {
      currency: DEFAULT_CURRENCY,
      total_sales: 114230.8,
      average_ticket: 16.7,
    },
    alerts: {
      active_stores: 12,
      total_stores: 14,
      total_alerts: 2,
      critical_alerts: 1,
      warning_alerts: 1,
      critical_ratio_pct: 7.1,
      risk_level: "low",
      alerts: [
        {
          store_id: "med-001",
          store_name: "Brasaland Laureles",
          market: "Colombia",
          store_timezone: "America/Bogota",
          minutes_without_sales: 158,
          severity: "critical",
          last_sale_at: "2026-05-08T12:00:00Z",
          last_sale_local: "2026-05-08T07:00:00-05:00",
          alert_status: "new",
          alert_owner: null,
          alert_note: null,
          alert_updated_at: null,
          recommended_action: "Contact store manager and validate POS/connectivity immediately",
        },
        {
          store_id: "mia-002",
          store_name: "Brasaland Kendall",
          market: "Florida",
          store_timezone: "America/New_York",
          minutes_without_sales: 85,
          severity: "warning",
          last_sale_at: "2026-05-08T13:30:00Z",
          last_sale_local: "2026-05-08T09:30:00-04:00",
          alert_status: "acknowledged",
          alert_owner: "ops-on-duty",
          alert_note: "Investigando demora en caja",
          alert_updated_at: "2026-05-08T10:05:00-04:00",
          recommended_action: "Monitor next 30 minutes and verify staffing and ticket flow",
        },
      ],
    },
    stores: [
      {
        store_name: "Brasaland Laureles",
        market: "Colombia",
        total_sales: 38120,
        average_ticket: 14.5,
        tickets: 2627,
      },
      {
        store_name: "Brasaland Doral",
        market: "Florida",
        total_sales: 42120.8,
        average_ticket: 19.1,
        tickets: 2205,
      },
    ],
    trend: [
      { day: "2026-05-02", total_sales: 13200, tickets: 810 },
      { day: "2026-05-03", total_sales: 14900, tickets: 867 },
      { day: "2026-05-04", total_sales: 12100, tickets: 745 },
      { day: "2026-05-05", total_sales: 16200, tickets: 902 },
      { day: "2026-05-06", total_sales: 17500, tickets: 986 },
      { day: "2026-05-07", total_sales: 16800, tickets: 944 },
      { day: "2026-05-08", total_sales: 18200, tickets: 1020 },
    ],
    markets: [
      { market: "Colombia", sales: 72110, wow_variation_pct: 5.21 },
      { market: "Florida", sales: 42120.8, wow_variation_pct: 2.84 },
    ],
    finance: {
      total_revenue: 114230.8,
      estimated_cogs: 61290.5,
      estimated_gross_profit: 52940.3,
      gross_margin_pct: 46.34,
    },
    alertsSla: {
      resolved_within_sla_pct: 82.5,
    },
    smartOrders: [
      {
        store_id: "mia-002",
        store_name: "Brasaland Kendall",
        country: "US",
        market: "Florida",
        sku: "CHICKEN",
        item_name: "Whole chicken",
        category: "protein",
        unit: "kg",
        current_stock: 35,
        min_stock: 28,
        expected_daily_usage: 14.2,
        projected_days_of_cover: 2.46,
        target_days_of_cover: 7,
        recommended_order_qty: 64.4,
        estimated_unit_cost: 3.55,
        estimated_order_cost: 228.62,
        currency: "USD",
        risk_level: "warning",
      },
    ],
    receipts: [
      {
        id: 1,
        store_id: "med-001",
        store_name: "Brasaland Laureles",
        country: "CO",
        market: "Colombia",
        sku: "CHICKEN",
        received_qty: 12,
        unit_cost: 12100,
        currency: "COP",
        note: "recepcion proveedor semanal",
        received_at: "2026-05-09T13:10:00Z",
        received_by_role: "operations",
      },
    ],
    supplierPrices: [
      {
        supplier_id: "sup-co-01",
        supplier_name: "Andes Proteinas",
        sku: "SKU-POLLO",
        item_name: "Pollo entero",
        country: "CO",
        currency: "COP",
        price: 11900,
        valid_from: "2026-05-09T09:00:00Z",
      },
      {
        supplier_id: "sup-us-01",
        supplier_name: "SunState Foods",
        sku: "SKU-CHICKEN",
        item_name: "Whole chicken",
        country: "US",
        currency: "USD",
        price: 3.7,
        valid_from: "2026-05-09T09:00:00Z",
      },
    ],
    supplierAlerts: [
      {
        supplier_id: "sup-co-01",
        supplier_name: "Andes Proteinas",
        sku: "SKU-POLLO",
        item_name: "Pollo entero",
        country: "CO",
        currency: "COP",
        previous_price: 11100,
        current_price: 11900,
        change_pct: 7.21,
        valid_from: "2026-05-09T09:00:00Z",
      },
    ],
    supplierConsolidated: {
      period_days: 30,
      currency: "USD",
      total_receipts: 14,
      total_suppliers: 4,
      total_spend: 8241.4,
      by_country: [
        { country: "CO", market: "Colombia", receipts_count: 8, suppliers_count: 2, total_spend: 5220.1, currency: "USD" },
        { country: "US", market: "Florida", receipts_count: 6, suppliers_count: 2, total_spend: 3021.3, currency: "USD" },
      ],
      by_supplier: [
        { supplier_id: "sup-co-001", supplier_name: "Avicola Andina", country: "CO", market: "Colombia", receipts_count: 5, total_qty: 116, total_spend: 3512.1, average_unit_cost: 3.42, currency: "USD" },
        { supplier_id: "sup-us-001", supplier_name: "Florida Poultry LLC", country: "US", market: "Florida", receipts_count: 4, total_qty: 91, total_spend: 2190.8, average_unit_cost: 3.55, currency: "USD" },
      ],
    },
    crmOverview: {
      period_days: 30,
      country: null,
      total_customers: 4,
      active_customers: 3,
      total_orders: 9,
      total_revenue: 512.3,
      currency: "USD",
      generated_at: "2026-05-10T12:00:00Z",
    },
    crmCustomers: [
      {
        customer_id: "cus-co-001",
        full_name: "Ana Rios",
        country: "CO",
        segment: "vip",
        points_balance: 420,
        orders_count: 4,
        total_spend: 146.2,
        favorite_item: "combo_familiar",
        last_order_at: "2026-05-09T14:00:00Z",
      },
      {
        customer_id: "cus-us-001",
        full_name: "Emily Carter",
        country: "US",
        segment: "vip",
        points_balance: 530,
        orders_count: 3,
        total_spend: 91.4,
        favorite_item: "family_combo",
        last_order_at: "2026-05-09T18:00:00Z",
      },
    ],
    personalization: {
      customer_id: "cus-co-001",
      currency: "USD",
      generated_at: "2026-05-10T12:00:00Z",
      recommendations: [
        {
          product_id: "prd-family-brasa",
          name: "Combo Familiar Brasa",
          reason: "Coincide con tu comportamiento: familiar, pollo",
          score: 6.4,
          expected_price: 29.9,
          currency: "USD",
        },
      ],
    },
    hrKpis: {
      period_days: 90,
      country: null,
      total_active_headcount: 115,
      total_terminations: 8,
      overall_turnover_rate_pct: 6.72,
      overall_absenteeism_rate_pct: 0.22,
      overall_avg_time_to_fill_days: 23.1,
      by_country: [
        {
          country: "CO",
          market: "Colombia",
          active_headcount: 63,
          total_headcount: 67,
          terminations: 4,
          turnover_rate_pct: 6.25,
          absent_days: 18,
          absenteeism_rate_pct: 0.317,
          open_vacancies: 1,
          avg_time_to_fill_days: 21,
          pending_time_off_requests: 2,
          active_onboarding_cases: 1,
        },
        {
          country: "US",
          market: "Florida",
          active_headcount: 52,
          total_headcount: 56,
          terminations: 4,
          turnover_rate_pct: 7.41,
          absent_days: 11,
          absenteeism_rate_pct: 0.235,
          open_vacancies: 1,
          avg_time_to_fill_days: 25.2,
          pending_time_off_requests: 1,
          active_onboarding_cases: 1,
        },
      ],
    },
    hrRequests: [
      {
        id: 1001,
        employee_id: "emp-co-001",
        employee_name: "Employee CO 001",
        store_id: "med-001",
        country: "CO",
        market: "Colombia",
        request_type: "vacation",
        start_date: "2026-05-28T00:00:00Z",
        end_date: "2026-06-01T00:00:00Z",
        total_days: 5,
        reason: "Vacaciones familiares",
        status: "pending",
      },
    ],
    hrOnboarding: [
      {
        id: 2001,
        employee_id: "emp-us-082",
        employee_name: "Employee US 082",
        store_id: "mia-003",
        country: "US",
        market: "Florida",
        position_title: "Prep Cook",
        mentor_name: "Ashley Turner",
        status: "active",
        completed_steps: 1,
        total_steps: 4,
        last_step_key: "documents",
      },
    ],
    hrEmployees: [
      { id: "emp-co-001", full_name: "Employee CO 001", country: "CO", store_id: "med-001" },
      { id: "emp-us-070", full_name: "Employee US 070", country: "US", store_id: "mia-001" },
    ],
    trainingCatalog: [
      {
        id: "res-co-pol-001",
        title: "Pollo Brasaland clasico",
        locale: "es",
        version: "v2.4",
        tags: ["kitchen", "core", "pollo"],
        updated_at: "2026-05-10T10:30:00Z",
      },
      {
        id: "res-us-fam-002",
        title: "Family combo prep standard",
        locale: "en",
        version: "v1.8",
        tags: ["kitchen", "combo", "quality"],
        updated_at: "2026-05-09T19:20:00Z",
      },
    ],
    trainingItineraries: [
      {
        itinerary_id: "it-kitchen-es-v1",
        title: "Onboarding Cocina Estandar",
        role_target: "kitchen_staff",
        locale: "es",
        steps_count: 6,
        version: "v1.0",
      },
      {
        itinerary_id: "it-kitchen-en-v1",
        title: "Kitchen Onboarding Standard",
        role_target: "kitchen_staff",
        locale: "en",
        steps_count: 6,
        version: "v1.0",
      },
    ],
    trainingUpdates: [
      {
        update_id: 501,
        resource_id: "res-co-pol-001",
        resource_title: "Pollo Brasaland clasico",
        locale: "es",
        version: "v2.5",
        change_summary: "Ajuste de temperatura final de emplatado.",
        delivered_stores: 14,
        acknowledged_stores: 11,
        pending_stores: 3,
      },
    ],
  };
}

function buildQuery() {
  const selectedCurrency = currencyFilterEl?.value || DEFAULT_CURRENCY;
  const params = new URLSearchParams({ currency: selectedCurrency });
  const country = countryFilterEl?.value;
  if (country) {
    params.set("country", country);
  }
  if (startDateEl?.value) {
    params.set("start_date", startDateEl.value);
  }
  if (endDateEl?.value) {
    params.set("end_date", endDateEl.value);
  }
  return params.toString();
}

function setupAutoRefresh() {
  if (!refreshIntervalEl) {
    return;
  }

  if (refreshTimerId !== null) {
    clearInterval(refreshTimerId);
    refreshTimerId = null;
  }

  const refreshSeconds = Number(refreshIntervalEl.value || "0");
  if (refreshSeconds > 0) {
    refreshTimerId = setInterval(() => {
      loadDashboard();
    }, refreshSeconds * 1000);
  }
}

function setDefaultDates() {
  if (!startDateEl || !endDateEl) {
    return;
  }

  const today = new Date();
  const start = new Date(today);
  start.setDate(today.getDate() - 6);
  startDateEl.value = start.toISOString().slice(0, 10);
  endDateEl.value = today.toISOString().slice(0, 10);
}

async function submitInventoryReceipt(event) {
  event.preventDefault();
  const qty = Number(receiptQtyEl.value || "0");
  if (!(qty > 0)) {
    receiptStatusEl.textContent = "La cantidad recibida debe ser mayor a cero.";
    return;
  }

  const payload = {
    store_id: receiptStoreIdEl.value,
    sku: receiptSkuEl.value,
    received_qty: qty,
    currency: receiptCurrencyEl.value,
    note: (receiptNoteEl.value || "").trim() || null,
  };

  const unitCost = Number(receiptUnitCostEl.value || "0");
  if (receiptUnitCostEl.value && unitCost >= 0) {
    payload.unit_cost = unitCost;
  }

  receiptSubmitEl.disabled = true;
  receiptStatusEl.textContent = "Registrando recepcion...";

  try {
    const result = await postJsonWithHeaders(
      "/api/v1/inventory/receipts?days_history=14&target_days=7",
      payload,
      {
        "X-API-Role": RECEIPTS_ROLE,
        "X-API-Token": RECEIPTS_TOKEN,
      },
    );

    receiptStatusEl.textContent = `Recepcion registrada. Stock ${result.previous_stock.toFixed(1)} -> ${result.current_stock.toFixed(1)}. Recomendacion ${String(result.recommendation_status).toUpperCase()}.`;
    await loadDashboard();
  } catch (error) {
    receiptStatusEl.textContent = `Error: ${error.message}`;
  } finally {
    receiptSubmitEl.disabled = false;
  }
}

async function loadDashboard() {
  if (!API_BASE) {
    const fallback = getFallbackData();
    renderDashboard(fallback.summary, fallback.alerts, fallback.stores);
    renderTrend(fallback.trend, fallback.summary.currency);
    renderMarkets(fallback.markets, fallback.summary.currency);
    renderFinance(fallback.finance, fallback.summary.currency);
    renderAlertsSla(fallback.alertsSla);
    renderSmartOrders(fallback.smartOrders, fallback.summary.currency);
    renderExecutiveSalesDual(
      { total_sales: fallback.summary.total_sales },
      { total_sales: fallback.summary.total_sales * 3950 },
    );
    renderMonthlyTopTicket(fallback.stores || [], fallback.summary.currency);
    renderWeeklyReportPreview({
      currency: fallback.summary.currency,
      generated_at: new Date().toISOString(),
      summary: fallback.summary,
      markets: fallback.markets,
    });
    if (executiveAskAnswerEl) {
      executiveAskAnswerEl.textContent = "Semana actual en Florida: 42,120.80 USD (demo).";
    }
    if (executiveAskSourcesEl) {
      executiveAskSourcesEl.textContent = "Fuentes: sales_events, stores, rule:sales_week_country_single (demo)";
    }
    if (executiveAskStatusEl) {
      executiveAskStatusEl.textContent = "Asistente IA en modo demo.";
    }
    renderSupplierConsolidated(fallback.supplierConsolidated, fallback.summary.currency);
    renderSupplierPrices(fallback.supplierPrices, fallback.summary.currency);
    renderSupplierAlerts(fallback.supplierAlerts, fallback.summary.currency);
    renderCrmOverview(fallback.crmOverview, fallback.summary.currency);
    renderCrmCustomers(fallback.crmCustomers, fallback.summary.currency);
    renderPersonalization(fallback.personalization.recommendations, fallback.summary.currency, fallback.personalization.customer_id);
    renderHrKpis(fallback.hrKpis);
    renderHrRequests(fallback.hrRequests || []);
    renderHrOnboarding(fallback.hrOnboarding || []);
    populateHrEmployeeOptions(fallback.hrEmployees || []);
    renderTrainingCatalog(fallback.trainingCatalog || []);
    renderTrainingItineraries(fallback.trainingItineraries || []);
    renderTrainingUpdates(fallback.trainingUpdates || []);
    populateTrainingResourceOptions(fallback.trainingCatalog || []);
    if (trainingSearchStatusEl) {
      trainingSearchStatusEl.textContent = "Catalogo demo cargado.";
    }
    if (trainingUpdateStatusEl) {
      trainingUpdateStatusEl.textContent = "Listo para publicar actualizaciones demo.";
    }
    receiptsOffset = 0;
    renderReceipts(fallback.receipts, false);
    salesCurrencyDetailEl.textContent = "Consolidado USD";
    statusText.textContent = "Modo demo local (archivo HTML). Para API en vivo usa ?apiBase=http://localhost:8000";
    return;
  }

  statusText.textContent = `Conectando con API (${API_BASE})...`;
  const query = buildQuery();
  const suppliersQuery = buildSuppliersQuery(8);
  const marketingCustomerId = resolveMarketingCustomerId();
  try {
    const trainingSearchQuery = encodeURIComponent((trainingSearchQueryEl?.value || "").trim());
    const trainingLocale = trainingLocaleFilterEl?.value || "";
    const trainingLocaleParam = trainingLocale ? `&locale=${trainingLocale}` : "";
    const [summary, alerts, stores, trend, markets, finance, alertsSla, smartOrders, receipts, supplierPrices, supplierAlerts, supplierConsolidated, crmOverview, crmCustomers, personalization, hrKpis, hrRequests, hrOnboarding, hrEmployees, trainingCatalog, trainingItineraries, trainingUpdates, executiveSummaryUsd, executiveSummaryCop, monthlyTopStores, weeklyReport] = await Promise.all([
      fetchJson(`/api/v1/sales/summary?period=week&${query}`),
      fetchJsonWithHeaders(`/api/v1/alerts/inactivity?window_minutes=60&limit=6&${query}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJson(`/api/v1/sales/by-store?${query}`),
      fetchJson(`/api/v1/sales/daily-trend?${query}`),
      fetchJson(`/api/v1/markets/summary?${query}`),
      fetchJsonWithHeaders(`/api/v1/finance/kpis?${query}`, {
        "X-API-Role": FINANCE_ROLE,
        "X-API-Token": FINANCE_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/alerts/inactivity/sla?days=7&sla_target_minutes=30${countryFilterEl.value ? `&country=${countryFilterEl.value}` : ""}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/orders/recommendations?days_history=14&target_days=7&only_at_risk=true&limit=6&${query}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchReceiptsPage(0),
      fetchJsonWithHeaders(`/api/v1/suppliers/prices?${suppliersQuery}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/suppliers/price-alerts?threshold_pct=5&${suppliersQuery}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/suppliers/purchases/consolidated?days=30&${suppliersQuery}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/marketing/crm/overview?days=30&${query}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/marketing/crm/customers?limit=10&${query}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/marketing/personalization/recommendations?customer_id=${marketingCustomerId}&currency=${currencyFilterEl?.value || DEFAULT_CURRENCY}&limit=5`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/hr/kpis/overview?days=90${countryFilterEl.value ? `&country=${countryFilterEl.value}` : ""}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/hr/time-off/requests?status=pending&limit=8${countryFilterEl.value ? `&country=${countryFilterEl.value}` : ""}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/hr/onboarding/cases?status=active&limit=8${countryFilterEl.value ? `&country=${countryFilterEl.value}` : ""}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/hr/employees?employment_status=active&limit=200${countryFilterEl.value ? `&country=${countryFilterEl.value}` : ""}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/training/recipes/search?q=${trainingSearchQuery}${trainingLocaleParam}&limit=8`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/training/onboarding/itineraries?limit=8${trainingLocale ? `&locale=${trainingLocale}` : ""}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJsonWithHeaders(`/api/v1/training/recipes/updates?limit=8${trainingLocale ? `&locale=${trainingLocale}` : ""}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
      fetchJson(`/api/v1/sales/summary?period=week&currency=USD`),
      fetchJson(`/api/v1/sales/summary?period=week&currency=COP`),
      fetchJson(`/api/v1/sales/by-store?currency=USD&start_date=${monthStartIsoDate()}&end_date=${todayIsoDate()}`),
      fetchJsonWithHeaders(`/api/v1/executive/weekly-report?currency=${currencyFilterEl?.value || DEFAULT_CURRENCY}`, {
        "X-API-Role": ALERTS_ROLE,
        "X-API-Token": ALERTS_TOKEN,
      }),
    ]);

    renderDashboard(summary, alerts, stores);
    renderTrend(trend, summary.currency);
    renderMarkets(markets, summary.currency);
    renderFinance(finance, summary.currency);
    renderAlertsSla(alertsSla);
    renderSmartOrders(smartOrders.recommendations || [], summary.currency);
    renderExecutiveSalesDual(executiveSummaryUsd, executiveSummaryCop);
    renderMonthlyTopTicket(monthlyTopStores || [], "USD");
    renderWeeklyReportPreview(weeklyReport);
    if (executiveAskStatusEl && !executiveAskStatusEl.textContent.includes("consult")) {
      executiveAskStatusEl.textContent = "Asistente IA listo para preguntas ejecutivas.";
    }
    renderSupplierConsolidated(supplierConsolidated, summary.currency);
    renderSupplierPrices(supplierPrices || [], summary.currency);
    renderSupplierAlerts(supplierAlerts || [], summary.currency);
    renderCrmOverview(crmOverview, summary.currency);
    renderCrmCustomers(crmCustomers || [], summary.currency);
    renderPersonalization((personalization && personalization.recommendations) || [], summary.currency, marketingCustomerId);
    renderHrKpis(hrKpis);
    renderHrRequests(hrRequests || []);
    renderHrOnboarding(hrOnboarding || []);
    populateHrEmployeeOptions(hrEmployees || []);
    renderTrainingCatalog((trainingCatalog && trainingCatalog.resources) || []);
    renderTrainingItineraries(trainingItineraries || []);
    renderTrainingUpdates(trainingUpdates || []);
    populateTrainingResourceOptions((trainingCatalog && trainingCatalog.resources) || []);
    if (trainingSearchStatusEl) {
      trainingSearchStatusEl.textContent = `Catalogo cargado: ${Number((trainingCatalog && trainingCatalog.total_results) || 0)} recetas.`;
    }
    if (trainingUpdateStatusEl) {
      trainingUpdateStatusEl.textContent = "Listo para publicar nueva actualizacion.";
    }
    receiptsOffset = 0;
    renderReceipts(receipts || [], false);
    salesCurrencyDetailEl.textContent = `Consolidado ${summary.currency}`;
    const nowLabel = new Date().toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const refreshLabel = Number(refreshIntervalEl.value || "0");
    statusText.textContent = refreshLabel > 0
      ? `Datos en vivo. Ultima actualizacion ${nowLabel}. Auto refresh cada ${refreshLabel}s.`
      : `Datos en vivo. Ultima actualizacion ${nowLabel}.`;
  } catch (error) {
    const fallback = getFallbackData();
    renderDashboard(fallback.summary, fallback.alerts, fallback.stores);
    renderTrend(fallback.trend, fallback.summary.currency);
    renderMarkets(fallback.markets, fallback.summary.currency);
    renderFinance(fallback.finance, fallback.summary.currency);
    renderAlertsSla(fallback.alertsSla);
    renderSmartOrders(fallback.smartOrders, fallback.summary.currency);
    renderExecutiveSalesDual(
      { total_sales: fallback.summary.total_sales },
      { total_sales: fallback.summary.total_sales * 3950 },
    );
    renderMonthlyTopTicket(fallback.stores || [], fallback.summary.currency);
    renderWeeklyReportPreview({
      currency: fallback.summary.currency,
      generated_at: new Date().toISOString(),
      summary: fallback.summary,
      markets: fallback.markets,
    });
    if (executiveAskAnswerEl) {
      executiveAskAnswerEl.textContent = "Modo demo: pregunta sugerida -> Que local tiene el ticket medio mas alto este mes?";
    }
    if (executiveAskSourcesEl) {
      executiveAskSourcesEl.textContent = "Fuentes: datos demo en navegador";
    }
    if (executiveAskStatusEl) {
      executiveAskStatusEl.textContent = "API no disponible, asistente en modo demo.";
    }
    renderSupplierConsolidated(fallback.supplierConsolidated, fallback.summary.currency);
    renderSupplierPrices(fallback.supplierPrices, fallback.summary.currency);
    renderSupplierAlerts(fallback.supplierAlerts, fallback.summary.currency);
    renderCrmOverview(fallback.crmOverview, fallback.summary.currency);
    renderCrmCustomers(fallback.crmCustomers, fallback.summary.currency);
    renderPersonalization(fallback.personalization.recommendations, fallback.summary.currency, fallback.personalization.customer_id);
    renderHrKpis(fallback.hrKpis);
    renderHrRequests(fallback.hrRequests || []);
    renderHrOnboarding(fallback.hrOnboarding || []);
    populateHrEmployeeOptions(fallback.hrEmployees || []);
    renderTrainingCatalog(fallback.trainingCatalog || []);
    renderTrainingItineraries(fallback.trainingItineraries || []);
    renderTrainingUpdates(fallback.trainingUpdates || []);
    populateTrainingResourceOptions(fallback.trainingCatalog || []);
    if (trainingSearchStatusEl) {
      trainingSearchStatusEl.textContent = "API no disponible, mostrando catalogo demo.";
    }
    if (trainingUpdateStatusEl) {
      trainingUpdateStatusEl.textContent = "Modo demo: publicacion deshabilitada en API offline.";
    }
    receiptsOffset = 0;
    renderReceipts(fallback.receipts, false);
    salesCurrencyDetailEl.textContent = "Consolidado USD";
    statusText.textContent = `API no disponible en ${API_BASE}. Mostrando modo demo.`;
  }
}

function bootstrapDashboard() {
  if (!statusText || !weeklySalesEl || !storeRowsEl || !inactivityRowsEl) {
    return;
  }

  if (applyFiltersButton) {
    applyFiltersButton.addEventListener("click", () => {
      loadDashboard();
    });
  }

  if (refreshIntervalEl) {
    refreshIntervalEl.addEventListener("change", () => {
      setupAutoRefresh();
      loadDashboard();
    });
  }

  if (currencyFilterEl) {
    currencyFilterEl.addEventListener("change", () => {
      loadDashboard();
    });
  }

  if (receiptFormEl) {
    receiptFormEl.addEventListener("submit", submitInventoryReceipt);
  }

  if (receiptLoadMoreEl) {
    receiptLoadMoreEl.addEventListener("click", loadMoreReceipts);
  }

  if (inactivityRowsEl) {
    inactivityRowsEl.addEventListener("click", onAlertActionClick);
  }

  if (hrRequestFormEl) {
    hrRequestFormEl.addEventListener("submit", submitHrRequest);
  }

  if (hrOnboardingFormEl) {
    hrOnboardingFormEl.addEventListener("submit", submitOnboardingCase);
  }

  if (hrRequestsRowsEl) {
    hrRequestsRowsEl.addEventListener("click", onHrRequestActionClick);
  }

  if (hrOnboardingRowsEl) {
    hrOnboardingRowsEl.addEventListener("click", onHrOnboardingAdvanceClick);
  }

  if (trainingSearchFormEl) {
    trainingSearchFormEl.addEventListener("submit", submitTrainingSearch);
  }

  if (trainingUpdateFormEl) {
    trainingUpdateFormEl.addEventListener("submit", submitTrainingUpdate);
  }

  if (executiveAskFormEl) {
    executiveAskFormEl.addEventListener("submit", submitExecutiveAsk);
  }

  if (weeklyReportRefreshEl) {
    weeklyReportRefreshEl.addEventListener("click", refreshWeeklyReportPreview);
  }

  if (currencyFilterEl && receiptCurrencyEl) {
    currencyFilterEl.addEventListener("change", () => {
      receiptCurrencyEl.value = currencyFilterEl.value || DEFAULT_CURRENCY;
    });
    receiptCurrencyEl.value = currencyFilterEl.value || DEFAULT_CURRENCY;
  }

  setDefaultDates();
  setDefaultHrDates();
  setupAutoRefresh();
  loadDashboard();
}

bootstrapDashboard();
