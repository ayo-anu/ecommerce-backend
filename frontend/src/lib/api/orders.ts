import apiClient from './client';
import { Order, OrderDetail, CreateOrderData } from '@/types/api';

export const ordersAPI = {
  // Get all user orders
  getOrders: async (): Promise<Order[]> => {
    const response = await apiClient.get<Order[]>('/api/orders/orders/');
    return response.data;
  },

  // Get single order
  getOrder: async (orderId: string): Promise<OrderDetail> => {
    const response = await apiClient.get<OrderDetail>(`/api/orders/orders/${orderId}/`);
    return response.data;
  },

  // Create new order
  createOrder: async (data: CreateOrderData): Promise<OrderDetail> => {
    const response = await apiClient.post<OrderDetail>('/api/orders/orders/', data);
    return response.data;
  },

  // Cancel order
  cancelOrder: async (orderId: string): Promise<OrderDetail> => {
    const response = await apiClient.post<OrderDetail>(
      `/api/orders/orders/${orderId}/cancel/`
    );
    return response.data;
  },
};
