from django.core.management.base import BaseCommand
from apps.core.cache_utils import CacheStats
import time


class Command(BaseCommand):
    help = 'Display Redis cache statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Continuously watch cache stats (refresh every 5 seconds)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Watch interval in seconds (default: 5)'
        )

    def handle(self, *args, **options):
        if options['watch']:
            self.watch_stats(options['interval'])
        else:
            self.show_stats()

    def show_stats(self):
        stats = CacheStats.get_stats()

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Redis Cache Statistics'))
        self.stdout.write('=' * 60)

        self.stdout.write(f"\nTotal Keys: {self.style.WARNING(str(stats.get('total_keys', 'N/A')))}")
        self.stdout.write(f"Memory Used: {stats.get('memory_used', 'N/A')}")

        self.stdout.write('\nHit/Miss Statistics:')
        self.stdout.write(f"  Hits: {stats.get('keyspace_hits', 0):,}")
        self.stdout.write(f"  Misses: {stats.get('keyspace_misses', 0):,}")

        hit_rate = stats.get('hit_rate', 0)
        if hit_rate >= 90:
            style = self.style.SUCCESS
        elif hit_rate >= 70:
            style = self.style.WARNING
        else:
            style = self.style.ERROR

        self.stdout.write(f"  Hit Rate: {style(f'{hit_rate:.2f}%')}")

        self.stdout.write(f"\n  Target Hit Rate: {self.style.WARNING('> 90%')}")

        if hit_rate < 90:
            self.stdout.write(
                self.style.WARNING(f"\nWarning: Hit rate is below target (Current: {hit_rate:.2f}%)")
            )
            self.stdout.write("Consider:")
            self.stdout.write("  1. Running: python manage.py warm_cache --all")
            self.stdout.write("  2. Increasing cache timeouts")
            self.stdout.write("  3. Adding more caching to frequently accessed endpoints")

        self.stdout.write('\n' + '=' * 60 + '\n')

    def watch_stats(self, interval):
        self.stdout.write(
            self.style.SUCCESS(f'Watching cache stats (refresh every {interval}s). Press Ctrl+C to stop.')
        )

        try:
            while True:
                self.stdout.write('\033[2J\033[H')

                self.show_stats()

                self.stdout.write(f"Refreshing in {interval} seconds...")

                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write('\n\nStopped watching cache stats.')
