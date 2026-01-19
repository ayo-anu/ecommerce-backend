from django.core.management.base import BaseCommand
from apps.products.models import Product
from apps.products.documents import ProductDocument


class Command(BaseCommand):
    help = 'Index all products in Elasticsearch'
    
    def handle(self, *args, **kwargs):
        self.stdout.write('Indexing products...')
        
        ProductDocument().update(Product.objects.all())
        
        count = Product.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'Successfully indexed {count} products')
        )
