/**
 * Búsquedas: lineal y binaria genéricas
 */

export function linearSearchIndex<T>(arr: T[], predicate: (item: T) => boolean): number {
  for (let i = 0; i < arr.length; i++) {
    if (predicate(arr[i])) return i;
  }
  return -1;
}

export function linearSearch<T>(arr: T[], predicate: (item: T) => boolean): T | null {
  const idx = linearSearchIndex(arr, predicate);
  return idx === -1 ? null : arr[idx];
}

export type Comparator<T> = (a: T, b: T) => number;

/**
 * Binary search assumes `arr` is sorted according to the comparator.
 * Returns index of found element or -1 if not found.
 */
export function binarySearchIndex<T>(arr: T[], target: T, comparator: Comparator<T>): number {
  let lo = 0;
  let hi = arr.length - 1;
  while (lo <= hi) {
    const mid = Math.floor((lo + hi) / 2);
    const cmp = comparator(arr[mid], target);
    if (cmp === 0) return mid;
    if (cmp < 0) lo = mid + 1;
    else hi = mid - 1;
  }
  return -1;
}

export function binarySearch<T>(arr: T[], target: T, comparator: Comparator<T>): T | null {
  const idx = binarySearchIndex(arr, target, comparator);
  return idx === -1 ? null : arr[idx];
}
