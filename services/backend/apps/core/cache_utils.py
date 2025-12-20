"""
Caching utilities for the e-commerce platform.
Provides decorators, helpers, and patterns for efficient caching.
"""
from django.core.cache import cache
from django.conf import settings
from functools import wraps
import hashlib
import json
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)


# Cache key generators
def make_cache_key(*args, prefix: str = '', **kwargs) -> str:
    """
    Generate a cache key from arguments.

    Args:
        *args: Positional arguments to include in key
        prefix: Key prefix (e.g., 'product', 'user')
        **kwargs: Keyword arguments to include in key

    Returns:
        A unique cache key string
    """
    key_parts = [prefix] if prefix else []

    # Add positional arguments
    key_parts.extend(str(arg) for arg in args)

    # Add sorted keyword arguments
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")

    # Join and hash if too long
    key = ':'.join(key_parts)

    if len(key) > 200:  # Redis key length limit
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    return key


def make_query_cache_key(queryset) -> str:
    """
    Generate cache key for a Django queryset.

    Args:
        queryset: Django QuerySet object

    Returns:
        Cache key based on query SQL
    """
    return hashlib.md5(str(queryset.query).encode()).hexdigest()


# Decorators
def cache_result(timeout: int = 300, key_prefix: str = ''):
    """
    Decorator to cache function results.

    Usage:
        @cache_result(timeout=600, key_prefix='user_profile')
        def get_user_profile(user_id):
            return User.objects.get(id=user_id)

    Args:
        timeout: Cache timeout in seconds (default 5 minutes)
        key_prefix: Prefix for cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = make_cache_key(
                *args,
                prefix=key_prefix or func.__name__,
                **kwargs
            )

            # Try to get from cache
            result = cache.get(cache_key)

            if result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return result

            # Cache miss - execute function
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, timeout)

            return result

        # Add cache invalidation method
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
    """
    Decorator to cache queryset results.

    Usage:
        @cache_queryset(timeout=600, key_prefix='products')
        def get_featured_products():
            return Product.objects.filter(is_featured=True)

    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute function to get queryset
            queryset = func(*args, **kwargs)

            # Generate cache key from query
            query_hash = make_query_cache_key(queryset)
            cache_key = f"{key_prefix or func.__name__}:{query_hash}"

            # Try to get from cache
            cached_ids = cache.get(cache_key)

            if cached_ids is not None:
                logger.debug(f"Queryset cache HIT: {cache_key}")
                # Return queryset filtered by cached IDs
                model = queryset.model
                return model.objects.filter(id__in=cached_ids)

            # Cache miss - evaluate queryset
            logger.debug(f"Queryset cache MISS: {cache_key}")
            result_list = list(queryset)
            result_ids = [obj.id for obj in result_list]

            # Cache the IDs
            cache.set(cache_key, result_ids, timeout)

            return queryset

        return wrapper

    return decorator


# Context managers
class CachedAttribute:
    """
    Cache an attribute on an instance.

    Usage:
        class Product(models.Model):
            @property
            def related_products(self):
                return CachedAttribute(
                    instance=self,
                    attr_name='related_products',
                    func=self._get_related_products,
                    timeout=3600
                ).value

            def _get_related_products(self):
                # Expensive computation
                return Product.objects.filter(category=self.category).exclude(id=self.id)[:5]
    """

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


# Cache patterns
class CachePattern:
    """
    Predefined caching patterns for common scenarios.
    """

    @staticmethod
    def cache_list_view(queryset, timeout: int = 300, filters: dict = None):
        """
        Cache results of a list view.

        Args:
            queryset: Django queryset
            timeout: Cache timeout
            filters: Additional filters to include in cache key

        Returns:
            Cached or fresh queryset results
        """
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
        """
        Cache a detail view object.

        Args:
            model_class: Django model class
            pk: Primary key
            timeout: Cache timeout (default 15 minutes)

        Returns:
            Cached or fresh object
        """
        cache_key = f"detail:{model_class.__name__}:{pk}"

        cached_obj = cache.get(cache_key)

        if cached_obj is not None:
            return cached_obj

        obj = model_class.objects.get(pk=pk)
        cache.set(cache_key, obj, timeout)

        return obj

    @staticmethod
    def cache_count(queryset, timeout: int = 600):
        """
        Cache queryset count.

        Args:
            queryset: Django queryset
            timeout: Cache timeout

        Returns:
            Cached or fresh count
        """
        query_hash = make_query_cache_key(queryset)
        cache_key = f"count:{query_hash}"

        cached_count = cache.get(cache_key)

        if cached_count is not None:
            return cached_count

        count = queryset.count()
        cache.set(cache_key, count, timeout)

        return count


# Cache invalidation helpers
class CacheInvalidator:
    """
    Helpers for cache invalidation.
    """

    @staticmethod
    def invalidate_by_prefix(prefix: str):
        """
        Invalidate all cache keys with a given prefix.

        Note: This requires django-redis and uses SCAN for efficiency.

        Args:
            prefix: Cache key prefix to invalidate
        """
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection("default")

            # Use SCAN to find keys (more efficient than KEYS)
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
        """
        Invalidate all cache entries for a model instance.

        Args:
            model_instance: Django model instance
        """
        prefix = f"{model_instance.__class__.__name__}:{model_instance.pk}"
        CacheInvalidator.invalidate_by_prefix(prefix)

    @staticmethod
    def invalidate_list_cache(model_class):
        """
        Invalidate list view caches for a model.

        Args:
            model_class: Django model class
        """
        prefix = f"list:{model_class.__name__}"
        CacheInvalidator.invalidate_by_prefix(prefix)


# Cache warming
def warm_cache(cache_func: Callable, *args, **kwargs):
    """
    Warm cache by pre-computing and caching a result.

    Usage:
        warm_cache(get_featured_products)
        warm_cache(get_user_profile, user_id=123)

    Args:
        cache_func: Function decorated with @cache_result
        *args: Arguments to pass to function
        **kwargs: Keyword arguments to pass to function
    """
    try:
        result = cache_func(*args, **kwargs)
        logger.info(f"Cache warmed for {cache_func.__name__}")
        return result
    except Exception as e:
        logger.error(f"Cache warming failed for {cache_func.__name__}: {e}")
        return None


# Cache statistics
class CacheStats:
    """
    Get cache statistics from Redis.
    """

    @staticmethod
    def get_stats() -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
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
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100
