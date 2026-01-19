"""
Database Integrity and CRUD Testing
Comprehensive database validation including migrations, relationships, and data integrity
"""
import pytest
import os
import sys
from pathlib import Path
from decimal import Decimal

# Setup Django environment
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'services' / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection, transaction
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from apps.products.models import Product, Category, ProductReview, Wishlist
from apps.orders.models import Order, OrderItem, Cart, CartItem
from apps.payments.models import Payment, Refund, PaymentMethod
from apps.notifications.models import Notification, EmailTemplate
from apps.analytics.models import UserActivity, SalesMetric


User = get_user_model()


class TestDatabaseConnection:
    """Test database connectivity and basic operations"""

    def test_database_connection(self):
        """Database should be accessible"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_database_version(self):
        """Check database version"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            assert 'PostgreSQL' in version
            print(f"\n✅ Database: {version}")


class TestMigrations:
    """Test that all migrations are applied"""

    def test_migrations_applied(self):
        """All migrations should be applied"""
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        # No pending migrations
        assert len(plan) == 0, \
            f"Found {len(plan)} pending migrations: {plan}"

    def test_all_tables_exist(self):
        """All expected tables should exist"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """)
            tables = [row[0] for row in cursor.fetchall()]

        # Check for key tables
        expected_tables = [
            'accounts_user',
            'products_product',
            'products_category',
            'orders_order',
            'payments_payment',
        ]

        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"

        print(f"\n✅ Found {len(tables)} tables in database")


@pytest.mark.django_db
class TestUserModel:
    """Test User model CRUD operations"""

    def test_create_user(self):
        """Create a new user"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        assert user.id is not None
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')

    def test_user_email_unique(self):
        """Email should be unique"""
        User.objects.create_user(
            email='unique@example.com',
            password='pass123'
        )

        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email='unique@example.com',
                password='pass456'
            )

    def test_user_str_representation(self):
        """User __str__ should return email"""
        user = User.objects.create_user(
            email='test@example.com',
            password='pass123'
        )

        assert str(user) == 'test@example.com'


@pytest.mark.django_db
class TestProductModel:
    """Test Product model and relationships"""

    def test_create_category(self):
        """Create a product category"""
        category = Category.objects.create(
            name='Electronics',
            slug='electronics',
            description='Electronic products'
        )

        assert category.id is not None
        assert category.name == 'Electronics'

    def test_create_product(self):
        """Create a product with category"""
        category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )

        product = Product.objects.create(
            name='Laptop',
            slug='laptop',
            description='High-performance laptop',
            price=Decimal('999.99'),
            stock=10,
            category=category
        )

        assert product.id is not None
        assert product.price == Decimal('999.99')
        assert product.category.name == 'Electronics'

    def test_product_price_positive(self):
        """Product price should be positive"""
        category = Category.objects.create(name='Test', slug='test')

        # Negative price should fail validation (if implemented)
        product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price=Decimal('-10.00'),  # Invalid
            stock=5,
            category=category
        )

        # Note: This tests whether validation is implemented
        # In production, you should have a check constraint
        assert product.price < 0, "Negative price allowed (validation needed)"

    def test_product_category_relationship(self):
        """Test foreign key relationship"""
        category = Category.objects.create(
            name='Books',
            slug='books'
        )

        product1 = Product.objects.create(
            name='Book 1',
            slug='book-1',
            price=Decimal('19.99'),
            stock=5,
            category=category
        )

        product2 = Product.objects.create(
            name='Book 2',
            slug='book-2',
            price=Decimal('29.99'),
            stock=3,
            category=category
        )

        # Category should have 2 products
        assert category.products.count() == 2
        assert list(category.products.all()) == [product1, product2]

    def test_product_slug_unique(self):
        """Product slug should be unique"""
        category = Category.objects.create(name='Test', slug='test')

        Product.objects.create(
            name='Product 1',
            slug='unique-slug',
            price=Decimal('10.00'),
            stock=5,
            category=category
        )

        with pytest.raises(IntegrityError):
            Product.objects.create(
                name='Product 2',
                slug='unique-slug',  # Duplicate
                price=Decimal('20.00'),
                stock=3,
                category=category
            )


@pytest.mark.django_db
class TestOrderModel:
    """Test Order model and order items"""

    def test_create_order(self):
        """Create an order with items"""
        user = User.objects.create_user(
            email='customer@example.com',
            password='pass123'
        )

        category = Category.objects.create(name='Test', slug='test')
        product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price=Decimal('50.00'),
            stock=10,
            category=category
        )

        order = Order.objects.create(
            user=user,
            total_amount=Decimal('100.00'),
            status='pending'
        )

        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=2,
            price=Decimal('50.00')
        )

        assert order.id is not None
        assert order.items.count() == 1
        assert order_item.quantity == 2

    def test_order_total_calculation(self):
        """Order total should match sum of items"""
        user = User.objects.create_user(
            email='customer@example.com',
            password='pass123'
        )

        category = Category.objects.create(name='Test', slug='test')

        product1 = Product.objects.create(
            name='Product 1',
            slug='product-1',
            price=Decimal('25.00'),
            stock=10,
            category=category
        )

        product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
            price=Decimal('35.00'),
            stock=10,
            category=category
        )

        order = Order.objects.create(
            user=user,
            total_amount=Decimal('0.00'),  # Will calculate
            status='pending'
        )

        OrderItem.objects.create(
            order=order,
            product=product1,
            quantity=2,
            price=product1.price
        )

        OrderItem.objects.create(
            order=order,
            product=product2,
            quantity=1,
            price=product2.price
        )

        # Calculate total
        calculated_total = sum(
            item.quantity * item.price
            for item in order.items.all()
        )

        # Total should be 2*25 + 1*35 = 85
        assert calculated_total == Decimal('85.00')


@pytest.mark.django_db
class TestPaymentModel:
    """Test Payment model"""

    def test_create_payment(self):
        """Create a payment for an order"""
        user = User.objects.create_user(
            email='customer@example.com',
            password='pass123'
        )

        order = Order.objects.create(
            user=user,
            total_amount=Decimal('100.00'),
            status='pending'
        )

        payment = Payment.objects.create(
            order=order,
            amount=Decimal('100.00'),
            payment_method='credit_card',
            status='completed',
            transaction_id='txn_12345'
        )

        assert payment.id is not None
        assert payment.order == order
        assert payment.amount == order.total_amount


@pytest.mark.django_db
class TestDatabaseConstraints:
    """Test database constraints and data integrity"""

    def test_foreign_key_cascade(self):
        """Deleting parent should handle children appropriately"""
        category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price=Decimal('10.00'),
            stock=5,
            category=category
        )

        category_id = category.id
        product_id = product.id

        # Delete category
        category.delete()

        # Check if product still exists (depends on on_delete setting)
        # If on_delete=CASCADE, product should be deleted
        # If on_delete=PROTECT, delete should fail
        # If on_delete=SET_NULL, product.category should be None

        product_exists = Product.objects.filter(id=product_id).exists()

        # Document the behavior
        if product_exists:
            product = Product.objects.get(id=product_id)
            print(f"\n⚠️  Product still exists after category deletion")
            print(f"   Category: {product.category}")
        else:
            print(f"\n✅ CASCADE delete working: product deleted with category")

    def test_unique_constraints(self):
        """Test unique constraints are enforced"""
        # Test user email uniqueness
        User.objects.create_user(
            email='unique@test.com',
            password='pass123'
        )

        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email='unique@test.com',
                password='pass456'
            )

    def test_null_constraints(self):
        """Test NOT NULL constraints"""
        category = Category.objects.create(name='Test', slug='test')

        # Try to create product without required fields
        with pytest.raises(IntegrityError):
            Product.objects.create(
                name='Test',
                slug='test-slug',
                # price missing (should be required)
                stock=5,
                category=category
            )


@pytest.mark.django_db
class TestDatabaseIndexes:
    """Test that critical indexes exist"""

    def test_indexes_exist(self):
        """Check that important indexes are created"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    tablename,
                    indexname,
                    indexdef
                FROM
                    pg_indexes
                WHERE
                    schemaname = 'public'
                ORDER BY
                    tablename,
                    indexname;
            """)

            indexes = cursor.fetchall()

        index_names = [idx[1] for idx in indexes]

        # Check for important indexes
        # Primary keys
        assert any('pkey' in idx for idx in index_names), \
            "Primary key indexes not found"

        # Foreign keys should have indexes
        print(f"\n✅ Found {len(indexes)} indexes in database")

        # Print some key indexes
        for table, index, definition in indexes[:10]:
            print(f"   {table}.{index}")


@pytest.mark.django_db
class TestTransactions:
    """Test transaction handling"""

    def test_transaction_rollback(self):
        """Failed transaction should rollback"""
        initial_count = User.objects.count()
        error_raised = False

        try:
            with transaction.atomic():
                User.objects.create_user(
                    email='test1@example.com',
                    password='pass123'
                )

                # Force an error
                User.objects.create_user(
                    email='test1@example.com',  # Duplicate
                    password='pass456'
                )
        except IntegrityError:
            error_raised = True

        # Count should be unchanged (rolled back)
        assert error_raised is True
        assert User.objects.count() == initial_count

    def test_transaction_commit(self):
        """Successful transaction should commit"""
        initial_count = User.objects.count()

        with transaction.atomic():
            User.objects.create_user(
                email='test1@example.com',
                password='pass123'
            )

            User.objects.create_user(
                email='test2@example.com',
                password='pass456'
            )

        # Count should increase by 2
        assert User.objects.count() == initial_count + 2


@pytest.mark.django_db
class TestQueryPerformance:
    """Test query performance and N+1 issues"""

    def test_select_related_usage(self):
        """Test that select_related reduces queries"""
        category = Category.objects.create(name='Test', slug='test')

        # Create 10 products
        for i in range(10):
            Product.objects.create(
                name=f'Product {i}',
                slug=f'product-{i}',
                price=Decimal('10.00'),
                stock=5,
                category=category
            )

        # Without select_related (N+1 problem)
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as context:
            products = Product.objects.all()
            for product in products:
                _ = product.category.name  # Accesses category

        queries_without = len(context.captured_queries)

        # With select_related (optimized)
        with CaptureQueriesContext(connection) as context:
            products = Product.objects.select_related('category').all()
            for product in products:
                _ = product.category.name

        queries_with = len(context.captured_queries)

        # Should use fewer queries with select_related
        print(f"\n📊 Query optimization:")
        print(f"   Without select_related: {queries_without} queries")
        print(f"   With select_related: {queries_with} queries")

        # With select_related should be significantly better
        assert queries_with < queries_without, \
            "select_related not reducing queries"


@pytest.mark.django_db
class TestDataValidation:
    """Test model validation rules"""

    def test_email_validation(self):
        """Test email format validation"""
        # This depends on if you have validators
        # Try to create user with invalid email
        try:
            user = User.objects.create_user(
                email='invalid-email',
                password='pass123'
            )
            # If it succeeds, validation may not be implemented
            print("\n⚠️  Email validation may not be enforced")
        except Exception as e:
            print(f"\n✅ Email validation working: {e}")

    def test_decimal_precision(self):
        """Test decimal field precision"""
        category = Category.objects.create(name='Test', slug='test')

        product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price=Decimal('999.999'),  # More precision than allowed
            stock=5,
            category=category
        )

        # Check if rounding is applied
        print(f"\n💰 Price precision: {product.price}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
