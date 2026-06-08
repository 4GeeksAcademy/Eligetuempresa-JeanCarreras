import { SaleRecord, StoreSummary } from "../types/models";
import { groupBy, sumBy } from "./collections";

export function summarizeByStore(sales: SaleRecord[]): StoreSummary[] {
  const grouped = groupBy(sales, (sale) => sale.storeId);

  return Object.entries(grouped).map(([storeId, records]) => ({
    storeId,
    totalSales: sumBy(records, (record) => record.amount),
    transactions: records.length,
  }));
}
