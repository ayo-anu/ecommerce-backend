"""
Synthetic Data Generator for E-commerce AI Platform
Generates realistic fake data for testing all 7 services
"""
import random
import json
from datetime import datetime, timedelta
from pathlib import Path
import base64
from io import BytesIO

# Try to import optional libraries
try:
    from faker import Faker
    FAKER_AVAILABLE = True
except ImportError:
    FAKER_AVAILABLE = False
    print("⚠️  Faker not installed. Install with: pip install faker")

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  Pillow not installed. Install with: pip install Pillow")


class SyntheticDataGenerator:
    """Generate realistic test data for all services"""
    
    def __init__(self, num_users=100, num_products=500, num_orders=1000):
        self.num_users = num_users
        self.num_products = num_products
        self.num_orders = num_orders
        
        if FAKER_AVAILABLE:
            self.fake = Faker()
        
        # Product categories and attributes
        self.categories = [
            'Electronics', 'Clothing', 'Home & Garden', 'Sports', 
            'Books', 'Toys', 'Beauty', 'Automotive', 'Food', 'Jewelry'
        ]
        
        self.colors = [
            'Red', 'Blue', 'Green', 'Black', 'White', 
            'Silver', 'Gold', 'Pink', 'Purple', 'Orange'
        ]
        
        self.brands = [
            'TechPro', 'StyleMax', 'HomeComfort', 'SportElite', 
            'ReadWell', 'PlayFun', 'BeautyGlow', 'DriveRight',
            'TasteBest', 'ShineOn'
        ]
        
        # Output directory
        self.output_dir = Path('test_data')
        self.output_dir.mkdir(exist_ok=True)
        
    def generate_users(self):
        """Generate synthetic user data"""
        print("\n📊 Generating users...")
        users = []
        
        for i in range(self.num_users):
            if FAKER_AVAILABLE:
                user = {
                    'user_id': f'user_{i+1:04d}',
                    'email': self.fake.email(),
                    'name': self.fake.name(),
                    'phone': self.fake.phone_number(),
                    'address': {
                        'street': self.fake.street_address(),
                        'city': self.fake.city(),
                        'state': self.fake.state(),
                        'country': self.fake.country(),
                        'zipcode': self.fake.zipcode()
                    },
                    'registration_date': (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
                    'preferences': {
                        'categories': random.sample(self.categories, k=random.randint(2, 5)),
                        'price_range': random.choice(['low', 'medium', 'high']),
                        'frequency': random.choice(['occasional', 'regular', 'frequent'])
                    }
                }
            else:
                user = {
                    'user_id': f'user_{i+1:04d}',
                    'email': f'user{i+1}@example.com',
                    'name': f'User {i+1}',
                    'phone': f'+1-555-{random.randint(1000, 9999)}',
                    'registration_date': (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
                }
            users.append(user)
        
        # Save to file
        output_file = self.output_dir / 'users.json'
        with open(output_file, 'w') as f:
            json.dump(users, f, indent=2)
        
        print(f"✅ Generated {len(users)} users → {output_file}")
        return users
    
    def generate_products(self):
        """Generate synthetic product data"""
        print("\n📦 Generating products...")
        products = []
        
        product_templates = {
            'Electronics': ['Laptop', 'Smartphone', 'Tablet', 'Headphones', 'Camera', 'Smart Watch'],
            'Clothing': ['T-Shirt', 'Jeans', 'Dress', 'Jacket', 'Shoes', 'Hat'],
            'Home & Garden': ['Sofa', 'Lamp', 'Rug', 'Plant', 'Curtains', 'Cushion'],
            'Sports': ['Running Shoes', 'Yoga Mat', 'Dumbbell', 'Tennis Racket', 'Basketball', 'Bicycle'],
            'Books': ['Novel', 'Cookbook', 'Biography', 'Textbook', 'Comic Book', 'Magazine'],
            'Toys': ['Action Figure', 'Board Game', 'Puzzle', 'Doll', 'Building Blocks', 'Remote Car'],
            'Beauty': ['Lipstick', 'Face Cream', 'Perfume', 'Shampoo', 'Nail Polish', 'Makeup Kit'],
            'Automotive': ['Car Mat', 'Phone Holder', 'Air Freshener', 'Seat Cover', 'Tire Pump', 'Dashboard Cam'],
            'Food': ['Organic Coffee', 'Protein Bar', 'Olive Oil', 'Dark Chocolate', 'Green Tea', 'Honey'],
            'Jewelry': ['Necklace', 'Bracelet', 'Ring', 'Earrings', 'Watch', 'Brooch']
        }
        
        for i in range(self.num_products):
            category = random.choice(self.categories)
            product_type = random.choice(product_templates[category])
            color = random.choice(self.colors)
            brand = random.choice(self.brands)
            
            base_price = random.uniform(10, 1000)
            
            product = {
                'product_id': f'prod_{i+1:04d}',
                'name': f'{brand} {color} {product_type}',
                'description': f'High-quality {color.lower()} {product_type.lower()} from {brand}. Perfect for everyday use.',
                'category': category,
                'subcategory': product_type,
                'brand': brand,
                'color': color,
                'price': round(base_price, 2),
                'cost': round(base_price * 0.6, 2),  # 40% margin
                'stock': random.randint(0, 500),
                'rating': round(random.uniform(3.0, 5.0), 1),
                'num_reviews': random.randint(0, 500),
                'tags': [
                    category.lower(),
                    product_type.lower().replace(' ', '-'),
                    color.lower(),
                    brand.lower()
                ],
                'attributes': {
                    'weight': f'{random.uniform(0.1, 10.0):.1f}kg',
                    'dimensions': f'{random.randint(10, 50)}x{random.randint(10, 50)}x{random.randint(5, 30)}cm',
                    'warranty': f'{random.choice([6, 12, 24, 36])} months'
                },
                'created_at': (datetime.now() - timedelta(days=random.randint(1, 180))).isoformat()
            }
            products.append(product)
        
        # Save to file
        output_file = self.output_dir / 'products.json'
        with open(output_file, 'w') as f:
            json.dump(products, f, indent=2)
        
        print(f"✅ Generated {len(products)} products → {output_file}")
        return products
    
    def generate_orders(self, users, products):
        """Generate synthetic order data"""
        print("\n🛒 Generating orders...")
        orders = []
        
        for i in range(self.num_orders):
            user = random.choice(users)
            num_items = random.randint(1, 5)
            order_products = random.sample(products, k=num_items)
            
            items = []
            total_amount = 0
            for prod in order_products:
                quantity = random.randint(1, 3)
                price = prod['price']
                items.append({
                    'product_id': prod['product_id'],
                    'product_name': prod['name'],
                    'quantity': quantity,
                    'price': price,
                    'subtotal': round(price * quantity, 2)
                })
                total_amount += price * quantity
            
            order_date = datetime.now() - timedelta(days=random.randint(0, 90))
            
            order = {
                'order_id': f'order_{i+1:05d}',
                'user_id': user['user_id'],
                'order_date': order_date.isoformat(),
                'items': items,
                'total_amount': round(total_amount, 2),
                'status': random.choice(['pending', 'processing', 'shipped', 'delivered', 'cancelled']),
                'payment_method': random.choice(['credit_card', 'debit_card', 'paypal', 'bank_transfer']),
                'shipping_address': user.get('address', {'city': 'Unknown'}),
            }
            orders.append(order)
        
        # Save to file
        output_file = self.output_dir / 'orders.json'
        with open(output_file, 'w') as f:
            json.dump(orders, f, indent=2)
        
        print(f"✅ Generated {len(orders)} orders → {output_file}")
        return orders
    
    def generate_interactions(self, users, products):
        """Generate user-product interaction data"""
        print("\n👆 Generating interactions...")
        interactions = []
        
        interaction_types = ['view', 'click', 'add_to_cart', 'purchase', 'like', 'share']
        
        # Generate 5-10 interactions per user
        for user in users:
            num_interactions = random.randint(5, 10)
            for _ in range(num_interactions):
                product = random.choice(products)
                
                interaction = {
                    'interaction_id': f'int_{len(interactions)+1:06d}',
                    'user_id': user['user_id'],
                    'product_id': product['product_id'],
                    'interaction_type': random.choice(interaction_types),
                    'timestamp': (datetime.now() - timedelta(days=random.randint(0, 30), 
                                                           hours=random.randint(0, 23),
                                                           minutes=random.randint(0, 59))).isoformat(),
                    'session_id': f'session_{random.randint(1000, 9999)}',
                    'device': random.choice(['mobile', 'desktop', 'tablet']),
                    'duration_seconds': random.randint(5, 300)
                }
                interactions.append(interaction)
        
        # Save to file
        output_file = self.output_dir / 'interactions.json'
        with open(output_file, 'w') as f:
            json.dump(interactions, f, indent=2)
        
        print(f"✅ Generated {len(interactions)} interactions → {output_file}")
        return interactions
    
    def generate_reviews(self, users, products):
        """Generate product reviews"""
        print("\n⭐ Generating reviews...")
        reviews = []
        
        positive_comments = [
            "Excellent product! Highly recommended.",
            "Great quality, exactly what I needed.",
            "Very satisfied with my purchase.",
            "Amazing product, will buy again!",
            "Perfect! Exceeded my expectations."
        ]
        
        negative_comments = [
            "Not as described, disappointed.",
            "Quality could be better.",
            "Arrived damaged, need replacement.",
            "Overpriced for what you get.",
            "Expected more from this brand."
        ]
        
        neutral_comments = [
            "It's okay, nothing special.",
            "Does the job, average quality.",
            "Good for the price.",
            "Decent product.",
            "As expected."
        ]
        
        # Generate 1-3 reviews per product (randomly)
        for product in random.sample(products, k=int(self.num_products * 0.3)):
            num_reviews = random.randint(1, 3)
            for _ in range(num_reviews):
                user = random.choice(users)
                rating = random.randint(1, 5)
                
                if rating >= 4:
                    comment = random.choice(positive_comments)
                elif rating <= 2:
                    comment = random.choice(negative_comments)
                else:
                    comment = random.choice(neutral_comments)
                
                review = {
                    'review_id': f'review_{len(reviews)+1:05d}',
                    'product_id': product['product_id'],
                    'user_id': user['user_id'],
                    'rating': rating,
                    'comment': comment,
                    'helpful_count': random.randint(0, 50),
                    'verified_purchase': random.choice([True, False]),
                    'created_at': (datetime.now() - timedelta(days=random.randint(0, 60))).isoformat()
                }
                reviews.append(review)
        
        # Save to file
        output_file = self.output_dir / 'reviews.json'
        with open(output_file, 'w') as f:
            json.dump(reviews, f, indent=2)
        
        print(f"✅ Generated {len(reviews)} reviews → {output_file}")
        return reviews
    
    def generate_transactions_for_fraud(self, users, orders):
        """Generate transaction data for fraud detection testing"""
        print("\n🛡️  Generating fraud detection transactions...")
        transactions = []
        
        for order in orders:
            user = next((u for u in users if u['user_id'] == order['user_id']), None)
            if not user:
                continue
            
            # 95% legitimate, 5% potentially fraudulent
            is_suspicious = random.random() < 0.05
            
            transaction = {
                'transaction_id': f'tx_{order["order_id"]}',
                'user_id': order['user_id'],
                'amount': order['total_amount'],
                'currency': 'USD',
                'payment_method': order['payment_method'],
                'timestamp': order['order_date'],
                'device_info': {
                    'device_id': f'device_{random.randint(1000, 9999)}',
                    'ip_address': f'{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}',
                    'user_agent': random.choice(['Mozilla/5.0', 'Chrome/91.0', 'Safari/14.0']),
                    'is_vpn': is_suspicious and random.choice([True, False]),
                    'is_proxy': is_suspicious and random.choice([True, False])
                },
                'billing_country': user.get('address', {}).get('country', 'USA'),
                'shipping_country': user.get('address', {}).get('country', 'USA'),
                'is_first_purchase': random.choice([True, False]),
                'account_age_days': random.randint(1, 365),
                # Mark some as fraud for testing
                'is_fraud': is_suspicious
            }
            transactions.append(transaction)
        
        # Save to file
        output_file = self.output_dir / 'fraud_transactions.json'
        with open(output_file, 'w') as f:
            json.dump(transactions, f, indent=2)
        
        print(f"✅ Generated {len(transactions)} transactions ({sum(1 for t in transactions if t['is_fraud'])} flagged) → {output_file}")
        return transactions
    
    def generate_product_images(self, products):
        """Generate simple placeholder product images"""
        if not PIL_AVAILABLE:
            print("\n⚠️  Skipping image generation (Pillow not installed)")
            return
        
        print("\n🖼️  Generating product images...")
        
        images_dir = self.output_dir / 'product_images'
        images_dir.mkdir(exist_ok=True)
        
        # Generate images for first 20 products
        for product in products[:20]:
            # Create simple colored rectangle as product image
            img = Image.new('RGB', (400, 400), color=self._get_color_rgb(product['color']))
            draw = ImageDraw.Draw(img)
            
            # Add product name text
            text = product['name'][:30]  # Truncate long names
            # Use default font
            draw.text((20, 180), text, fill='white')
            
            # Save image
            image_path = images_dir / f"{product['product_id']}.jpg"
            img.save(image_path, 'JPEG')
        
        print(f"✅ Generated 20 sample product images → {images_dir}")
    
    def _get_color_rgb(self, color_name):
        """Convert color name to RGB tuple"""
        color_map = {
            'Red': (220, 20, 20),
            'Blue': (20, 20, 220),
            'Green': (20, 180, 20),
            'Black': (40, 40, 40),
            'White': (240, 240, 240),
            'Silver': (192, 192, 192),
            'Gold': (255, 215, 0),
            'Pink': (255, 192, 203),
            'Purple': (128, 0, 128),
            'Orange': (255, 165, 0)
        }
        return color_map.get(color_name, (128, 128, 128))
    
    def generate_all(self):
        """Generate all test data"""
        print("\n" + "="*60)
        print("🚀 SYNTHETIC DATA GENERATOR")
        print("="*60)
        print(f"📊 Configuration:")
        print(f"   Users: {self.num_users}")
        print(f"   Products: {self.num_products}")
        print(f"   Orders: {self.num_orders}")
        print("="*60)
        
        # Generate data
        users = self.generate_users()
        products = self.generate_products()
        orders = self.generate_orders(users, products)
        interactions = self.generate_interactions(users, products)
        reviews = self.generate_reviews(users, products)
        transactions = self.generate_transactions_for_fraud(users, orders)
        self.generate_product_images(products)
        
        # Generate summary
        summary = {
            'generated_at': datetime.now().isoformat(),
            'statistics': {
                'users': len(users),
                'products': len(products),
                'orders': len(orders),
                'interactions': len(interactions),
                'reviews': len(reviews),
                'transactions': len(transactions)
            },
            'files': {
                'users': 'test_data/users.json',
                'products': 'test_data/products.json',
                'orders': 'test_data/orders.json',
                'interactions': 'test_data/interactions.json',
                'reviews': 'test_data/reviews.json',
                'fraud_transactions': 'test_data/fraud_transactions.json',
                'images': 'test_data/product_images/'
            }
        }
        
        summary_file = self.output_dir / 'data_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("\n" + "="*60)
        print("✅ DATA GENERATION COMPLETE!")
        print("="*60)
        print(f"📁 Output directory: {self.output_dir.absolute()}")
        print(f"📄 Summary: {summary_file}")
        print("\n📊 Statistics:")
        for key, value in summary['statistics'].items():
            print(f"   {key.capitalize()}: {value:,}")
        print("="*60)
        
        return summary


if __name__ == "__main__":
    # Generate test data
    generator = SyntheticDataGenerator(
        num_users=100,
        num_products=500,
        num_orders=1000
    )
    
    summary = generator.generate_all()
    