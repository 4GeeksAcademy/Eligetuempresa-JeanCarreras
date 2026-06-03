const products = [
  { id: 'p1', name: 'Arroz', category: 'Comida', price: 10, stock: 100 },
  { id: 'p2', name: 'Frijol', category: 'Comida', price: 8, stock: 50 },
  { id: 'p3', name: 'Coca', category: 'Bebida', price: 3, stock: 200 },
];

const output = document.getElementById('output');
const categorySelect = document.getElementById('categorySelect');
const searchInput = document.getElementById('searchId');

function renderResult(value) {
  output.textContent = JSON.stringify(value, null, 2);
}

function filterByProperty(arr, key, value) {
  return arr.filter((item) => item[key] === value);
}

function sortByField(arr, field, direction = 'asc') {
  return [...arr].sort((a, b) => {
    const valueA = a[field];
    const valueB = b[field];
    if (valueA === valueB) return 0;
    if (valueA === undefined) return 1;
    if (valueB === undefined) return -1;
    if (typeof valueA === 'number' && typeof valueB === 'number') {
      return direction === 'asc' ? valueA - valueB : valueB - valueA;
    }
    return direction === 'asc' ? String(valueA).localeCompare(String(valueB)) : String(valueB).localeCompare(String(valueA));
  });
}

function countBy(arr, keyFn) {
  return arr.reduce((acc, item) => {
    const key = keyFn(item);
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

function average(arr, valueFn) {
  if (arr.length === 0) return 0;
  return arr.reduce((sum, item) => sum + valueFn(item), 0) / arr.length;
}

function findMax(arr, valueFn) {
  if (arr.length === 0) return null;
  return arr.reduce((best, item) => (valueFn(item) > valueFn(best) ? item : best));
}

function findMin(arr, valueFn) {
  if (arr.length === 0) return null;
  return arr.reduce((best, item) => (valueFn(item) < valueFn(best) ? item : best));
}

function linearSearch(arr, predicate) {
  for (let i = 0; i < arr.length; i += 1) {
    if (predicate(arr[i])) return arr[i];
  }
  return null;
}

function binarySearch(arr, target, comparator) {
  let lo = 0;
  let hi = arr.length - 1;
  while (lo <= hi) {
    const mid = Math.floor((lo + hi) / 2);
    const cmp = comparator(arr[mid], target);
    if (cmp === 0) return arr[mid];
    if (cmp < 0) lo = mid + 1;
    else hi = mid - 1;
  }
  return null;
}

function populateCategories() {
  const categories = Array.from(new Set(products.map((product) => product.category)));
  categories.forEach((category) => {
    const option = document.createElement('option');
    option.value = category;
    option.textContent = category;
    categorySelect.appendChild(option);
  });
}

function initEvents() {
  document.getElementById('btnFilter').addEventListener('click', () => {
    const selected = categorySelect.value;
    const result = selected ? filterByProperty(products, 'category', selected) : products;
    renderResult(result);
  });

  document.getElementById('btnSearch').addEventListener('click', () => {
    const targetId = searchInput.value.trim();
    const result = linearSearch(products, (item) => item.id === targetId);
    renderResult(result || { message: 'Producto no encontrado' });
  });

  document.getElementById('btnSortAsc').addEventListener('click', () => {
    renderResult(sortByField(products, 'price', 'asc'));
  });

  document.getElementById('btnSortDesc').addEventListener('click', () => {
    renderResult(sortByField(products, 'price', 'desc'));
  });

  document.getElementById('btnCount').addEventListener('click', () => {
    renderResult(countBy(products, (product) => product.category));
  });

  document.getElementById('btnAverage').addEventListener('click', () => {
    renderResult({ averagePrice: average(products, (product) => product.price) });
  });

  document.getElementById('btnMaxMin').addEventListener('click', () => {
    renderResult({ maxProduct: findMax(products, (product) => product.price), minProduct: findMin(products, (product) => product.price) });
  });

  document.getElementById('btnValidate').addEventListener('click', () => {
    const validations = products.map((product) => ({ id: product.id, valid: product.id && product.name && product.category && product.price >= 0 && product.stock >= 0 }));
    renderResult(validations);
  });
}

populateCategories();
initEvents();
renderResult(products);
