import { Product, Order, OrderItem } from '../types/models';

export function countBy<T, K extends string | number>(arr: T[], keyFn: (item: T) => K): Record<K, number> {
  return arr.reduce((acc: Record<any, number>, item) => {
    const k = keyFn(item) as any;
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {} as Record<K, number>);
}

export function sumValues<T>(arr: T[], valueFn: (item: T) => number): number {
  return arr.reduce((s, it) => s + valueFn(it), 0);
}

export function average<T>(arr: T[], valueFn: (item: T) => number): number {
  if (arr.length === 0) return 0;
  return sumValues(arr, valueFn) / arr.length;
}

export function findMax<T>(arr: T[], valueFn: (item: T) => number): T | null {
  if (arr.length === 0) return null;
  return arr.reduce((best, cur) => (valueFn(cur) > valueFn(best) ? cur : best));
}

export function findMin<T>(arr: T[], valueFn: (item: T) => number): T | null {
  if (arr.length === 0) return null;
  return arr.reduce((best, cur) => (valueFn(cur) < valueFn(best) ? cur : best));
}

// Report: sales by product id given orders
export function salesByProduct(orders: Order[]): Record<string, number> {
  const totals: Record<string, number> = {};
  for (const order of orders) {
    for (const item of order.items) {
      totals[item.productId] = (totals[item.productId] || 0) + item.unitPrice * item.quantity;
    }
  }
  return totals;
}

// Report: inventory value by product list
export function inventoryValueByProduct(products: Product[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const p of products) {
    out[p.id] = p.price * p.stock;
  }
  return out;
}
