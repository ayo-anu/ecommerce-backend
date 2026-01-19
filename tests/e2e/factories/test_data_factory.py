"""
Test Data Factory - Generate comprehensive test data
"""
import os
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
import random

# Add Django project to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "services" / "backend"))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from apps.products.models import Product, Category, ProductVariant, ProductImage, Tag
from apps.accounts.models import Address, UserProfile

User = get_user_model()


class TestDataFactory:
    """Main factory for generating all test data"""

    def __init__(self):
        self.created_objects = {
            'users': [],
            'categories': [],
            'products': [],
            'addresses': [],
            'tags': []
        }

    def cleanup(self):
        """Cleanup all created test data"""
        print("\n🧹 Cleaning up test data...")

        # Delete orders first (they have PROTECT relationships to users and products)
        from apps.orders.models import Order
        try:
            Order.objects.all().delete()
            print("  ✓ Deleted all orders")
        except Exception as e:
            print(f"  ⚠ Could not delete orders: {e}")

        # Delete in reverse order of dependencies
        for user in self.created_objects['users']:
            try:
                user.delete()
            except Exception as e:
                print(f"  ⚠ Could not delete user {user.email}: {e}")

        for product in self.created_objects['products']:
            try:
                product.delete()
            except Exception as e:
                print(f"  ⚠ Could not delete product {product.sku}: {e}")

        for category in self.created_objects['categories']:
            try:
                category.delete()
            except Exception as e:
                print(f"  ⚠ Could not delete category {category.name}: {e}")

        print("✅ Cleanup complete")

    def create_all(self):
        """Create all test data"""
        print("\n🏭 Generating comprehensive test data...")

        self.create_users()
        self.create_categories()
        self.create_tags()
        self.create_products()
        self.create_addresses()

        print(f"\n✅ Test data generation complete!")
        print(f"   Users: {len(self.created_objects['users'])}")
        print(f"   Categories: {len(self.created_objects['categories'])}")
        print(f"   Products: {len(self.created_objects['products'])}")
        print(f"   Addresses: {len(self.created_objects['addresses'])}")
        print(f"   Tags: {len(self.created_objects['tags'])}")

        return self.created_objects

    def create_users(self):
        """Create test users"""
        print("\n👥 Creating test users...")

        users_data = [
            # Normal users
            {
                "email": "alice@example.com",
                "username": "alice",
                "password": "SecurePass123!",
                "first_name": "Alice",
                "last_name": "Johnson",
                "phone": "+1-555-0100",
                "is_staff": False
            },
            {
                "email": "bob@example.com",
                "username": "bob",
                "password": "SecurePass123!",
                "first_name": "Bob",
                "last_name": "Smith",
                "phone": "+1-555-0101",
                "is_staff": False
            },
            {
                "email": "charlie@example.com",
                "username": "charlie",
                "password": "SecurePass123!",
                "first_name": "Charlie",
                "last_name": "Chen",
                "phone": "+1-555-0102",
                "is_staff": False
            },

            # Edge case users
            {
                "email": "new.user@example.com",
                "username": "newuser",
                "password": "Pass123!",
                "first_name": "New",
                "last_name": "User",
                "phone": "+1-555-0103",
                "is_staff": False
            },
            {
                "email": "vip@example.com",
                "username": "vipuser",
                "password": "VIP123!",
                "first_name": "VIP",
                "last_name": "Customer",
                "phone": "+1-555-0104",
                "is_staff": False
            },

            # Admin
            {
                "email": "admin@example.com",
                "username": "admin",
                "password": "Admin123!",
                "first_name": "Admin",
                "last_name": "User",
                "phone": "+1-555-0199",
                "is_staff": True,
                "is_superuser": True
            },
        ]

        for user_data in users_data:
            # Check if user already exists (by email)
            existing_user = User.objects.filter(email=user_data["email"]).first()
            if existing_user:
                # User already exists - skip creation and reuse
                self.created_objects['users'].append(existing_user)
                continue

            # Extract password and special flags
            password = user_data.pop("password")
            is_staff = user_data.pop("is_staff", False)
            is_superuser = user_data.pop("is_superuser", False)

            # Create user
            user = User.objects.create_user(**user_data)
            user.set_password(password)
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.email_verified = True  # Bypass email verification for testing
            user.save()

            # Create profile if not exists
            if not hasattr(user, 'profile'):
                UserProfile.objects.create(user=user)

            self.created_objects['users'].append(user)
            print(f"  ✓ Created user: {user.email}")

        return self.created_objects['users']

    def create_categories(self):
        """Create product categories"""
        print("\n📁 Creating categories...")

        categories_data = [
            {"name": "Electronics", "description": "Electronic devices and accessories"},
            {"name": "Clothing", "description": "Apparel and fashion items"},
            {"name": "Home & Kitchen", "description": "Home appliances and kitchenware"},
            {"name": "Books", "description": "Books and educational materials"},
            {"name": "Sports", "description": "Sports and outdoor equipment"},
            {"name": "Toys", "description": "Toys and games"},
            {"name": "Beauty", "description": "Beauty and personal care products"},
            {"name": "Automotive", "description": "Automotive parts and accessories"},
        ]

        for cat_data in categories_data:
            # Get or create (don't delete if exists due to protected foreign keys)
            category, created = Category.objects.get_or_create(
                name=cat_data["name"],
                defaults=cat_data
            )
            self.created_objects['categories'].append(category)
            if created:
                print(f"  ✓ Created category: {category.name}")
            else:
                print(f"  ↻ Using existing category: {category.name}")

        return self.created_objects['categories']

    def create_tags(self):
        """Create product tags"""
        print("\n🏷️ Creating tags...")

        tags_list = [
            "wireless", "bluetooth", "premium", "sale", "new-arrival",
            "bestseller", "eco-friendly", "limited-edition", "imported",
            "handmade", "vintage", "modern", "classic", "luxury"
        ]

        for tag_name in tags_list:
            tag, created = Tag.objects.get_or_create(name=tag_name)
            if created:
                self.created_objects['tags'].append(tag)
                print(f"  ✓ Created tag: {tag.name}")

        return self.created_objects['tags']

    def create_products(self):
        """Create comprehensive product catalog"""
        print("\n📦 Creating products...")

        # Get categories
        electronics = Category.objects.get(name="Electronics")
        clothing = Category.objects.get(name="Clothing")
        home = Category.objects.get(name="Home & Kitchen")
        books = Category.objects.get(name="Books")

        products_data = [
            # Electronics
            {
                "name": "Wireless Bluetooth Headphones - Premium",
                "slug": "wireless-bluetooth-headphones-premium",
                "sku": "ELEC-HP-001",
                "description": "High-quality wireless headphones with noise cancellation, 30-hour battery life, and premium sound quality. Perfect for music lovers and professionals.",
                "price": Decimal("199.99"),
                "compare_at_price": Decimal("249.99"),
                "cost_per_item": Decimal("80.00"),
                "stock_quantity": 50,
                "low_stock_threshold": 10,
                "category": electronics,
                "tags": ["wireless", "bluetooth", "premium"],
                "is_active": True,
                "is_featured": True,
                "meta_title": "Premium Wireless Headphones | 30h Battery",
                "meta_description": "Experience superior sound with our premium wireless headphones."
            },
            {
                "name": "4K Smart TV - 55 inch",
                "slug": "4k-smart-tv-55-inch",
                "sku": "ELEC-TV-001",
                "description": "Ultra HD 4K Smart TV with HDR, built-in streaming apps, and voice control.",
                "price": Decimal("599.99"),
                "compare_at_price": Decimal("799.99"),
                "cost_per_item": Decimal("300.00"),
                "stock_quantity": 15,
                "low_stock_threshold": 5,
                "category": electronics,
                "tags": ["sale", "new-arrival"],
                "is_active": True,
                "is_featured": True
            },
            {
                "name": "Wireless Gaming Mouse",
                "slug": "wireless-gaming-mouse",
                "sku": "ELEC-MOUSE-001",
                "description": "High-precision wireless gaming mouse with RGB lighting and programmable buttons.",
                "price": Decimal("79.99"),
                "cost_per_item": Decimal("30.00"),
                "stock_quantity": 100,
                "low_stock_threshold": 20,
                "category": electronics,
                "tags": ["wireless"],
                "is_active": True,
                "is_featured": False
            },

            # Clothing
            {
                "name": "Men's Cotton T-Shirt - Blue",
                "slug": "mens-cotton-tshirt-blue",
                "sku": "CLOTH-TS-001",
                "description": "Comfortable 100% cotton t-shirt in classic blue color. Available in multiple sizes.",
                "price": Decimal("24.99"),
                "compare_at_price": Decimal("34.99"),
                "cost_per_item": Decimal("8.00"),
                "stock_quantity": 200,
                "low_stock_threshold": 30,
                "category": clothing,
                "tags": ["sale"],
                "is_active": True,
                "is_featured": False,
                "has_variants": True
            },
            {
                "name": "Women's Winter Jacket - Black",
                "slug": "womens-winter-jacket-black",
                "sku": "CLOTH-JK-001",
                "description": "Warm and stylish winter jacket with water-resistant fabric and fleece lining.",
                "price": Decimal("129.99"),
                "compare_at_price": Decimal("179.99"),
                "cost_per_item": Decimal("60.00"),
                "stock_quantity": 40,
                "low_stock_threshold": 10,
                "category": clothing,
                "tags": ["new-arrival"],
                "is_active": True,
                "is_featured": True
            },

            # Home & Kitchen
            {
                "name": "Stainless Steel Coffee Maker - 12 Cup",
                "slug": "stainless-steel-coffee-maker-12cup",
                "sku": "HOME-CM-001",
                "description": "Programmable coffee maker with thermal carafe, auto-shutoff, and brew strength control.",
                "price": Decimal("89.99"),
                "cost_per_item": Decimal("40.00"),
                "stock_quantity": 60,
                "low_stock_threshold": 15,
                "category": home,
                "tags": ["bestseller"],
                "is_active": True,
                "is_featured": False
            },
            {
                "name": "Non-Stick Cookware Set - 10 Piece",
                "slug": "nonstick-cookware-set-10piece",
                "sku": "HOME-CK-001",
                "description": "Complete cookware set with non-stick coating, dishwasher safe, and heat-resistant handles.",
                "price": Decimal("149.99"),
                "compare_at_price": Decimal("199.99"),
                "cost_per_item": Decimal("70.00"),
                "stock_quantity": 25,
                "low_stock_threshold": 8,
                "category": home,
                "tags": ["sale", "bestseller"],
                "is_active": True,
                "is_featured": True
            },

            # Books
            {
                "name": "Python Programming for Beginners",
                "slug": "python-programming-for-beginners",
                "sku": "BOOK-PY-001",
                "description": "Comprehensive guide to Python programming with hands-on examples and projects.",
                "price": Decimal("39.99"),
                "compare_at_price": Decimal("49.99"),
                "cost_per_item": Decimal("15.00"),
                "stock_quantity": 75,
                "low_stock_threshold": 20,
                "category": books,
                "tags": ["bestseller", "new-arrival"],
                "is_active": True,
                "is_featured": True
            },

            # Edge Case Products
            {
                "name": "Out of Stock Item - Test",
                "slug": "out-of-stock-item-test",
                "sku": "TEST-OOS-001",
                "description": "This item is currently out of stock for testing purposes.",
                "price": Decimal("29.99"),
                "cost_per_item": Decimal("10.00"),
                "stock_quantity": 0,  # OUT OF STOCK
                "low_stock_threshold": 5,
                "category": electronics,
                "tags": [],
                "is_active": True,
                "is_featured": False
            },
            {
                "name": "Low Stock Item - Only 3 Left",
                "slug": "low-stock-item-test",
                "sku": "TEST-LOW-001",
                "description": "This item has very low stock for testing low inventory scenarios.",
                "price": Decimal("19.99"),
                "cost_per_item": Decimal("8.00"),
                "stock_quantity": 3,  # LOW STOCK
                "low_stock_threshold": 10,
                "category": electronics,
                "tags": [],
                "is_active": True,
                "is_featured": False
            },
            {
                "name": "Inactive Product - Not for Sale",
                "slug": "inactive-product-test",
                "sku": "TEST-INACT-001",
                "description": "This product is inactive and should not appear in listings.",
                "price": Decimal("99.99"),
                "cost_per_item": Decimal("40.00"),
                "stock_quantity": 50,
                "low_stock_threshold": 10,
                "category": electronics,
                "tags": [],
                "is_active": False,  # INACTIVE
                "is_featured": False
            },
            {
                "name": "High-Value Luxury Watch",
                "slug": "high-value-luxury-watch",
                "sku": "LUXURY-WATCH-001",
                "description": "Premium luxury watch with Swiss movement and sapphire crystal.",
                "price": Decimal("5999.99"),
                "compare_at_price": Decimal("7999.99"),
                "cost_per_item": Decimal("3000.00"),
                "stock_quantity": 5,
                "low_stock_threshold": 2,
                "category": electronics,
                "tags": ["luxury", "premium", "limited-edition"],
                "is_active": True,
                "is_featured": True
            }
        ]

        for prod_data in products_data:
            # Extract special fields
            tags = prod_data.pop("tags", [])
            has_variants = prod_data.pop("has_variants", False)

            # Get or create product by SKU
            sku = prod_data["sku"]
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults=prod_data
            )

            # Update if exists
            if not created:
                for key, value in prod_data.items():
                    if key not in ['sku']:  # Don't update SKU
                        setattr(product, key, value)
                product.save()

            # Clear and add tags
            product.tags.clear()
            for tag_name in tags:
                tag = Tag.objects.get(name=tag_name)
                product.tags.add(tag)

            # Create variants for t-shirt
            if has_variants and product.sku == "CLOTH-TS-001":
                # Delete existing variants
                product.variants.all().delete()
                self._create_tshirt_variants(product)

            self.created_objects['products'].append(product)
            if created:
                print(f"  ✓ Created product: {product.name} (SKU: {product.sku})")
            else:
                print(f"  ↻ Updated product: {product.name} (SKU: {product.sku})")

        return self.created_objects['products']

    def _create_tshirt_variants(self, product):
        """Create size variants for t-shirt"""
        sizes = [
            ("S", 50),
            ("M", 80),
            ("L", 50),
            ("XL", 20)
        ]

        for size, stock in sizes:
            variant = ProductVariant.objects.create(
                product=product,
                name=f"Size: {size}, Color: Blue",
                sku=f"{product.sku}-{size}",
                stock_quantity=stock,
                attributes={"size": size, "color": "blue"}
            )
            print(f"    ✓ Created variant: {variant.name}")

    def create_addresses(self):
        """Create test addresses for users"""
        print("\n🏠 Creating addresses...")

        users = User.objects.filter(email__in=[
            "alice@example.com",
            "bob@example.com",
            "charlie@example.com"
        ])

        addresses_data = {
            "alice@example.com": [
                {
                    "address_type": "both",
                    "full_name": "Alice Johnson",
                    "phone": "+1-555-0100",
                    "address_line1": "123 Main Street",
                    "address_line2": "Apt 4B",
                    "city": "New York",
                    "state": "NY",
                    "country": "United States",
                    "postal_code": "10001",
                    "is_default": True
                }
            ],
            "bob@example.com": [
                {
                    "address_type": "both",
                    "full_name": "Bob Smith",
                    "phone": "+44-20-1234-5678",
                    "address_line1": "10 Downing Street",
                    "address_line2": "",
                    "city": "London",
                    "state": "England",
                    "country": "United Kingdom",
                    "postal_code": "SW1A 2AA",
                    "is_default": True
                }
            ],
            "charlie@example.com": [
                {
                    "address_type": "both",
                    "full_name": "Charlie Chen",
                    "phone": "+86-10-1234-5678",
                    "address_line1": "Building 3, Zhongguancun",
                    "address_line2": "Haidian District",
                    "city": "Beijing",
                    "state": "Beijing",
                    "country": "China",
                    "postal_code": "100080",
                    "is_default": True
                }
            ]
        }

        for user in users:
            if user.email in addresses_data:
                for addr_data in addresses_data[user.email]:
                    # Delete existing
                    Address.objects.filter(user=user).delete()

                    # Create address
                    address = Address.objects.create(user=user, **addr_data)
                    self.created_objects['addresses'].append(address)
                    print(f"  ✓ Created address for {user.email}: {address.city}, {address.country}")

        return self.created_objects['addresses']


def main():
    """Main function to generate test data"""
    factory = TestDataFactory()

    try:
        # Create all test data
        created_objects = factory.create_all()

        print("\n" + "=" * 60)
        print("✅ TEST DATA GENERATION SUCCESSFUL!")
        print("=" * 60)

        return created_objects

    except Exception as e:
        print(f"\n❌ Error generating test data: {e}")
        import traceback
        traceback.print_exc()
        factory.cleanup()
        return None


if __name__ == "__main__":
    main()
