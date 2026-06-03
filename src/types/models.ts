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
