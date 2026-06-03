import { describe, it, expect } from 'vitest';
import { linearSearch, binarySearch, Comparator } from '../search';

describe('search utilities', () => {
  const arr = [1, 3, 5, 7, 9];
  it('linearSearch finds existing', () => {
    const found = linearSearch(arr, (x) => x === 5);
    expect(found).toBe(5);
  });

  it('linearSearch returns null when not found', () => {
    const found = linearSearch(arr, (x) => x === 2);
    expect(found).toBeNull();
  });

  it('binarySearch finds existing in sorted array', () => {
    const cmp: Comparator<number> = (a, b) => a - b;
    const found = binarySearch(arr, 7, cmp);
    expect(found).toBe(7);
  });
});
