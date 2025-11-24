import apiClient from './client';
import { Product, ProductDetail, ProductListResponse } from '@/types/api';

export const productsAPI = {
  // Get all products
  getProducts: async (params?: {
    page?: number;
    search?: string;
    category?: string;
    ordering?: string;
  }): Promise<ProductListResponse> => {
    const response = await apiClient.get<ProductListResponse>('/api/products/products/', {
      params,
    });
    return response.data;
  },

  // Get single product by slug
  getProduct: async (slug: string): Promise<ProductDetail> => {
    const response = await apiClient.get<ProductDetail>(`/api/products/products/${slug}/`);
    return response.data;
  },

  // Get featured products
  getFeaturedProducts: async (): Promise<Product[]> => {
    const response = await apiClient.get<Product[]>('/api/products/products/featured/');
    return response.data;
  },

  // Search products
  searchProducts: async (query: string): Promise<{ results: Product[] }> => {
    const response = await apiClient.get('/api/products/products/search/', {
      params: { q: query },
    });
    return response.data;
  },
};
