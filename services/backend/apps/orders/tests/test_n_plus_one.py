from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from apps.orders.models import Order, OrderItem
from apps.products.models import Product, Category

User = get_user_model()


class OrderQueryOptimizationTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        cls.category = Category.objects.create(name='Test Category', slug='test-category')
        cls.products = []
        for i in range(10):
            product = Product.objects.create(
                name=f'Product {i}',
                slug=f'product-{i}',
                description='Test description',
                price=10.00,
                sku=f'SKU{i}',
                category=cls.category,
                stock_quantity=100
            )
            cls.products.append(product)
        
        cls.orders = []
        for i in range(5):
            order = Order.objects.create(
                user=cls.user,
                subtotal=100.00,
                tax=10.00,
                shipping_cost=5.00,
                total=115.00,
                shipping_name='Test User',
                shipping_email='test@example.com',
                shipping_phone='1234567890',
                shipping_address_line1='123 Test St',
                shipping_city='Test City',
                shipping_state='Test State',
                shipping_country='Test Country',
                shipping_postal_code='12345'
            )
            
            for j in range(3):
                OrderItem.objects.create(
                    order=order,
                    product=cls.products[j],
                    product_name=cls.products[j].name,
                    product_sku=cls.products[j].sku,
                    quantity=2,
                    unit_price=10.00,
                    total_price=20.00
                )
            
            cls.orders.append(order)
    
    def test_order_list_optimized(self):
        
        with CaptureQueriesContext(connection) as context:
            orders = Order.objects.all().select_related('user').prefetch_related(
                'items__product',
                'items__variant'
            )
            
            order_list = list(orders)
            
            for order in order_list:
                _ = order.user.email
                for item in order.items.all():
                    _ = item.product.name
                    _ = item.product_sku
        
        query_count = len(context.captured_queries)
        
        print(f"\n{'='*60}")
        print(f"✅ OPTIMIZED Order List: {query_count} queries")
        print(f"{'='*60}")
        
        for i, query in enumerate(context.captured_queries, 1):
            print(f"\nQuery {i}:")
            sql = query['sql']
            print(sql[:200] + '...' if len(sql) > 200 else sql)
        
        self.assertLessEqual(
            query_count, 
            4,
            f"Order list generated {query_count} queries, expected <= 4"
        )
    
    def test_order_list_unoptimized(self):
        
        with CaptureQueriesContext(connection) as context:
            orders = Order.objects.all()
            order_list = list(orders)
            
            for order in order_list:
                _ = order.user.email
                for item in order.items.all():
                    _ = item.product.name
        
        query_count = len(context.captured_queries)
        
        print(f"\n{'='*60}")
        print(f"❌ UNOPTIMIZED Order List: {query_count} queries")
        print(f"{'='*60}")
        print(f"This is N+1 problem! With 5 orders × 3 items each")
        print(f"Expected: 1 + 5 (users) + 5 (items) + 15 (products) = 26+ queries")
        
        self.assertGreater(
            query_count,
            15,
            f"Should have many queries due to N+1, got {query_count}"
        )
