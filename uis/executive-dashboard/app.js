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
let refreshTimerId = null;
const RECEIPTS_PAGE_SIZE = 8;
let receiptsOffset = 0;

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

function renderDashboard(summary, alerts, stores) {
  const formatter = getFormatter(summary.currency);
  weeklySalesEl.textContent = formatter.format(summary.total_sales);
  avgTicketEl.textContent = formatter.format(summary.average_ticket);
  activeStoresEl.textContent = `${alerts.active_stores}/${alerts.total_stores}`;
  inactiveStoresEl.textContent = `${alerts.total_alerts} alertas · ${alerts.critical_alerts} criticas · riesgo ${Number(alerts.critical_ratio_pct || 0).toFixed(1)}% · nivel ${String(alerts.risk_level || "low").toUpperCase()}`;
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
      return `
        <article class="alert-row ${severityClass}">
          <p class="alert-store">${item.store_name}</p>
          <p class="alert-meta">${item.market} · ${item.minutes_without_sales} min sin ventas · TZ ${item.store_timezone}</p>
          <p class="alert-meta">Ultima venta local: ${lastSaleLocal}</p>
          <p class="alert-action">${item.recommended_action || "Validar operacion del local"}</p>
          <p class="alert-meta">Estado: ${lifecycleLabel}</p>
          <p class="alert-severity">${severityLabel}</p>
        </article>
      `;
    })
    .join("");
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
    receiptsOffset = 0;
    renderReceipts(fallback.receipts, false);
    salesCurrencyDetailEl.textContent = "Consolidado USD";
    statusText.textContent = "Modo demo local (archivo HTML). Para API en vivo usa ?apiBase=http://localhost:8000";
    return;
  }

  statusText.textContent = `Conectando con API (${API_BASE})...`;
  const query = buildQuery();
  try {
    const [summary, alerts, stores, trend, markets, finance, alertsSla, smartOrders, receipts] = await Promise.all([
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
    ]);

    renderDashboard(summary, alerts, stores);
    renderTrend(trend, summary.currency);
    renderMarkets(markets, summary.currency);
    renderFinance(finance, summary.currency);
    renderAlertsSla(alertsSla);
    renderSmartOrders(smartOrders.recommendations || [], summary.currency);
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

  if (currencyFilterEl && receiptCurrencyEl) {
    currencyFilterEl.addEventListener("change", () => {
      receiptCurrencyEl.value = currencyFilterEl.value || DEFAULT_CURRENCY;
    });
    receiptCurrencyEl.value = currencyFilterEl.value || DEFAULT_CURRENCY;
  }

  setDefaultDates();
  setupAutoRefresh();
  loadDashboard();
}

bootstrapDashboard();
