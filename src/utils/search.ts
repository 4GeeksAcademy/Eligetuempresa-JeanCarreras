export function linearSearch<T>(items: T[], predicate: (item: T) => boolean): T | null {
  for (const item of items) {
    if (predicate(item)) {
      return item;
    }
  }
  return null;
}

export function binarySearch(sortedNumbers: number[], target: number): number {
  let left = 0;
  let right = sortedNumbers.length - 1;

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const value = sortedNumbers[mid];

    if (value === target) {
      return mid;
    }

    if (value < target) {
      left = mid + 1;
    } else {
      right = mid - 1;
    }
  }

  return -1;
}
