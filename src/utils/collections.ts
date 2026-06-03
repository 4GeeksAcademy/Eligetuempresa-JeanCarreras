import { Comparator } from './search';

export function filterBy<T>(arr: T[], predicate: (item: T) => boolean): T[] {
  return arr.filter(predicate);
}

export function sortBy<T>(arr: T[], comparator: Comparator<T>): T[] {
  return [...arr].sort(comparator);
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
