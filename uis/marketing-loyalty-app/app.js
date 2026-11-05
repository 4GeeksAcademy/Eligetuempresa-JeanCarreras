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





const statusText = document.getElementById("statusText");
const retryAppButton = document.getElementById("retryApp");
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

function authenticatedHeaders(headers = {}) {
  const target = new URL(API_BASE, window.location.href);
  const local = ["localhost", "127.0.0.1"].includes(window.location.hostname)
    && target.hostname === window.location.hostname && target.port === "8000"
    && target.protocol === window.location.protocol;
  if (!(target.origin === window.location.origin || local)) {
    throw new Error("Origen de API no autorizado para enviar credenciales.");
  }
  const token = window.localStorage.getItem("brasaland_token");
  if (!token) throw new Error("Inicia sesion antes de consultar datos internos.");
  const filtered = Object.fromEntries(Object.entries(headers).filter(
    ([name]) => !/^x-api-(role|token)$/i.test(name),
  ));
  return { ...filtered, Authorization: `Bearer ${token}` };
}

async function fetchJson(path, headers = {}) {
  if (!API_BASE) {
    throw new Error("La conexion con la API no esta disponible. Reintenta en unos minutos.");
  }
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { headers: window.BrasalandSecurity.authHeaders(API_BASE, headers) });
  } catch (_error) {
    throw new Error("No se pudo conectar con la API. Reintenta en unos minutos.");
  }
  if (!response.ok) {
    throw new Error("No fue posible obtener los datos solicitados. Reintenta nuevamente.");
  }
  try {
    return await response.json();
  } catch (_error) {
    throw new Error("La API devolvio datos no disponibles. Reintenta nuevamente.");
  }
}

async function postJson(path, payload, headers = {}) {
  if (!API_BASE) {
    throw new Error("La conexion con la API no esta disponible. Reintenta en unos minutos.");
  }
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...window.BrasalandSecurity.authHeaders(API_BASE, headers),
      },
      body: JSON.stringify(payload),
    });
  } catch (_error) {
    throw new Error("No se pudo conectar con la API. Reintenta en unos minutos.");
  }
  if (!response.ok) {
    throw new Error("No fue posible registrar el pedido. Revisa los datos e intenta nuevamente.");
  }
  try {
    return await response.json();
  } catch (_error) {
    throw new Error("La API devolvio datos no disponibles. Reintenta nuevamente.");
  }
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
    recommendationsRows.innerHTML = window.BrasalandSecurity.sanitizeHTML('<p class="detail">Sin recomendaciones por ahora.</p>');
    return;
  }
  const format = moneyFormatter(currency);
  recommendationsRows.innerHTML = window.BrasalandSecurity.sanitizeHTML(rows
    .map(
      (row) => `
      <article class="row">
        <h3>${row.name}</h3>
        <p>${format.format(Number(row.expected_price || 0))} · score ${Number(row.score || 0).toFixed(2)}</p>
        <p>${row.reason}</p>
      </article>
    `,
    )
    .join(""));
}

function renderHistory(rows, currency) {
  if (!rows?.length) {
    historyRows.innerHTML = window.BrasalandSecurity.sanitizeHTML('<p class="detail">Este cliente aun no tiene pedidos digitales.</p>');
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
  historyRows.innerHTML = window.BrasalandSecurity.sanitizeHTML(rows
    .map(
      (row) => `
      <article class="row">
        <h3>${format.format(Number(row.total_amount || 0))} · ${String(row.channel).toUpperCase()}</h3>
        <p>Local ${row.store_id} · ${new Date(row.ordered_at).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" })}</p>
        <p>${(row.order_items || []).join(", ")}</p>
      </article>
    `,
    )
    .join(""));
}

async function loadStores() {
  const rows = await fetchJson("/api/v1/stores");
  storeSelect.innerHTML = window.BrasalandSecurity.sanitizeHTML(rows
    .map((store) => `<option value="${store.id}">${store.name}</option>`)
    .join(""));
}

async function loadCustomers() {
  const currency = selectedCurrency();
  cachedCustomers = await fetchJson(
    `/api/v1/marketing/crm/customers?currency=${currency}&limit=100`,
    {},
  );

  if (!cachedCustomers.length) {
    customerSelect.innerHTML = window.BrasalandSecurity.sanitizeHTML("");
    throw new Error("No hay clientes CRM disponibles");
  }

  const previous = customerSelect.value;
  customerSelect.innerHTML = window.BrasalandSecurity.sanitizeHTML(cachedCustomers
    .map((customer) => `<option value="${customer.customer_id}">${customer.full_name} (${customer.country})</option>`)
    .join(""));

  if (previous && cachedCustomers.some((customer) => customer.customer_id === previous)) {
    customerSelect.value = previous;
  }
}

async function loadCustomerExperience() {
  const customerId = selectedCustomerId();
  const currency = selectedCurrency();

  const [profile, history, personalization] = await Promise.all([
    fetchJson(`/api/v1/customers/${customerId}`, {}),
    fetchJson(`/api/v1/marketing/customers/${customerId}/history?limit=8`, {}),
    fetchJson(`/api/v1/marketing/personalization/recommendations?customer_id=${customerId}&currency=${currency}&limit=6`, {}),
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
    const result = await postJson("/api/v1/marketing/orders", payload, {});
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
  if (retryAppButton) {
    retryAppButton.hidden = true;
  }
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
    statusText.textContent = `No fue posible cargar la app: ${error.message} Reintenta nuevamente.`;
    if (retryAppButton) {
      retryAppButton.hidden = false;
    }
  }
}

function bootstrap() {
  customerSelect.addEventListener("change", () => {
    void refreshAll();
  });

  currencySelect.addEventListener("change", () => {
    void refreshAll();
  });

  if (retryAppButton) {
    retryAppButton.addEventListener("click", () => {
      void refreshAll();
    });
  }

  orderForm.addEventListener("submit", submitOrder);
  void refreshAll();
}

bootstrap();
