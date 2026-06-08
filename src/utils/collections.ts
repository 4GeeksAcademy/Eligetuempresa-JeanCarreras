export function groupBy<T, K extends string | number>(
  items: T[],
  keySelector: (item: T) => K
): Record<K, T[]> {
  return items.reduce((acc, item) => {
    const key = keySelector(item);
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(item);
    return acc;
  }, {} as Record<K, T[]>);
}

export function sumBy<T>(items: T[], selector: (item: T) => number): number {
  return items.reduce((sum, item) => sum + selector(item), 0);
}
