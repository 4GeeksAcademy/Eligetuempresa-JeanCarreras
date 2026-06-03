import { Product, Customer, Order } from './types/models';
import { linearSearch, binarySearch, Comparator } from './utils/search';
import { filterBy, sortBy, groupBy } from './utils/collections';
import { countBy, sumValues, average, salesByProduct } from './utils/transformations';
import { validateProduct, validateCustomer, validateOrder } from './utils/validations';

const products: Product[] = [
  { id: 'p1', name: 'Arroz', category: 'Comida', price: 10, stock: 100, createdAt: new Date().toISOString() },
  { id: 'p2', name: 'Frijol', category: 'Comida', price: 8, stock: 50, createdAt: new Date().toISOString() },
  { id: 'p3', name: 'Coca', category: 'Bebida', price: 3, stock: 200, createdAt: new Date().toISOString() },
];

const customers: Customer[] = [
  { id: 'c1', name: 'Ana', email: 'ana@example.com', loyaltyPoints: 10, createdAt: new Date().toISOString() },
];

const orders: Order[] = [
  {
    id: 'o1',
    customerId: 'c1',
    items: [{ productId: 'p1', quantity: 2, unitPrice: 10 }],
    total: 20,
    status: 'paid',
    createdAt: new Date().toISOString(),
  },
];

console.log('countBy category:', countBy(products, p => p.category));
console.log('total inventory value:', sumValues(products, p => p.price * p.stock));
console.log('salesByProduct:', salesByProduct(orders));

// validations
console.log('valid product:', validateProduct(products[0]));
console.log('valid customer:', validateCustomer(customers[0]));
console.log('valid order:', validateOrder(orders[0]));

// searches
const cmpById: Comparator<Product> = (a, b) => a.id.localeCompare(b.id);
const sorted = sortBy(products, cmpById);
console.log('binary search p2 index:', binarySearch(sorted, { id: 'p2', name: '', category: '', price: 0, stock: 0, createdAt: '' }, cmpById));
