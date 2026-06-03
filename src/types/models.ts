export interface Product {
  id: string;
  name: string;
  category: string;
  price: number;
  stock: number;
  createdAt: string; // ISO date
}

export interface Customer {
  id: string;
  name: string;
  email: string;
  loyaltyPoints: number;
  createdAt: string;
}

export interface Location {
  id: string;
  name: string;
  country: string;
  currency: 'COP' | 'USD';
  isOpen: boolean;
  createdAt: string;
}

export interface Supplier {
  id: string;
  name: string;
  category: string;
  country: string;
  active: boolean;
  createdAt: string;
}

export interface MenuItem {
  id: string;
  name: string;
  category: string;
  price: number;
  available: boolean;
  createdAt: string;
}

export interface InventoryItem {
  id: string;
  productId: string;
  quantity: number;
  unitCost: number;
  locationId: string;
}

export type OrderStatus = 'pending' | 'paid' | 'shipped' | 'cancelled';

export interface OrderItem {
  productId: string;
  quantity: number;
  unitPrice: number;
}

export interface Order {
  id: string;
  customerId: string;
  items: OrderItem[];
  total: number;
  status: OrderStatus;
  createdAt: string;
}
