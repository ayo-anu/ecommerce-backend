from django.core.management.base import BaseCommand
from django.core.cache import cache
from apps.products.models import Product, Category, ProductImage
from apps.orders.models import Order
from django.db.models import Prefetch
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Warm up application caches with frequently accessed data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--categories',
            action='store_true',
            help='Warm category cache'
        )
        parser.add_argument(
            '--products',
            action='store_true',
            help='Warm product cache'
        )
        parser.add_argument(
            '--featured',
            action='store_true',
            help='Warm featured products cache'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Warm all caches'
        )

    def handle(self, *args, **options):
        if options['all']:
            options['categories'] = True
            options['products'] = True
            options['featured'] = True

        if not any((options['categories'], options['products'], options['featured'])):
            self.stdout.write(
                self.style.WARNING('No cache warming options specified. Use --help for options.')
            )
            return

        self.stdout.write(self.style.SUCCESS('Starting cache warming...'))

        if options['categories']:
            self.warm_categories()

        if options['products']:
            self.warm_products()

        if options['featured']:
            self.warm_featured_products()

        self.stdout.write(self.style.SUCCESS('\nCache warming complete!'))

        self.show_cache_stats()

    def warm_categories(self):
        self.stdout.write('Warming category cache...')

        categories = list(
            Category.objects.filter(is_active=True)
            .prefetch_related('children')
        )

        for category in categories:
            cache_key = f'category:{category.id}'
            cache.set(cache_key, category, timeout=3600)

            cache_key_slug = f'category:slug:{category.slug}'
            cache.set(cache_key_slug, category, timeout=3600)

        self.stdout.write(
            self.style.SUCCESS(f'  Cached {len(categories)} categories')
        )

    def warm_products(self):
        self.stdout.write('Warming product cache...')

        products = list(
            Product.objects.filter(is_active=True)
            .select_related('category')
            .prefetch_related(
                Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True)),
                'variants',
                'tags'
            )
            .order_by('-created_at')[:100]
        )

        for product in products:
            cache_key = f'product_detail:{product.id}'
            cache.set(cache_key, product, timeout=900)

            cache_key_slug = f'product:slug:{product.slug}'
            cache.set(cache_key_slug, product, timeout=900)

        self.stdout.write(
            self.style.SUCCESS(f'  Cached {len(products)} products')
        )

    def warm_featured_products(self):
        self.stdout.write('Warming featured products cache...')

        featured_products = list(
            Product.objects.filter(is_featured=True, is_active=True)
            .select_related('category')
            .prefetch_related(
                Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
            )
            .only('id', 'name', 'slug', 'price', 'category__name')
        )

        cache_key = 'featured_products'
        cache.set(cache_key, featured_products, timeout=1800)

        self.stdout.write(
            self.style.SUCCESS(f'  Cached {len(featured_products)} featured products')
        )

    def show_cache_stats(self):
        try:
            from apps.core.cache_utils import CacheStats

            stats = CacheStats.get_stats()

            self.stdout.write('\n' + '=' * 50)
            self.stdout.write('Cache Statistics:')
            self.stdout.write(f"  Total Keys: {stats.get('total_keys', 'N/A')}")
            self.stdout.write(f"  Hit Rate: {stats.get('hit_rate', 0):.2f}%")
            self.stdout.write(f"  Memory Used: {stats.get('memory_used', 'N/A')}")
            self.stdout.write('=' * 50)

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not retrieve cache stats: {e}')
            )
