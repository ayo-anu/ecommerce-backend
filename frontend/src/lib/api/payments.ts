import apiClient from './client';
import {
  Payment,
  CreatePaymentIntentData,
  PaymentIntentResponse,
} from '@/types/api';

export const paymentsAPI = {
  // Get all user payments
  getPayments: async (): Promise<Payment[]> => {
    const response = await apiClient.get<Payment[]>('/api/payments/payments/');
    return response.data;
  },

  // Get single payment
  getPayment: async (paymentId: string): Promise<Payment> => {
    const response = await apiClient.get<Payment>(`/api/payments/payments/${paymentId}/`);
    return response.data;
  },

  // Create payment intent
  createPaymentIntent: async (data: CreatePaymentIntentData): Promise<PaymentIntentResponse> => {
    const response = await apiClient.post<PaymentIntentResponse>(
      '/api/payments/create-payment-intent/',
      data
    );
    return response.data;
  },

  // Confirm payment
  confirmPayment: async (paymentIntentId: string): Promise<Payment> => {
    const response = await apiClient.post<Payment>('/api/payments/confirm-payment/', {
      payment_intent_id: paymentIntentId,
    });
    return response.data;
  },

  // Request refund
  requestRefund: async (data: {
    payment_id: string;
    amount?: string;
    reason: string;
    description?: string;
  }): Promise<void> => {
    await apiClient.post('/api/payments/request-refund/', data);
  },
};
