# Redis Caching Strategy

**Last Updated:** 2025-12-20
**Owner:** Backend Team
**Target Hit Rate:** > 90%

---

## Table of Contents

1. [Overview](#overview)
2. [Cache Configuration](#cache-configuration)
3. [Caching Patterns](#caching-patterns)
4. [Cache Invalidation](#cache-invalidation)
5. [Cache Warming](#cache-warming)
6. [Monitoring](#monitoring)
7. [Best Practices](#best-practices)

---

## Overview

This document describes the Redis caching strategy used to achieve >90% cache hit rate and minimize database queries.

### Cache TTL Guidelines

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Product List | 5 min | Frequently updated, balance freshness |
| Product Detail | 15 min | Less frequent changes |
| Category Data | 1 hour | Rarely changes |
| User Session | 30 min | Security balance |
| Search Results | 10 min | Dynamic content |
| AI Recommendations | 1 hour | Expensive to compute |
| Cart Data | 30 min | User-specific, moderate freshness |

---

## Cache Configuration

### Production Settings

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'ecommerce',
        'TIMEOUT': 300,  # Default 5 minutes
    }
}
```

---

## Caching Patterns

### Pattern 1: Function Result Caching

Cache expensive function results:

```python
from apps.core.cache_utils import cache_result

@cache_result(timeout=600, key_prefix='user_profile')
def get_user_profile(user_id):
    return User.objects.select_related('profile').get(id=user_id)

# Invalidate when user updates profile
user.save()
get_user_profile.invalidate(user.id)
```

### Pattern 2: Queryset Caching

Cache queryset results:

```python
from apps.core.cache_utils import cache_queryset

@cache_queryset(timeout=600, key_prefix='featured_products')
def get_featured_products():
    return Product.objects.filter(is_featured=True).select_related('category')
```

### Pattern 3: View-Level Caching

Cache entire view responses:

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # 5 minutes
def product_list(request):
    products = Product.objects.all()
    return render(request, 'products/list.html', {'products': products})
```

### Pattern 4: Template Fragment Caching

Cache expensive template fragments:

```django
{% load cache %}

{% cache 600 product_recommendations product.id %}
  <!-- Expensive recommendation logic -->
  {% for rec in product.get_recommendations %}
    ...
  {% endfor %}
{% endcache %}
```

### Pattern 5: Instance Attribute Caching

Cache expensive computed properties:

```python
from apps.core.cache_utils import CachedAttribute

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
        return Product.objects.filter(
            category=self.category
        ).exclude(id=self.id)[:5]
```

### Pattern 6: List View Caching

Cache paginated list views:

```python
from apps.core.cache_utils import CachePattern

def get_product_list(filters=None):
    queryset = Product.objects.filter(is_active=True)

    if filters:
        queryset = queryset.filter(**filters)

    return CachePattern.cache_list_view(
        queryset,
        timeout=300,
        filters=filters
    )
```

---

## Cache Invalidation

### Strategy 1: Time-Based Invalidation (TTL)

Simplest approach - let cache expire:

```python
cache.set('product:123', product, timeout=900)  # 15 minutes
```

### Strategy 2: Manual Invalidation

Invalidate on updates:

```python
from apps.core.cache_utils import CacheInvalidator

# When product is updated
def update_product(product_id, data):
    product = Product.objects.get(id=product_id)
    product.name = data['name']
    product.save()

    # Invalidate caches
    CacheInvalidator.invalidate_model(product)
    CacheInvalidator.invalidate_list_cache(Product)
```

### Strategy 3: Signal-Based Invalidation

Auto-invalidate on model changes:

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Product)
def invalidate_product_cache(sender, instance, **kwargs):
    cache.delete(f'product_detail:{instance.id}')
    cache.delete(f'product:slug:{instance.slug}')

    # Invalidate list caches
    CacheInvalidator.invalidate_list_cache(Product)
```

### Strategy 4: Prefix-Based Invalidation

Invalidate all keys with a prefix:

```python
# Invalidate all product-related caches
CacheInvalidator.invalidate_by_prefix('product')
```

---

## Cache Warming

### On Deployment

Warm cache after deployment:

```bash
# In deployment script
python manage.py warm_cache --all
```

### Scheduled Warming

Use Celery for periodic cache warming:

```python
from celery import shared_task

@shared_task
def warm_popular_caches():
    """Warm caches for popular data"""
    # Featured products
    featured = Product.objects.filter(is_featured=True)
    cache.set('featured_products', list(featured), timeout=1800)

    # Categories
    categories = Category.objects.filter(is_active=True)
    cache.set('active_categories', list(categories), timeout=3600)

# Schedule in celery beat
CELERY_BEAT_SCHEDULE = {
    'warm-cache-every-hour': {
        'task': 'apps.products.tasks.warm_popular_caches',
        'schedule': crontab(minute=0),  # Every hour
    },
}
```

### Manual Warming

```bash
# Warm specific caches
python manage.py warm_cache --products
python manage.py warm_cache --categories
python manage.py warm_cache --featured

# Warm all caches
python manage.py warm_cache --all
```

---

## Monitoring

### View Cache Statistics

```bash
# One-time stats
python manage.py cache_stats

# Watch continuously
python manage.py cache_stats --watch

# Custom refresh interval
python manage.py cache_stats --watch --interval 10
```

### Grafana Metrics

Monitor cache performance:

```promql
# Cache hit rate
(
  rate(redis_keyspace_hits_total[5m])
  /
  (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))
) * 100

# Cache memory usage
redis_memory_used_bytes / redis_memory_max_bytes * 100

# Total keys
redis_db_keys

# Commands per second
rate(redis_commands_processed_total[5m])
```

### Application Metrics

Track cache hits in code:

```python
import logging
logger = logging.getLogger('cache')

result = cache.get(cache_key)
if result:
    logger.info(f'Cache HIT: {cache_key}')
else:
    logger.info(f'Cache MISS: {cache_key}')
```

---

## Best Practices

### DO

1. **Cache expensive operations**
   - Database queries
   - API calls
   - Complex computations
   - Template rendering

2. **Use appropriate TTLs**
   - Frequently changing data: 5-15 min
   - Moderate changes: 30-60 min
   - Rarely changing: 1-24 hours

3. **Invalidate on updates**
   ```python
   product.save()
   cache.delete(f'product:{product.id}')
   ```

4. **Use cache key prefixes**
   ```python
   cache.set('product:123', data)  # Not just '123'
   ```

5. **Warm cache after deployment**
   ```bash
   python manage.py warm_cache --all
   ```

6. **Monitor hit rate**
   - Target: >90%
   - Acceptable: >70%
   - Poor: <70%

7. **Handle cache misses gracefully**
   ```python
   data = cache.get(key)
   if data is None:
       data = expensive_operation()
       cache.set(key, data, timeout=600)
   ```

### DON'T

1. **Don't cache user-specific data in shared cache**
   ```python
   # BAD: Shared cache for user data
   cache.set('cart', user.cart)

   # GOOD: User-specific key
   cache.set(f'cart:user:{user.id}', user.cart)
   ```

2. **Don't cache everything**
   - Avoid caching rapidly changing data
   - Don't cache one-time queries
   - Skip caching admin-only views

3. **Don't forget to invalidate**
   ```python
   # BAD: Update without invalidation
   product.name = "New Name"
   product.save()

   # GOOD: Invalidate after update
   product.save()
   cache.delete(f'product:{product.id}')
   ```

4. **Don't use overly long TTLs**
   - Risk serving stale data
   - Wastes cache memory
   - Makes debugging harder

5. **Don't cache errors**
   ```python
   try:
       data = expensive_operation()
       cache.set(key, data, timeout=600)
   except Exception:
       # Don't cache None or errors
       pass
   ```

---

## Cache Key Naming Convention

Follow consistent naming:

```
{model}:{id}                    # Detail view: product:123
{model}:slug:{slug}             # By slug: product:slug:laptop
{model}:list:{filter_hash}      # List view: product:list:abc123
{model}:{id}:{attr}             # Attribute: product:123:related
{action}:{model}:{params}       # Action: search:product:laptop
```

Examples:
```
product:123
product:slug:macbook-pro
product:list:featured
user:456:profile
cart:user:789
search:product:laptop
category:electronics:products
```

---

## Troubleshooting

### Low Hit Rate (<70%)

**Causes:**
- TTLs too short
- Cache not warmed
- High cache invalidation rate
- Keys not reused

**Solutions:**
1. Increase TTLs for stable data
2. Run `python manage.py warm_cache --all`
3. Review invalidation logic
4. Check cache key consistency

### High Memory Usage

**Causes:**
- Caching large objects
- Too many keys
- TTLs too long

**Solutions:**
1. Cache only necessary fields
2. Implement cache eviction
3. Reduce TTLs
4. Use Redis maxmemory policy

### Cache Miss Storm

**Cause:** Cache expires under high load, causing DB overload

**Solution:** Use cache stampede prevention:

```python
import random

# Add jitter to TTL
ttl = 300 + random.randint(0, 60)  # 5-6 minutes
cache.set(key, value, timeout=ttl)
```

---

## References

- [Django Caching Framework](https://docs.djangoproject.com/en/4.2/topics/cache/)
- [django-redis Documentation](https://github.com/jazzband/django-redis)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)

---

**Document Owner:** Backend Team
**Review Schedule:** Quarterly
**Version:** 1.0
**Last Reviewed:** 2025-12-20
