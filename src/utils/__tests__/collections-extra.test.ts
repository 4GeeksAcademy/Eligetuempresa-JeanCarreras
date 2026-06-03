import { describe, it, expect } from 'vitest';
import { filterByProperty, filterByRange, sortByField, sortByMultiple } from '../collections';

describe('collections explicit helpers', () => {
  const arr = [
    { id: 'a', category: 'x', price: 10, rank: 1 },
    { id: 'b', category: 'x', price: 20, rank: 1 },
    { id: 'c', category: 'y', price: 5, rank: 2 },
  ];

  it('filterByProperty filters by property value', () => {
    expect(filterByProperty(arr, 'category', 'x')).toHaveLength(2);
  });

  it('filterByRange filters by numeric range', () => {
    expect(filterByRange(arr, 'price', 6, 20)).toHaveLength(2);
  });

  it('sortByField sorts ascending and descending', () => {
    const asc = sortByField(arr, 'price', 'asc');
    expect(asc[0].price).toBe(5);
    const desc = sortByField(arr, 'price', 'desc');
    expect(desc[0].price).toBe(20);
  });

  it('sortByMultiple sorts by multiple criteria', () => {
    const sorted = sortByMultiple(arr, [
      (a, b) => a.rank - b.rank,
      (a, b) => a.price - b.price,
    ]);
    expect(sorted[0].id).toBe('a');
  });
});
