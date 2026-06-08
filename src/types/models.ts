export interface SaleRecord {
  id: string;
  storeId: string;
  amount: number;
  timestamp: string;
  country: "CO" | "US";
  currency: "COP" | "USD";
}

export interface StoreSummary {
  storeId: string;
  totalSales: number;
  transactions: number;
}

export interface ValidationResult {
  ok: boolean;
  errors: string[];
}
