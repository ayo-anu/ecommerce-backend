// User & Authentication Types
export interface User {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  phone?: string;
  date_of_birth?: string;
  avatar?: string;
  bio?: string;
  email_verified: boolean;
  profile: UserProfile;
  created_at: string;
  last_login?: string;
}

export interface UserProfile {
  newsletter_subscribed: boolean;
  sms_notifications: boolean;
  preferred_language: string;
  preferred_currency: string;
  total_orders: number;
  total_spent: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  password2: string;
  first_name: string;
  last_name: string;
  phone?: string;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface TokenRefreshResponse {
  access: string;
}

// Product Types
export interface ProductImage {
  id: string;
  image: string;
  alt_text: string;
  is_primary: boolean;
  position: number;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  parent?: string;
}

export interface ProductVariant {
  id: string;
  name: string;
  sku: string;
  price: string;
  stock_quantity: number;
  is_active: boolean;
  attributes: Record<string, any>;
}

export interface Product {
  id: string;
  name: string;
  slug: string;
  description: string;
  price: string;
  compare_at_price?: string;
  is_on_sale: boolean;
  discount_percentage?: number;
  stock_quantity: number;
  is_low_stock: boolean;
  category_name: string;
  primary_image?: string;
  sku: string;
  track_inventory: boolean;
  is_active: boolean;
  is_featured: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductDetail extends Product {
  images: ProductImage[];
  category: Category;
  variants: ProductVariant[];
  tags: string[];
  meta_title?: string;
  meta_description?: string;
}

export interface ProductListResponse {
  count: number;
  next?: string;
  previous?: string;
  results: Product[];
}

// Cart Types
export interface CartItem {
  id: string;
  product: string;
  variant?: string;
  quantity: number;
  product_name: string;
  product_price: string;
  product_image?: string;
  subtotal: string;
}

export interface Cart {
  id: string;
  items: CartItem[];
  total: string;
  updated_at: string;
}

export interface AddToCartData {
  product_id: string;
  variant_id?: string;
  quantity: number;
}

// Order Types
export interface ShippingAddress {
  full_name: string;
  email: string;
  phone: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
}

export interface OrderItem {
  id: string;
  product: string;
  variant?: string;
  product_name: string;
  variant_name?: string;
  quantity: number;
  unit_price: string;
  total_price: string;
}

export interface Order {
  id: string;
  order_number: string;
  status: 'pending' | 'processing' | 'shipped' | 'delivered' | 'cancelled';
  payment_status: 'pending' | 'paid' | 'failed' | 'refunded';
  total: string;
  items_count: number;
  created_at: string;
}

export interface OrderDetail extends Order {
  items: OrderItem[];
  subtotal: string;
  tax: string;
  shipping_cost: string;
  shipping_name: string;
  shipping_email: string;
  shipping_phone: string;
  shipping_address_line1: string;
  shipping_address_line2?: string;
  shipping_city: string;
  shipping_state: string;
  shipping_country: string;
  shipping_postal_code: string;
  customer_notes?: string;
}

export interface CreateOrderData {
  items: {
    product_id: string;
    variant_id?: string;
    quantity: number;
  }[];
  shipping_address: ShippingAddress;
  billing_address?: ShippingAddress;
  customer_notes?: string;
}

// Payment Types
export interface Payment {
  id: string;
  order: string;
  order_number: string;
  payment_method: string;
  amount: string;
  currency: string;
  status: 'pending' | 'succeeded' | 'failed' | 'refunded';
  stripe_payment_intent_id?: string;
  created_at: string;
  paid_at?: string;
}

export interface CreatePaymentIntentData {
  order_id: string;
  payment_method_id?: string;
  save_payment_method?: boolean;
}

export interface PaymentIntentResponse {
  client_secret: string;
  payment_intent_id: string;
}

// API Error Types
export interface APIError {
  detail?: string;
  [key: string]: any;
}

// Notification Types
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
