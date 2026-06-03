import { describe, it, expect } from 'vitest';
import { groupBy, uniqueBy, paginate } from '../collections';

describe('collections utilities', () => {
  const arr = [
    { id: 'a', cat: 'x' },
    { id: 'b', cat: 'x' },
    { id: 'c', cat: 'y' },
  ];

  it('groupBy groups items by key', () => {
    const g = groupBy(arr, (i) => i.cat);
    expect(Object.keys(g)).toHaveLength(2);
    expect(g['x']).toHaveLength(2);
  });

  it('uniqueBy returns unique items by key', () => {
    const u = uniqueBy(arr.concat([{ id: 'a', cat: 'x' }]), (i) => i.id);
    expect(u).toHaveLength(3);
  });

  it('paginate slices arrays', () => {
    const pages = paginate([1, 2, 3, 4, 5], 2, 2);
    expect(pages).toEqual([3, 4]);
  });
});
