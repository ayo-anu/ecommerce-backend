from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.test.utils import override_settings
from apps.orders.models import Order


class Command(BaseCommand):
    help = 'Quick check for N+1 queries'
    
    @override_settings(DEBUG=True)
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Checking for N+1 queries...\n'))
        
        # Check if we have any orders
        order_count = Order.objects.count()
        if order_count == 0:
            self.stdout.write(self.style.WARNING('No orders found. Creating test data first...'))
            self._create_test_data()
        
        # BAD: Without optimization
        self.stdout.write('='*60)
        self.stdout.write('Testing UNOPTIMIZED query...')
        self.stdout.write('='*60)
        reset_queries()
        
        orders = Order.objects.all()[:5]
        for order in orders:
            _ = order.user.email
            for item in order.items.all():
                _ = item.product.name
        
        bad_count = len(connection.queries)
        self.stdout.write(self.style.ERROR(f'❌ Queries without optimization: {bad_count}'))
        
        # GOOD: With optimization
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Testing OPTIMIZED query...')
        self.stdout.write('='*60)
        reset_queries()
        
        orders = Order.objects.all().select_related('user').prefetch_related(
            'items__product'
        )[:5]
        for order in orders:
            _ = order.user.email
            for item in order.items.all():
                _ = item.product.name
        
        good_count = len(connection.queries)
        self.stdout.write(self.style.SUCCESS(f'✅ Queries with optimization: {good_count}'))
        
        if bad_count > 0:
            improvement = ((bad_count - good_count) / bad_count * 100)
            self.stdout.write(self.style.SUCCESS(
                f'\n🎉 Improvement: {improvement:.1f}% reduction in queries!'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'💡 From {bad_count} queries down to {good_count} queries\n'
            ))
    
    def _create_test_data(self):
        """Create some test data if none exists"""
        from apps.accounts.models import User
        from apps.products.models import Product, Category
        from apps.orders.models import OrderItem
        
        # Create user
        user, _ = User.objects.get_or_create(
            email='test@example.com',
            defaults={
                'username': 'testuser',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Create category and products
        category, _ = Category.objects.get_or_create(
            name='Test Category',
            defaults={'slug': 'test-category'}
        )
        
        products = []
        for i in range(3):
            product, _ = Product.objects.get_or_create(
                sku=f'TEST{i}',
                defaults={
                    'name': f'Test Product {i}',
                    'slug': f'test-product-{i}',
                    'description': 'Test',
                    'price': 10.00,
                    'category': category,
                    'stock_quantity': 100
                }
            )
            products.append(product)
        
        # Create orders
        for i in range(3):
            order = Order.objects.create(
                user=user,
                subtotal=30.00,
                tax=3.00,
                shipping_cost=5.00,
                total=38.00,
                shipping_name='Test User',
                shipping_email='test@example.com',
                shipping_phone='1234567890',
                shipping_address_line1='123 Test St',
                shipping_city='Test City',
                shipping_state='Test State',
                shipping_country='Test Country',
                shipping_postal_code='12345'
            )
            
            # Add items
            for j in range(2):
                OrderItem.objects.create(
                    order=order,
                    product=products[j],
                    product_name=products[j].name,
                    product_sku=products[j].sku,
                    quantity=1,
                    unit_price=10.00,
                    total_price=10.00
                )
        
        self.stdout.write(self.style.SUCCESS('✅ Test data created!\n'))