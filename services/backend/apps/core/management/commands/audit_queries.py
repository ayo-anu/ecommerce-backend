import json
import logging

from django.core.management.base import BaseCommand
from django.test import RequestFactory, override_settings
from django.db import connection, reset_queries
from django.contrib.auth import get_user_model
from apps.products.views import ProductViewSet, CategoryViewSet
from apps.orders.views import OrderViewSet, CartViewSet
from apps.accounts.views import UserViewSet

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = 'Audit database queries for all API endpoints'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=10,
            help='Query count threshold to flag as potential N+1 issue'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='console',
            choices=['console', 'json'],
            help='Output format'
        )

    @override_settings(DEBUG=True)
    def handle(self, *args, **options):
        threshold = options['threshold']
        output_format = options['output']

        factory = RequestFactory()
        results = []

        user, _ = User.objects.get_or_create(
            username='test_audit',
            defaults={'email': 'test@example.com'}
        )

        endpoints = [
            {
                'name': 'Product List',
                'viewset': ProductViewSet,
                'action': 'list',
                'path': '/api/v1/products/',
            },
            {
                'name': 'Product Detail',
                'viewset': ProductViewSet,
                'action': 'retrieve',
                'path': '/api/v1/products/1/',
            },
            {
                'name': 'Product Search',
                'viewset': ProductViewSet,
                'action': 'search',
                'path': '/api/v1/products/search/?q=laptop',
            },
            {
                'name': 'Category List',
                'viewset': CategoryViewSet,
                'action': 'list',
                'path': '/api/v1/categories/',
            },
            {
                'name': 'Order List',
                'viewset': OrderViewSet,
                'action': 'list',
                'path': '/api/v1/orders/',
            },
            {
                'name': 'Order Detail',
                'viewset': OrderViewSet,
                'action': 'retrieve',
                'path': '/api/v1/orders/1/',
            },
            {
                'name': 'Cart',
                'viewset': CartViewSet,
                'action': 'list',
                'path': '/api/v1/cart/',
            },
            {
                'name': 'User Profile',
                'viewset': UserViewSet,
                'action': 'me',
                'path': '/api/v1/users/me/',
            },
        ]

        for endpoint in endpoints:
            reset_queries()

            try:
                request = factory.get(endpoint['path'])
                request.user = user

                viewset = endpoint['viewset']()
                viewset.request = request
                viewset.format_kwarg = None
                viewset.action = endpoint['action']

                if endpoint['action'] == 'list':
                    viewset.list(request)
                elif endpoint['action'] == 'retrieve':
                    try:
                        viewset.retrieve(request, pk=1)
                    except Exception as exc:
                        logger.debug("Retrieve failed for %s: %s", endpoint['path'], exc)
                elif endpoint['action'] == 'search':
                    viewset.search(request)
                elif endpoint['action'] == 'me':
                    viewset.me(request)

                query_count = len(connection.queries)

                similar_queries = self.find_similar_queries(connection.queries)

                result = {
                    'endpoint': endpoint['name'],
                    'path': endpoint['path'],
                    'query_count': query_count,
                    'status': 'GOOD' if query_count < threshold else 'NEEDS_OPTIMIZATION',
                    'similar_queries': similar_queries,
                }

                results.append(result)

            except Exception as e:
                results.append({
                    'endpoint': endpoint['name'],
                    'path': endpoint['path'],
                    'error': str(e),
                    'status': 'ERROR'
                })

        if output_format == 'json':
            self.stdout.write(json.dumps(results, indent=2))
        else:
            self.print_console_output(results, threshold)

    def find_similar_queries(self, queries):
        query_patterns = {}

        for query in queries:
            sql = query['sql']
            normalized = sql.split('WHERE')[0] if 'WHERE' in sql else sql
            normalized = normalized.split('LIMIT')[0] if 'LIMIT' in sql else normalized

            if normalized in query_patterns:
                query_patterns[normalized] += 1
            else:
                query_patterns[normalized] = 1

        return {
            pattern: count
            for pattern, count in query_patterns.items()
            if count > 1
        }

    def print_console_output(self, results, threshold):
        self.stdout.write(self.style.SUCCESS('\n=== Database Query Audit ===\n'))

        total_queries = 0
        needs_optimization = 0

        for result in results:
            if 'error' in result:
                self.stdout.write(
                    self.style.ERROR(f"\n{result['endpoint']}: {result['error']}")
                )
                continue

            query_count = result['query_count']
            total_queries += query_count

            if result['status'] == 'NEEDS_OPTIMIZATION':
                needs_optimization += 1
                style = self.style.WARNING
            else:
                style = self.style.SUCCESS

            self.stdout.write(
                style(f"\n{result['endpoint']}: {query_count} queries ({result['status']})")
            )
            self.stdout.write(f"  Path: {result['path']}")

            if result['similar_queries']:
                self.stdout.write(self.style.WARNING("  Potential N+1 detected:"))
                for pattern, count in list(result['similar_queries'].items())[:2]:
                    self.stdout.write(f"    - {count} similar queries")

        self.stdout.write(self.style.SUCCESS(f'\n\n=== Summary ==='))
        self.stdout.write(f'Total endpoints audited: {len(results)}')
        self.stdout.write(f'Total queries executed: {total_queries}')
        self.stdout.write(f'Average queries per endpoint: {total_queries / len(results):.1f}')
        self.stdout.write(
            self.style.WARNING(f'Endpoints needing optimization: {needs_optimization}')
            if needs_optimization > 0
            else self.style.SUCCESS('All endpoints optimized!')
        )
        self.stdout.write('\n')
