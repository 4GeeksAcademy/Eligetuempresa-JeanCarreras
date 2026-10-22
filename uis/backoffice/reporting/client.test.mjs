import test from "node:test";
import assert from "node:assert/strict";
import { reportingUrl, fetchReportingKpis } from "./client.mjs";

const filters = { startDate: "2026-10-05", endDate: "2026-10-11", country: "CO", storeId: " medellin-01 " };

test("reporting aplica pais, periodo y limite sin enviar credenciales en la URL", () => {
  const url = reportingUrl("http://localhost:8000", filters);
  assert.equal(url.pathname, "/api/v1/reporting/kpis");
  assert.equal(url.searchParams.get("country"), "CO");
  assert.equal(url.searchParams.get("start_date"), "2026-10-05");
  assert.equal(url.searchParams.get("end_date"), "2026-10-11");
  assert.equal(url.searchParams.get("limit"), "500");
  assert.equal(url.searchParams.get("store_id"), "medellin-01");
  assert.throws(() => reportingUrl("http://usuario:secreto@localhost", filters));
});

test("reporting omite el filtro de local cuando esta vacio", () => {
  const url = reportingUrl("http://localhost:8000", { ...filters, storeId: " " });
  assert.equal(url.searchParams.has("store_id"), false);
});

test("reporting rechaza fechas imposibles, periodos invertidos y paises invalidos", () => {
  for (const invalid of [
    { startDate: "2026-02-30" }, { startDate: "2026-11-01" },
    { endDate: "no-es-fecha" }, { country: "XX" },
  ]) assert.throws(() => reportingUrl("http://localhost:8000", { ...filters, ...invalid }));
});

test("reporting devuelve las filas reales y usa el token solo como encabezado", async () => {
  const rows = [{ metric_date: "2026-10-05", store_id: "medellin-01", country: "CO", valor: 15 }];
  const result = await fetchReportingKpis("http://localhost:8000", filters, {
    token: "token-de-prueba",
    fetchImpl: async (url, options) => {
      assert.equal(options.headers.Authorization, "Bearer token-de-prueba");
      assert.equal(url.toString().includes("token-de-prueba"), false);
      return { ok: true, json: async () => ({ rows, count: 1 }) };
    },
  });
  assert.deepEqual(result, { rows, possiblyTruncated: false });
});

test("reporting diferencia falta de permisos de una tabla vacia", async () => {
  await assert.rejects(fetchReportingKpis("http://localhost:8000", filters, {
    fetchImpl: async () => ({ ok: false, status: 403 }),
  }), /permisos/);
  const result = await fetchReportingKpis("http://localhost:8000", filters, {
    fetchImpl: async () => ({ ok: true, json: async () => ({ rows: [], count: 0 }) }),
  });
  assert.deepEqual(result.rows, []);
});

test("reporting rechaza respuestas malformadas sin presentarlas como ceros", async () => {
  for (const payload of [{}, { rows: [null], count: 1 }, { rows: [], count: 2 }]) {
    await assert.rejects(fetchReportingKpis("http://localhost:8000", filters, {
      fetchImpl: async () => ({ ok: true, json: async () => payload }),
    }), /formato inesperado/);
  }
});

test("reporting advierte cuando el limite del endpoint puede ocultar filas", async () => {
  const rows = Array.from({ length: 500 }, () => ({
    metric_date: "2026-10-05", store_id: "medellin-01", country: "CO", valor: 1,
  }));
  const result = await fetchReportingKpis("http://localhost:8000", filters, {
    fetchImpl: async () => ({ ok: true, json: async () => ({ rows, count: 500 }) }),
  });
  assert.equal(result.possiblyTruncated, true);
});