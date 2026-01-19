from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Product, Category
from decimal import Decimal

User = get_user_model()


class ProductAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            description='Test description',
            price=Decimal('99.99'),
            sku='TEST-001',
            stock_quantity=10,
            category=self.category
        )
    
    def test_list_products(self):
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_retrieve_product(self):
        response = self.client.get(f'/api/products/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Product')
    
    def test_create_product_as_admin(self):
        self.client.force_authenticate(user=self.admin)
        
        data = {
            'name': 'New Product',
            'description': 'New description',
            'price': '149.99',
            'sku': 'NEW-001',
            'stock_quantity': 5,
            'category': self.category.id
        }
        response = self.client.post('/api/products/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)
    
    def test_create_product_as_regular_user(self):
        self.client.force_authenticate(user=self.user)
        
        data = {
            'name': 'New Product',
            'description': 'New description',
            'price': '149.99',
            'sku': 'NEW-001',
            'stock_quantity': 5,
            'category': self.category.id
        }
        
        response = self.client.post('/api/products/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_product_stock(self):
        self.client.force_authenticate(user=self.admin)
        
        data = {'stock_quantity': 20}
        response = self.client.patch(f'/api/products/{self.product.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 20)
    
    def test_product_search(self):
        response = self.client.get('/api/products/search/?q=test')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class OrderAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            description='Test',
            price=Decimal('99.99'),
            sku='TEST-001',
            stock_quantity=10,
            category=category
        )
    
    def test_create_order(self):
        data = {
            'items': [
                {
                    'product_id': str(self.product.id),
                    'quantity': 2
                }
            ],
            'shipping_address': {
                'name': 'John Doe',
                'email': 'john@example.com',
                'phone': '1234567890',
                'address_line1': '123 Main St',
                'city': 'New York',
                'state': 'NY',
                'country': 'USA',
                'postal_code': '10001'
            }
        }
        
        response = self.client.post('/api/orders/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)
    
    def test_create_order_insufficient_stock(self):
        data = {
            'items': [
                {
                    'product_id': str(self.product.id),
                    'quantity': 20
                }
            ],
            'shipping_address': {
                'name': 'John Doe',
                'email': 'john@example.com',
                'phone': '1234567890',
                'address_line1': '123 Main St',
                'city': 'New York',
                'state': 'NY',
                'country': 'USA',
                'postal_code': '10001'
            }
        }
        
        response = self.client.post('/api/orders/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_cancel_order(self):
        from apps.orders.models import Order, OrderItem
        
        order = Order.objects.create(
            user=self.user,
            subtotal=Decimal('199.98'),
            total=Decimal('199.98'),
            status='pending',
            shipping_name='John Doe',
            shipping_email='john@example.com',
            shipping_phone='1234567890',
            shipping_address_line1='123 Main St',
            shipping_city='New York',
            shipping_state='NY',
            shipping_country='USA',
            shipping_postal_code='10001'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            product_sku=self.product.sku,
            quantity=2,
            unit_price=self.product.price,
            total_price=self.product.price * 2
        )
        
        self.product.stock_quantity = 8
        self.product.save()
        
        response = self.client.post(f'/api/orders/{order.id}/cancel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
