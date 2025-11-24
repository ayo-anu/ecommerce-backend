import apiClient, { setTokens, clearTokens } from './client';
import { AuthResponse, LoginData, RegisterData, User } from '@/types/api';

export const authAPI = {
  // Register new user
  register: async (data: RegisterData): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/auth/register/', data);
    setTokens({ access: response.data.access, refresh: response.data.refresh });
    return response.data;
  },

  // Login
  login: async (data: LoginData): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/auth/login/', data);
    setTokens({ access: response.data.access, refresh: response.data.refresh });
    return response.data;
  },

  // Logout
  logout: async (): Promise<void> => {
    clearTokens();
  },

  // Get current user
  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/auth/me/');
    return response.data;
  },

  // Request password reset
  requestPasswordReset: async (email: string): Promise<void> => {
    await apiClient.post('/api/auth/password-reset/', { email });
  },

  // Confirm password reset
  confirmPasswordReset: async (token: string, newPassword: string): Promise<void> => {
    await apiClient.post('/api/auth/password-reset/confirm/', {
      token,
      new_password: newPassword,
      new_password2: newPassword,
    });
  },
};
