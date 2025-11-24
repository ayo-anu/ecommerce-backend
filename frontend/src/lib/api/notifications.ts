import apiClient from './client';

export interface Notification {
  id: string;
  notification_type: 'order' | 'payment' | 'shipping' | 'promotion' | 'system';
  title: string;
  message: string;
  link?: string;
  is_read: boolean;
  read_at?: string;
  created_at: string;
}

export const notificationsAPI = {
  // Get all notifications
  getNotifications: async (): Promise<Notification[]> => {
    const response = await apiClient.get<Notification[]>('/api/notifications/notifications/');
    return response.data;
  },

  // Get unread count
  getUnreadCount: async (): Promise<number> => {
    const response = await apiClient.get<{ unread_count: number }>(
      '/api/notifications/notifications/unread_count/'
    );
    return response.data.unread_count;
  },

  // Mark notification as read
  markAsRead: async (notificationId: string): Promise<Notification> => {
    const response = await apiClient.post<Notification>(
      `/api/notifications/notifications/${notificationId}/mark_read/`
    );
    return response.data;
  },

  // Mark all as read
  markAllAsRead: async (): Promise<void> => {
    await apiClient.post('/api/notifications/notifications/mark_all_read/');
  },

  // Delete notification
  deleteNotification: async (notificationId: string): Promise<void> => {
    await apiClient.delete(`/api/notifications/notifications/${notificationId}/`);
  },
};
