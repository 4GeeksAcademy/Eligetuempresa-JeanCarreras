export function reportingUrl(apiBase, { startDate, endDate, country = "", storeId = "" }) {
  const base = new URL(apiBase);
  if (!["http:", "https:"].includes(base.protocol) || base.username || base.password) {
    throw new Error("La direccion del servicio no es valida.");
  }
  const validDate = (value) => /^\d{4}-\d{2}-\d{2}$/.test(value)
    && !Number.isNaN(Date.parse(value))
    && new Date(value).toISOString().slice(0, 10) === value;
  if (!validDate(startDate) || !validDate(endDate) || startDate > endDate) {
    throw new Error("Selecciona un periodo valido: la fecha inicial no puede superar la final.");
  }
  if (!["", "CO", "US"].includes(country)) {
    throw new Error("Selecciona Colombia, Estados Unidos o todos los paises.");
  }
  const url = new URL("/api/v1/reporting/kpis", base);
  url.search = new URLSearchParams({ start_date: startDate, end_date: endDate, limit: "500" });
  if (country) url.searchParams.set("country", country);
  if (storeId.trim()) url.searchParams.set("store_id", storeId.trim());
  return url;
}

export async function fetchReportingKpis(apiBase, filters, { token, signal, fetchImpl = fetch } = {}) {
  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetchImpl(reportingUrl(apiBase, filters), {
    headers, signal, cache: "no-store", credentials: "same-origin",
  });
  if (!response.ok) {
    const messages = {
      401: "Inicia sesion para consultar el informe.",
      403: "Tu cuenta no tiene permisos de direccion o finanzas.",
      404: "El servicio de informes no esta disponible en esta version de la API.",
    };
    throw new Error(messages[response.status] || "No se pudo consultar el informe. Intenta de nuevo.");
  }
  const result = await response.json();
  if (!result || !Array.isArray(result.rows) || !Number.isInteger(result.count)
      || result.count !== result.rows.length || result.rows.some((row) => !row
        || typeof row !== "object" || Array.isArray(row)
        || typeof row.metric_date !== "string" || typeof row.store_id !== "string"
        || !["CO", "US"].includes(row.country))) {
    throw new Error("El servicio devolvio un informe con formato inesperado.");
  }
  return { rows: result.rows, possiblyTruncated: result.count === 500 };
}