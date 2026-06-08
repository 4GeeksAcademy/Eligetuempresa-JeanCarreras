import { SaleRecord, ValidationResult } from "../types/models";

export function validateSaleRecord(record: SaleRecord): ValidationResult {
  const errors: string[] = [];

  if (!record.id) {
    errors.push("id is required");
  }

  if (!record.storeId) {
    errors.push("storeId is required");
  }

  if (record.amount < 0) {
    errors.push("amount cannot be negative");
  }

  if (!record.timestamp || Number.isNaN(Date.parse(record.timestamp))) {
    errors.push("timestamp must be a valid ISO date");
  }

  return {
    ok: errors.length === 0,
    errors,
  };
}
