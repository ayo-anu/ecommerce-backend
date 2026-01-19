from django.core.cache import cache
from django.conf import settings
from functools import wraps
import hashlib
import json
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)


def make_cache_key(*args, prefix: str = '', **kwargs) -> str:
    key_parts = [prefix] if prefix else []

    key_parts.extend(str(arg) for arg in args)

    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")

    key = ':'.join(key_parts)

    if len(key) > 200:
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    return key


def make_query_cache_key(queryset) -> str:
    return hashlib.md5(str(queryset.query).encode()).hexdigest()


def cache_result(timeout: int = 300, key_prefix: str = ''):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = make_cache_key(
                *args,
                prefix=key_prefix or func.__name__,
                **kwargs
            )

            result = cache.get(cache_key)

            if result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return result

            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)

            cache.set(cache_key, result, timeout)

            return result

        def invalidate(*args, **kwargs):
            cache_key = make_cache_key(
                *args,
                prefix=key_prefix or func.__name__,
                **kwargs
            )
            cache.delete(cache_key)
            logger.info(f"Cache invalidated: {cache_key}")

        wrapper.invalidate = invalidate

        return wrapper

    return decorator


def cache_queryset(timeout: int = 300, key_prefix: str = ''):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            queryset = func(*args, **kwargs)

            query_hash = make_query_cache_key(queryset)
            cache_key = f"{key_prefix or func.__name__}:{query_hash}"

            cached_ids = cache.get(cache_key)

            if cached_ids is not None:
                logger.debug(f"Queryset cache HIT: {cache_key}")
                model = queryset.model
                return model.objects.filter(id__in=cached_ids)

            logger.debug(f"Queryset cache MISS: {cache_key}")
            result_list = list(queryset)
            result_ids = [obj.id for obj in result_list]

            cache.set(cache_key, result_ids, timeout)

            return queryset

        return wrapper

    return decorator


class CachedAttribute:

    def __init__(self, instance, attr_name: str, func: Callable, timeout: int = 300):
        self.instance = instance
        self.attr_name = attr_name
        self.func = func
        self.timeout = timeout

    @property
    def value(self):
        cache_key = f"{self.instance.__class__.__name__}:{self.instance.pk}:{self.attr_name}"

        cached_value = cache.get(cache_key)

        if cached_value is not None:
            return cached_value

        value = self.func()
        cache.set(cache_key, value, self.timeout)

        return value

    def invalidate(self):
        cache_key = f"{self.instance.__class__.__name__}:{self.instance.pk}:{self.attr_name}"
        cache.delete(cache_key)


class CachePattern:

    @staticmethod
    def cache_list_view(queryset, timeout: int = 300, filters: dict = None):
        filter_str = json.dumps(filters or {}, sort_keys=True)
        cache_key = f"list:{queryset.model.__name__}:{hashlib.md5(filter_str.encode()).hexdigest()}"

        cached_ids = cache.get(cache_key)

        if cached_ids is not None:
            return queryset.model.objects.filter(id__in=cached_ids)

        result_list = list(queryset)
        result_ids = [obj.id for obj in result_list]

        cache.set(cache_key, result_ids, timeout)

        return result_list

    @staticmethod
    def cache_detail_view(model_class, pk, timeout: int = 900):
        cache_key = f"detail:{model_class.__name__}:{pk}"

        cached_obj = cache.get(cache_key)

        if cached_obj is not None:
            return cached_obj

        obj = model_class.objects.get(pk=pk)
        cache.set(cache_key, obj, timeout)

        return obj

    @staticmethod
    def cache_count(queryset, timeout: int = 600):
        query_hash = make_query_cache_key(queryset)
        cache_key = f"count:{query_hash}"

        cached_count = cache.get(cache_key)

        if cached_count is not None:
            return cached_count

        count = queryset.count()
        cache.set(cache_key, count, timeout)

        return count


class CacheInvalidator:

    @staticmethod
    def invalidate_by_prefix(prefix: str):
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection("default")

            cursor = 0
            pattern = f"*{prefix}*"

            while True:
                cursor, keys = conn.scan(cursor, match=pattern, count=100)

                if keys:
                    conn.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} keys with prefix: {prefix}")

                if cursor == 0:
                    break

        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")

    @staticmethod
    def invalidate_model(model_instance):
        prefix = f"{model_instance.__class__.__name__}:{model_instance.pk}"
        CacheInvalidator.invalidate_by_prefix(prefix)

    @staticmethod
    def invalidate_list_cache(model_class):
        prefix = f"list:{model_class.__name__}"
        CacheInvalidator.invalidate_by_prefix(prefix)


def warm_cache(cache_func: Callable, *args, **kwargs):
    try:
        result = cache_func(*args, **kwargs)
        logger.info(f"Cache warmed for {cache_func.__name__}")
        return result
    except Exception as e:
        logger.error(f"Cache warming failed for {cache_func.__name__}: {e}")
        return None


class CacheStats:

    @staticmethod
    def get_stats() -> dict:
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection("default")

            info = conn.info("stats")

            return {
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': CacheStats.calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                ),
                'total_keys': conn.dbsize(),
                'memory_used': info.get('used_memory_human', 'N/A'),
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

    @staticmethod
    def calculate_hit_rate(hits: int, misses: int) -> float:
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100
