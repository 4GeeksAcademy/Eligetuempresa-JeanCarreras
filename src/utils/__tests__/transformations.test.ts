import { describe, it, expect } from 'vitest';
import { countBy, sumValues, average, salesByProduct } from '../transformations';
import { Order } from '../../types/models';

describe('transformations utilities', () => {
  const products = [
    { id: 'p1', category: 'A' },
    { id: 'p2', category: 'A' },
    { id: 'p3', category: 'B' },
  ];

  it('countBy counts correctly', () => {
    const c = countBy(products, (p: any) => p.category);
    expect(c['A']).toBe(2);
    expect(c['B']).toBe(1);
  });

  it('sumValues and average work', () => {
    const arr = [{ v: 2 }, { v: 4 }];
    expect(sumValues(arr as any, (x: any) => x.v)).toBe(6);
    expect(average(arr as any, (x: any) => x.v)).toBe(3);
  });

  it('salesByProduct aggregates orders', () => {
    const orders: Order[] = [
      { id: 'o1', customerId: 'c1', items: [{ productId: 'p1', quantity: 2, unitPrice: 5 }], total: 10, status: 'paid', createdAt: '' },
    ];
    const s = salesByProduct(orders);
    expect(s['p1']).toBe(10);
  });
});
