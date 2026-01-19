from django.test import override_settings
from django.db import connection, reset_queries
from functools import wraps


class AssertNumQueriesLessThan:

    def __init__(self, num):
        self.num = num

    def __enter__(self):
        reset_queries()
        self.starting_queries = len(connection.queries)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            return

        final_queries = len(connection.queries)
        executed = final_queries - self.starting_queries

        if executed >= self.num:
            query_info = '\n'.join(
                f"{i}: {q['sql'][:100]}..."
                for i, q in enumerate(connection.queries[self.starting_queries:], 1)
            )
            raise AssertionError(
                f"Expected less than {self.num} queries, but {executed} were executed.\n"
                f"Queries:\n{query_info}"
            )


def assert_no_n_plus_one(func):

    @wraps(func)
    @override_settings(DEBUG=True)
    def wrapper(*args, **kwargs):
        reset_queries()
        result = func(*args, **kwargs)

        queries = connection.queries
        query_patterns = {}

        for query in queries:
            sql = query['sql']
            normalized = sql.split('WHERE')[0] if 'WHERE' in sql else sql

            if normalized in query_patterns:
                query_patterns[normalized].append(sql)
            else:
                query_patterns[normalized] = [sql]

        n_plus_one_detected = {
            pattern: sqls
            for pattern, sqls in query_patterns.items()
            if len(sqls) > 2
        }

        if n_plus_one_detected:
            details = '\n'.join(
                f"Pattern repeated {len(sqls)} times:\n{pattern[:100]}..."
                for pattern, sqls in list(n_plus_one_detected.items())[:3]
            )
            raise AssertionError(
                f"Potential N+1 query detected!\n"
                f"Total queries: {len(queries)}\n"
                f"{details}"
            )

        return result

    return wrapper


def print_queries():
    for i, query in enumerate(connection.queries, 1):
        print(f"\n{i}. Time: {query['time']}s")
        print(f"   SQL: {query['sql'][:200]}...")


class QueryCounter:

    def __init__(self, description=""):
        self.description = description

    def __enter__(self):
        reset_queries()
        self.starting_queries = len(connection.queries)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            return

        final_queries = len(connection.queries)
        executed = final_queries - self.starting_queries

        print(f"\n{'='*60}")
        print(f"Query Count: {self.description}")
        print(f"Queries executed: {executed}")
        print(f"{'='*60}\n")

        for i, query in enumerate(connection.queries[self.starting_queries:], 1):
            print(f"{i}. {query['sql'][:150]}...")

        print()
