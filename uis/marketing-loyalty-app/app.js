const DEFAULT_API_BASE = "http://localhost:8000";

function resolveApiBase() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("apiBase");
  if (fromQuery) {
    return fromQuery.replace(/\/$/, "");
  }

  if (window.location.protocol === "file:") {
    return null;
  }

  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return `${window.location.protocol}//${host}:8000`;
  }

  return DEFAULT_API_BASE;
}

const API_BASE = resolveApiBase();
const EXEC_ROLE = "executive";
const EXEC_TOKEN = "brasaland-executive-token";
const OPS_ROLE = "operations";
const OPS_TOKEN = "brasaland-operations-token";

const statusText = document.getElementById("statusText");
const customerSelect = document.getElementById("customerSelect");
const currencySelect = document.getElementById("currencySelect");
const pointsMetric = document.getElementById("pointsMetric");
const segmentDetail = document.getElementById("segmentDetail");
const ordersMetric = document.getElementById("ordersMetric");
const lastOrderDetail = document.getElementById("lastOrderDetail");
const storeSelect = document.getElementById("storeSelect");
const itemsInput = document.getElementById("itemsInput");
const amountInput = document.getElementById("amountInput");
const channelSelect = document.getElementById("channelSelect");
const orderForm = document.getElementById("orderForm");
const orderSubmit = document.getElementById("orderSubmit");
const orderStatus = document.getElementById("orderStatus");
const recommendationsRows = document.getElementById("recommendationsRows");
const historyRows = document.getElementById("historyRows");

let cachedCustomers = [];

async function fetchJson(path, headers = {}) {
  if (!API_BASE) {
    throw new Error("API base no configurada");
  }
  const response = await fetch(`${API_BASE}${path}`, { headers });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json();
}

async function postJson(path, payload, headers = {}) {
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
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_error) {
      // Keep fallback detail.
    }
    throw new Error(detail);
  }
  return response.json();
}

function moneyFormatter(currency) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  });
}

function selectedCustomerId() {
  return customerSelect.value;
}

function selectedCurrency() {
  return currencySelect.value;
}

function renderRecommendations(rows, currency) {
  if (!rows?.length) {
    recommendationsRows.innerHTML = '<p class="detail">Sin recomendaciones por ahora.</p>';
    return;
  }
  const format = moneyFormatter(currency);
  recommendationsRows.innerHTML = rows
    .map(
      (row) => `
      <article class="row">
        <h3>${row.name}</h3>
        <p>${format.format(Number(row.expected_price || 0))} · score ${Number(row.score || 0).toFixed(2)}</p>
        <p>${row.reason}</p>
      </article>
    `,
    )
    .join("");
}

function renderHistory(rows, currency) {
  if (!rows?.length) {
    historyRows.innerHTML = '<p class="detail">Este cliente aun no tiene pedidos digitales.</p>';
    ordersMetric.textContent = "0";
    lastOrderDetail.textContent = "Ultimo pedido -";
    return;
  }
  const format = moneyFormatter(currency);
  ordersMetric.textContent = String(rows.length);
  lastOrderDetail.textContent = `Ultimo pedido ${new Date(rows[0].ordered_at).toLocaleString("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
  })}`;
  historyRows.innerHTML = rows
    .map(
      (row) => `
      <article class="row">
        <h3>${format.format(Number(row.total_amount || 0))} · ${String(row.channel).toUpperCase()}</h3>
        <p>Local ${row.store_id} · ${new Date(row.ordered_at).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" })}</p>
        <p>${(row.order_items || []).join(", ")}</p>
      </article>
    `,
    )
    .join("");
}

async function loadStores() {
  const rows = await fetchJson("/api/v1/stores");
  storeSelect.innerHTML = rows
    .map((store) => `<option value="${store.id}">${store.name}</option>`)
    .join("");
}

async function loadCustomers() {
  const currency = selectedCurrency();
  cachedCustomers = await fetchJson(
    `/api/v1/marketing/crm/customers?currency=${currency}&limit=100`,
    {
      "X-API-Role": EXEC_ROLE,
      "X-API-Token": EXEC_TOKEN,
    },
  );

  if (!cachedCustomers.length) {
    customerSelect.innerHTML = "";
    throw new Error("No hay clientes CRM disponibles");
  }

  const previous = customerSelect.value;
  customerSelect.innerHTML = cachedCustomers
    .map((customer) => `<option value="${customer.customer_id}">${customer.full_name} (${customer.country})</option>`)
    .join("");

  if (previous && cachedCustomers.some((customer) => customer.customer_id === previous)) {
    customerSelect.value = previous;
  }
}

async function loadCustomerExperience() {
  const customerId = selectedCustomerId();
  const currency = selectedCurrency();

  const [profile, history, personalization] = await Promise.all([
    fetchJson(`/api/v1/customers/${customerId}`, {
      "X-API-Role": EXEC_ROLE,
      "X-API-Token": EXEC_TOKEN,
    }),
    fetchJson(`/api/v1/marketing/customers/${customerId}/history?limit=8`, {
      "X-API-Role": EXEC_ROLE,
      "X-API-Token": EXEC_TOKEN,
    }),
    fetchJson(`/api/v1/marketing/personalization/recommendations?customer_id=${customerId}&currency=${currency}&limit=6`, {
      "X-API-Role": EXEC_ROLE,
      "X-API-Token": EXEC_TOKEN,
    }),
  ]);

  pointsMetric.textContent = String(profile.points_balance);
  segmentDetail.textContent = `Segmento ${String(profile.segment).toUpperCase()} · ${profile.country}`;
  renderHistory(history, currency);
  renderRecommendations(personalization.recommendations || [], currency);
}

async function submitOrder(event) {
  event.preventDefault();
  const customerId = selectedCustomerId();
  const currency = selectedCurrency();
  const amount = Number(amountInput.value || "0");

  if (!(amount > 0)) {
    orderStatus.textContent = "El total debe ser mayor a cero.";
    return;
  }

  const items = (itemsInput.value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  if (!items.length) {
    orderStatus.textContent = "Debes incluir al menos un item.";
    return;
  }

  const payload = {
    customer_id: customerId,
    store_id: storeSelect.value,
    order_items: items,
    total_amount: amount,
    currency,
    channel: channelSelect.value,
  };

  orderSubmit.disabled = true;
  orderStatus.textContent = "Registrando pedido...";

  try {
    const result = await postJson("/api/v1/marketing/orders", payload, {
      "X-API-Role": OPS_ROLE,
      "X-API-Token": OPS_TOKEN,
    });
    orderStatus.textContent = `Pedido ${result.order_id} registrado. +${result.awarded_points} puntos.`;
    await loadCustomers();
    await loadCustomerExperience();
  } catch (error) {
    orderStatus.textContent = `Error: ${error.message}`;
  } finally {
    orderSubmit.disabled = false;
  }
}

async function refreshAll() {
  statusText.textContent = API_BASE ? `Conectando con ${API_BASE}...` : "Modo demo no habilitado para esta app.";
  try {
    await Promise.all([loadStores(), loadCustomers()]);
    await loadCustomerExperience();
    statusText.textContent = `Listo · actualizado ${new Date().toLocaleTimeString("es-CO", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })}`;
  } catch (error) {
    statusText.textContent = `No fue posible cargar la app: ${error.message}`;
  }
}

function bootstrap() {
  customerSelect.addEventListener("change", () => {
    loadCustomerExperience();
  });

  currencySelect.addEventListener("change", () => {
    refreshAll();
  });

  orderForm.addEventListener("submit", submitOrder);
  refreshAll();
}

bootstrap();
