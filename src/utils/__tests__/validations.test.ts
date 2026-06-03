import { describe, it, expect } from 'vitest';
import { validateProduct, validateOrder } from '../validations';

describe('validations', () => {
  it('validateProduct detects missing fields', () => {
    const res = validateProduct({} as any);
    expect(res.valid).toBe(false);
    expect(res.errors.length).toBeGreaterThan(0);
  });

  it('validateOrder detects total mismatch', () => {
    const res = validateOrder({ id: 'o1', customerId: 'c1', items: [{ productId: 'p1', quantity: 1, unitPrice: 5 }], total: 6, status: 'paid' } as any);
    expect(res.valid).toBe(false);
    expect(res.errors).toContain('total no coincide con la suma de los items');
  });
});
