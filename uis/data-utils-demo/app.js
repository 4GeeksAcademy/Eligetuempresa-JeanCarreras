// Demo app logic (plain JS) to showcase utilities
const products = [
  { id: 'p1', name: 'Arroz', category: 'Comida', price: 10, stock: 100 },
  { id: 'p2', name: 'Frijol', category: 'Comida', price: 8, stock: 50 },
  { id: 'p3', name: 'Coca', category: 'Bebida', price: 3, stock: 200 },
];

const customers = [
  { id: 'c1', name: 'Ana', email: 'ana@example.com', loyaltyPoints: 10 },
];

const orders = [
  { id: 'o1', customerId: 'c1', items: [{ productId: 'p1', quantity: 2, unitPrice: 10 }], total: 20, status: 'paid' },
];

function countBy(arr, keyFn) {
  return arr.reduce((acc, it) => {
    const k = keyFn(it);
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {});
}

function sumValues(arr, valueFn) {
  return arr.reduce((s, it) => s + valueFn(it), 0);
}

function salesByProduct(orders) {
  const totals = {};
  for (const o of orders) {
    for (const it of o.items) {
      totals[it.productId] = (totals[it.productId] || 0) + it.unitPrice * it.quantity;
    }
  }
  return totals;
}

function validateProduct(p) {
  const errors = [];
  if (!p.id) errors.push('id es obligatorio');
  if (!p.name) errors.push('name es obligatorio');
  if (typeof p.price !== 'number' || isNaN(p.price)) errors.push('price debe ser número');
  else if (p.price < 0) errors.push('price no puede ser negativo');
  if (typeof p.stock !== 'number' || isNaN(p.stock)) errors.push('stock debe ser número');
  else if (p.stock < 0) errors.push('stock no puede ser negativo');
  if (!p.category) errors.push('category es obligatorio');
  return { valid: errors.length === 0, errors };
}

// UI
const out = document.getElementById('output');
const sel = document.getElementById('category');

function renderOutput(obj) {
  out.textContent = JSON.stringify(obj, null, 2);
}

function populateCategories() {
  const cats = Array.from(new Set(products.map(p => p.category)));
  for (const c of cats) {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    sel.appendChild(opt);
  }
}

document.getElementById('btn-count').addEventListener('click', () => {
  const filtered = sel.value ? products.filter(p => p.category === sel.value) : products;
  renderOutput(countBy(filtered, p => p.category));
});

document.getElementById('btn-inv').addEventListener('click', () => {
  const filtered = sel.value ? products.filter(p => p.category === sel.value) : products;
  renderOutput({ totalInventoryValue: sumValues(filtered, p => p.price * p.stock) });
});

document.getElementById('btn-sales').addEventListener('click', () => {
  renderOutput(salesByProduct(orders));
});

document.getElementById('btn-validate').addEventListener('click', () => {
  renderOutput({ products: products.map(p => ({ id: p.id, validation: validateProduct(p) })) });
});

populateCategories();
renderOutput({ products, customers, orders });
