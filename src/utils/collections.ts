import { Comparator } from './search';

export function filterBy<T>(arr: T[], predicate: (item: T) => boolean): T[] {
  return arr.filter(predicate);
}

export function filterByProperty<T, K extends keyof T>(arr: T[], key: K, value: T[K]): T[] {
  return arr.filter((item) => item[key] === value);
}

export function filterByRange<T>(arr: T[], key: keyof T, min: number, max: number): T[] {
  return arr.filter((item) => {
    const value = item[key];
    return typeof value === 'number' && value >= min && value <= max;
  });
}

export function sortBy<T>(arr: T[], comparator: Comparator<T>): T[] {
  return [...arr].sort(comparator);
}

export function sortByField<T, K extends keyof T>(arr: T[], field: K, direction: 'asc' | 'desc' = 'asc'): T[] {
  return sortBy(arr, (a, b) => {
    const valueA = a[field];
    const valueB = b[field];
    if (valueA === valueB) return 0;
    if (valueA === undefined) return 1;
    if (valueB === undefined) return -1;
    if (typeof valueA === 'number' && typeof valueB === 'number') {
      return direction === 'asc' ? (valueA - valueB) : (valueB - valueA);
    }
    const aStr = String(valueA);
    const bStr = String(valueB);
    return direction === 'asc' ? (aStr > bStr ? 1 : -1) : (aStr < bStr ? 1 : -1);
  });
}

export function sortByMultiple<T>(arr: T[], comparators: Comparator<T>[]): T[] {
  return [...arr].sort((a, b) => {
    for (const comparator of comparators) {
      const result = comparator(a, b);
      if (result !== 0) return result;
    }
    return 0;
  });
}

export function groupBy<T, K extends string | number>(arr: T[], keyFn: (item: T) => K): Record<K, T[]> {
  return arr.reduce((acc: Record<any, T[]>, item) => {
    const k = keyFn(item) as any;
    if (!acc[k]) acc[k] = [];
    acc[k].push(item);
    return acc;
  }, {} as Record<K, T[]>);
}

export function uniqueBy<T, K extends string | number>(arr: T[], keyFn: (item: T) => K): T[] {
  const seen = new Set<K>();
  const out: T[] = [];
  for (const item of arr) {
    const k = keyFn(item);
    if (!seen.has(k)) {
      seen.add(k);
      out.push(item);
    }
  }
  return out;
}

export function paginate<T>(arr: T[], page = 1, pageSize = 10): T[] {
  if (page < 1) page = 1;
  const start = (page - 1) * pageSize;
  return arr.slice(start, start + pageSize);
}
