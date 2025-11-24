import apiClient from './client';
import { Cart, AddToCartData } from '@/types/api';

export const cartAPI = {
  // Get current user's cart
  getCart: async (): Promise<Cart> => {
    const response = await apiClient.get<Cart>('/api/orders/cart/');
    return response.data;
  },

  // Add item to cart
  addToCart: async (data: AddToCartData): Promise<Cart> => {
    const response = await apiClient.post<Cart>('/api/orders/cart/add_item/', data);
    return response.data;
  },

  // Update cart item quantity
  updateCartItem: async (itemId: string, quantity: number): Promise<Cart> => {
    const response = await apiClient.patch<Cart>(`/api/orders/cart/update_item/${itemId}/`, {
      quantity,
    });
    return response.data;
  },

  // Remove item from cart
  removeFromCart: async (itemId: string): Promise<Cart> => {
    const response = await apiClient.delete<Cart>(`/api/orders/cart/remove_item/${itemId}/`);
    return response.data;
  },

  // Clear entire cart
  clearCart: async (): Promise<void> => {
    await apiClient.post('/api/orders/cart/clear/');
  },
};
