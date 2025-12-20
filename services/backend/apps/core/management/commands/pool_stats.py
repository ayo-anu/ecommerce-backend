"""
Management command to monitor database connection pool statistics.
Usage: python manage.py pool_stats [--watch]
"""
from django.core.management.base import BaseCommand
from django.db import connection
import time
import psycopg2


class Command(BaseCommand):
    help = 'Display database connection pool statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Continuously watch pool stats (refresh every 5 seconds)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Watch interval in seconds (default: 5)'
        )
        parser.add_argument(
            '--pgbouncer',
            action='store_true',
            help='Show PgBouncer stats (requires connection to PgBouncer admin)'
        )

    def handle(self, *args, **options):
        if options['watch']:
            self.watch_stats(options['interval'], options['pgbouncer'])
        else:
            self.show_stats(options['pgbouncer'])

    def show_stats(self, show_pgbouncer=False):
        """Display connection pool statistics"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('Database Connection Pool Statistics'))
        self.stdout.write('=' * 70)

        # PostgreSQL connection stats
        self.show_postgres_stats()

        # PgBouncer stats if requested
        if show_pgbouncer:
            self.stdout.write('\n')
            self.show_pgbouncer_stats()

        self.stdout.write('\n' + '=' * 70 + '\n')

    def show_postgres_stats(self):
        """Show PostgreSQL connection statistics"""
        try:
            with connection.cursor() as cursor:
                # Total connections
                cursor.execute("""
                    SELECT count(*) as total_connections
                    FROM pg_stat_activity
                """)
                total_conn = cursor.fetchone()[0]

                # Active connections
                cursor.execute("""
                    SELECT count(*) as active_connections
                    FROM pg_stat_activity
                    WHERE state = 'active'
                """)
                active_conn = cursor.fetchone()[0]

                # Idle connections
                cursor.execute("""
                    SELECT count(*) as idle_connections
                    FROM pg_stat_activity
                    WHERE state = 'idle'
                """)
                idle_conn = cursor.fetchone()[0]

                # Max connections
                cursor.execute("""
                    SELECT setting::int as max_connections
                    FROM pg_settings
                    WHERE name = 'max_connections'
                """)
                max_conn = cursor.fetchone()[0]

                # Connection by state
                cursor.execute("""
                    SELECT state, count(*) as count
                    FROM pg_stat_activity
                    WHERE state IS NOT NULL
                    GROUP BY state
                    ORDER BY count DESC
                """)
                conn_by_state = cursor.fetchall()

                # Display stats
                self.stdout.write('\nPostgreSQL Connections:')
                self.stdout.write(f"  Total: {total_conn} / {max_conn} ({total_conn/max_conn*100:.1f}%)")
                self.stdout.write(f"  Active: {self.style.WARNING(str(active_conn))}")
                self.stdout.write(f"  Idle: {idle_conn}")

                utilization = (total_conn / max_conn) * 100
                if utilization > 80:
                    self.stdout.write(
                        self.style.ERROR(f"  Utilization: {utilization:.1f}% (HIGH - Consider increasing max_connections)")
                    )
                elif utilization > 60:
                    self.stdout.write(
                        self.style.WARNING(f"  Utilization: {utilization:.1f}% (MODERATE)")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"  Utilization: {utilization:.1f}% (GOOD)")
                    )

                self.stdout.write('\nConnections by state:')
                for state, count in conn_by_state:
                    self.stdout.write(f"  {state}: {count}")

                # Long running queries
                cursor.execute("""
                    SELECT pid, now() - query_start as duration, state, LEFT(query, 50) as query
                    FROM pg_stat_activity
                    WHERE state = 'active'
                      AND query NOT LIKE '%pg_stat_activity%'
                    ORDER BY duration DESC
                    LIMIT 5
                """)
                long_queries = cursor.fetchall()

                if long_queries:
                    self.stdout.write('\nLong running queries:')
                    for pid, duration, state, query in long_queries:
                        self.stdout.write(f"  PID {pid}: {duration} - {query}...")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching PostgreSQL stats: {e}'))

    def show_pgbouncer_stats(self):
        """Show PgBouncer statistics"""
        try:
            # Connect to PgBouncer admin console
            # Note: This requires PgBouncer to be configured with admin access
            import os
            pgb_host = os.getenv('PGBOUNCER_HOST', 'localhost')
            pgb_port = os.getenv('PGBOUNCER_PORT', '6432')

            conn = psycopg2.connect(
                host=pgb_host,
                port=pgb_port,
                user='postgres',
                password=os.getenv('POSTGRES_PASSWORD', ''),
                database='pgbouncer'
            )

            cursor = conn.cursor()

            # Pool statistics
            cursor.execute('SHOW POOLS')
            pools = cursor.fetchall()

            self.stdout.write('PgBouncer Pools:')
            self.stdout.write(
                f"  {'Database':<20} {'User':<15} {'Active':<8} {'Waiting':<8} {'MaxWait':<8}"
            )
            self.stdout.write('  ' + '-' * 65)

            for row in pools:
                database, user, cl_active, cl_waiting, sv_active, sv_idle, sv_used, sv_tested, sv_login, maxwait, pool_mode = row[:11]
                self.stdout.write(
                    f"  {database:<20} {user:<15} {cl_active:<8} {cl_waiting:<8} {maxwait:<8}"
                )

            # Stats
            cursor.execute('SHOW STATS')
            stats = cursor.fetchall()

            self.stdout.write('\nPgBouncer Stats:')
            for row in stats[:5]:  # Show top 5
                database = row[0]
                total_xact_count = row[1]
                total_query_count = row[2]
                self.stdout.write(
                    f"  {database}: {total_xact_count} transactions, {total_query_count} queries"
                )

            cursor.close()
            conn.close()

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not fetch PgBouncer stats: {e}')
            )
            self.stdout.write(
                'Tip: Ensure PgBouncer is running and admin access is configured'
            )

    def watch_stats(self, interval, show_pgbouncer=False):
        """Watch connection pool statistics in real-time"""
        self.stdout.write(
            self.style.SUCCESS(f'Watching pool stats (refresh every {interval}s). Press Ctrl+C to stop.')
        )

        try:
            while True:
                # Clear screen (works on Unix-like systems)
                self.stdout.write('\033[2J\033[H')

                self.show_stats(show_pgbouncer)

                self.stdout.write(f"Refreshing in {interval} seconds...")

                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write('\n\nStopped watching pool stats.')
