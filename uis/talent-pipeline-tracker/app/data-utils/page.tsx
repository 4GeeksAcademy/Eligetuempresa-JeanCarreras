"use client";

import { useState } from "react";
import type { SaleRecord } from "../../../../src/types/models";
import { groupBy } from "../../../../src/utils/collections";
import { linearSearch } from "../../../../src/utils/search";
import { summarizeByStore } from "../../../../src/utils/transformations";
import { validateSaleRecord } from "../../../../src/utils/validations";

const sample: SaleRecord[] = [
  { id: "demo-co", storeId: "CO-DEMO", amount: 100000, timestamp: "2026-11-01T12:00:00Z", country: "CO", currency: "COP" },
  { id: "demo-us", storeId: "US-DEMO", amount: 30, timestamp: "2026-11-01T17:00:00Z", country: "US", currency: "USD" },
];

export default function DataUtilsPage() {
  const [source, setSource] = useState(JSON.stringify(sample, null, 2));
  const [searchId, setSearchId] = useState("");
  const [output, setOutput] = useState("");
  const [error, setError] = useState("");

  function processSales(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setOutput("");
    try {
      const parsed: unknown = JSON.parse(source);
      if (!Array.isArray(parsed) || parsed.length > 10000) throw new Error("Introduce un arreglo de hasta 10000 ventas.");
      const records: SaleRecord[] = parsed.map((record: unknown) => {
        if (!record || typeof record !== "object") throw new Error("Registro de venta no valido.");
        const sale = record as SaleRecord;
        if (typeof sale.id !== "string" || typeof sale.storeId !== "string" || typeof sale.timestamp !== "string"
          || typeof sale.amount !== "number" || !Number.isFinite(sale.amount)
          || !["CO", "US"].includes(sale.country) || !["COP", "USD"].includes(sale.currency)) {
          throw new Error("Cada venta requiere id, storeId, timestamp, amount, country y currency validos.");
        }
        return sale;
      });
      const validations = records.map((record) => ({ id: record.id, ...validateSaleRecord(record) }));
      if (validations.some((result) => !result.ok)) {
        setOutput(JSON.stringify({ validations }, null, 2));
        return;
      }
      const grouped = groupBy(records, (record) => `${record.country}:${record.currency}`);
      const summaries = Object.entries(grouped).flatMap(([market, sales]) => summarizeByStore(sales).map((summary) => ({ market, ...summary })));
      setOutput(JSON.stringify({ validations, summaries, found: searchId ? linearSearch(records, (record) => record.id === searchId) : null }, null, 2));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Datos no validos.");
    }
  }

  return (
    <main className="auth-page" style={{ alignItems: "flex-start" }}>
      <form className="auth-form" style={{ width: "100%", maxWidth: 960 }} onSubmit={processSales}>
        <h1>Utilidades de datos</h1>
        <label>Ventas de prueba (JSON)
          <textarea aria-label="Ventas de prueba (JSON)" value={source} onChange={(event) => setSource(event.target.value)} rows={14} style={{ width: "100%", resize: "vertical", padding: 12, border: "1px solid var(--line)", borderRadius: 4 }} />
        </label>
        <label>ID de venta<input value={searchId} onChange={(event) => setSearchId(event.target.value)} /></label>
        <button type="submit">Procesar ventas</button>
        {error ? <p role="alert">{error}</p> : null}
        {output ? <pre aria-label="Resultado" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: 480, overflow: "auto" }}>{output}</pre> : null}
      </form>
    </main>
  );
}