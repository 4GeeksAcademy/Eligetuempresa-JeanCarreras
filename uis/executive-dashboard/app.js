const API_BASE = "http://localhost:8000";
const DEFAULT_CURRENCY = "USD";
const FINANCE_ROLE = "executive";
const FINANCE_TOKEN = "brasaland-executive-token";

const statusText = document.getElementById("statusText");
const weeklySalesEl = document.getElementById("weeklySales");
const avgTicketEl = document.getElementById("avgTicket");
const activeStoresEl = document.getElementById("activeStores");
const storeRowsEl = document.getElementById("storeRows");
const countryFilterEl = document.getElementById("countryFilter");
const startDateEl = document.getElementById("startDate");
const endDateEl = document.getElementById("endDate");
const applyFiltersButton = document.getElementById("applyFilters");
const trendBarsEl = document.getElementById("trendBars");
const marketGridEl = document.getElementById("marketGrid");
const financeRevenueEl = document.getElementById("financeRevenue");
const financeCogsEl = document.getElementById("financeCogs");
const financeProfitEl = document.getElementById("financeProfit");
const financeMarginEl = document.getElementById("financeMargin");

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
  renderStores(stores, summary.currency);
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
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json();
}

async function fetchJsonWithHeaders(path, headers) {
  const response = await fetch(`${API_BASE}${path}`, { headers });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
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
  };
}

function buildQuery() {
  const params = new URLSearchParams({ currency: DEFAULT_CURRENCY });
  const country = countryFilterEl.value;
  if (country) {
    params.set("country", country);
  }
  if (startDateEl.value) {
    params.set("start_date", startDateEl.value);
  }
  if (endDateEl.value) {
    params.set("end_date", endDateEl.value);
  }
  return params.toString();
}

function setDefaultDates() {
  const today = new Date();
  const start = new Date(today);
  start.setDate(today.getDate() - 6);
  startDateEl.value = start.toISOString().slice(0, 10);
  endDateEl.value = today.toISOString().slice(0, 10);
}

async function loadDashboard() {
  statusText.textContent = "Conectando con API...";
  const query = buildQuery();
  try {
    const [summary, alerts, stores, trend, markets, finance] = await Promise.all([
      fetchJson(`/api/v1/sales/summary?period=week&${query}`),
      fetchJson(`/api/v1/alerts/inactivity?window_minutes=60&${query}`),
      fetchJson(`/api/v1/sales/by-store?${query}`),
      fetchJson(`/api/v1/sales/daily-trend?${query}`),
      fetchJson(`/api/v1/markets/summary?${query}`),
      fetchJsonWithHeaders(`/api/v1/finance/kpis?${query}`, {
        "X-API-Role": FINANCE_ROLE,
        "X-API-Token": FINANCE_TOKEN,
      }),
    ]);

    renderDashboard(summary, alerts, stores);
    renderTrend(trend, summary.currency);
    renderMarkets(markets, summary.currency);
    renderFinance(finance, summary.currency);
    statusText.textContent = "Datos en vivo conectados al API local.";
  } catch (error) {
    const fallback = getFallbackData();
    renderDashboard(fallback.summary, fallback.alerts, fallback.stores);
    renderTrend(fallback.trend, fallback.summary.currency);
    renderMarkets(fallback.markets, fallback.summary.currency);
    renderFinance(fallback.finance, fallback.summary.currency);
    statusText.textContent = "API no disponible. Mostrando modo demo.";
  }
}

applyFiltersButton.addEventListener("click", () => {
  loadDashboard();
});

setDefaultDates();
loadDashboard();
