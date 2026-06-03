import { Product, Customer, Order, OrderItem } from '../types/models';

export function validateProduct(p: Partial<Product>): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  if (!p.id) errors.push('id es obligatorio');
  if (!p.name) errors.push('name es obligatorio');
  if (typeof p.price !== 'number' || isNaN(p.price)) errors.push('price debe ser número');
  else if (p.price < 0) errors.push('price no puede ser negativo');
  if (typeof p.stock !== 'number' || isNaN(p.stock)) errors.push('stock debe ser número');
  else if (p.stock < 0) errors.push('stock no puede ser negativo');
  if (!p.category) errors.push('category es obligatorio');
  return { valid: errors.length === 0, errors };
}

export function validateCustomer(c: Partial<Customer>): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  if (!c.id) errors.push('id es obligatorio');
  if (!c.name) errors.push('name es obligatorio');
  if (!c.email) errors.push('email es obligatorio');
  else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(c.email)) errors.push('email inválido');
  if (typeof c.loyaltyPoints !== 'number' || isNaN(c.loyaltyPoints)) errors.push('loyaltyPoints debe ser número');
  else if (c.loyaltyPoints < 0) errors.push('loyaltyPoints no puede ser negativo');
  return { valid: errors.length === 0, errors };
}

function sumOrderItems(items: OrderItem[]): number {
  return items.reduce((s, it) => s + it.unitPrice * it.quantity, 0);
}

export function validateOrder(o: Partial<Order>): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  if (!o.id) errors.push('id es obligatorio');
  if (!o.customerId) errors.push('customerId es obligatorio');
  if (!o.items || !Array.isArray(o.items) || o.items.length === 0) errors.push('items debe tener al menos un elemento');
  else {
    for (const [i, it] of (o.items || []).entries()) {
      if (!it.productId) errors.push(`items[${i}].productId es obligatorio`);
      if (typeof it.quantity !== 'number' || it.quantity <= 0) errors.push(`items[${i}].quantity debe ser > 0`);
      if (typeof it.unitPrice !== 'number' || it.unitPrice < 0) errors.push(`items[${i}].unitPrice inválido`);
    }
  }
  if (typeof o.total !== 'number' || isNaN(o.total)) errors.push('total debe ser número');
  else if (o.items && Array.isArray(o.items)) {
    const sum = sumOrderItems(o.items as OrderItem[]);
    if (Math.abs(sum - (o.total as number)) > 0.01) errors.push('total no coincide con la suma de los items');
  }
  if (!o.status) errors.push('status es obligatorio');
  return { valid: errors.length === 0, errors };
}
