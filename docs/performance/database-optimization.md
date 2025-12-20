# Database Query Optimization Guide

**Last Updated:** 2025-12-20
**Owner:** Backend Team

---

## Table of Contents

1. [Overview](#overview)
2. [Current Optimization Status](#current-optimization-status)
3. [Optimization Patterns](#optimization-patterns)
4. [Testing for N+1 Queries](#testing-for-n1-queries)
5. [Monitoring](#monitoring)
6. [Best Practices](#best-practices)

---

## Overview

This document describes the database query optimization strategies used in the e-commerce platform to eliminate N+1 queries and minimize database round-trips.

### Key Metrics

| Metric | Target | Current Status |
|--------|--------|----------------|
| N+1 Queries | 0 | 0 detected |
| Avg Queries per List Endpoint | < 5 | 2-4 queries |
| Avg Queries per Detail Endpoint | < 10 | 3-7 queries |
| P95 Query Time | < 50ms | < 30ms |

---

## Current Optimization Status

### Products App - OPTIMIZED

**ProductViewSet:**
```python
def get_queryset(self):
    if self.action == 'list':
        return Product.objects.filter(is_active=True).select_related(
            'category'
        ).prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
        ).only(
            'id', 'name', 'slug', 'price', 'category__name'
        )
    else:
        return Product.objects.select_related(
            'category'
        ).prefetch_related(
            'images', 'variants', 'tags'
        )
```

**Optimizations:**
- `select_related('category')` - Avoids extra query for category
- `prefetch_related('images')` - Single query for all images
- `only()` - Reduces data transfer for list views
- Separate querysets for list vs detail actions

**Query Count:**
- List: 2 queries (products + images)
- Detail: 4 queries (product + category + images + variants + tags)

### Orders App - OPTIMIZED

**OrderViewSet:**
```python
def get_queryset(self):
    return Order.objects.select_related('user').prefetch_related(
        'items__product',
        'items__variant'
    )
```

**CartViewSet:**
```python
def get_queryset(self):
    return Cart.objects.filter(user=self.request.user).prefetch_related(
        Prefetch(
            'items',
            queryset=CartItem.objects.select_related('product', 'variant')
        ),
        Prefetch(
            'items__product__images',
            queryset=ProductImage.objects.filter(is_primary=True)
        )
    )
```

**Optimizations:**
- Nested `prefetch_related` for order items and products
- `Prefetch()` objects for filtered querysets
- Combined `select_related` and `prefetch_related`

**Query Count:**
- Order List: 3 queries (orders + items + products)
- Cart: 3 queries (cart + items with products + images)

### Accounts App - OPTIMIZED

**UserViewSet:**
```python
def get_queryset(self):
    return User.objects.filter(id=self.request.user.id).select_related('profile')
```

**Optimizations:**
- `select_related('profile')` - Single query for user + profile

**Query Count:**
- User Profile: 1 query

---

## Optimization Patterns

### Pattern 1: Use `select_related()` for ForeignKey and OneToOne

**When to use:** Accessing related objects via ForeignKey or OneToOneField

**Example:**
```python
# BAD: N+1 queries
products = Product.objects.all()
for product in products:
    print(product.category.name)  # Triggers a query for each product

# GOOD: Single JOIN query
products = Product.objects.select_related('category')
for product in products:
    print(product.category.name)  # No additional query
```

**SQL Generated:**
```sql
-- With select_related('category')
SELECT * FROM products
INNER JOIN categories ON products.category_id = categories.id
```

### Pattern 2: Use `prefetch_related()` for ManyToMany and Reverse ForeignKey

**When to use:** Accessing multiple related objects

**Example:**
```python
# BAD: N+1 queries
products = Product.objects.all()
for product in products:
    for image in product.images.all():  # Query for each product
        print(image.url)

# GOOD: 2 queries total
products = Product.objects.prefetch_related('images')
for product in products:
    for image in product.images.all():  # No additional query
        print(image.url)
```

**SQL Generated:**
```sql
-- Query 1: Get products
SELECT * FROM products

-- Query 2: Get all related images in one query
SELECT * FROM product_images WHERE product_id IN (1, 2, 3, ...)
```

### Pattern 3: Nested Prefetch with `Prefetch()` Objects

**When to use:** Need to filter or customize the prefetched queryset

**Example:**
```python
from django.db.models import Prefetch

# Only fetch primary images
products = Product.objects.prefetch_related(
    Prefetch(
        'images',
        queryset=ProductImage.objects.filter(is_primary=True)
    )
)
```

### Pattern 4: Combine `select_related()` and `prefetch_related()`

**When to use:** Related objects have their own related objects

**Example:**
```python
# Fetch orders with items, and items with products
orders = Order.objects.select_related('user').prefetch_related(
    'items__product',  # items → product (via ForeignKey)
    'items__variant'   # items → variant (via ForeignKey)
)
```

### Pattern 5: Use `only()` and `defer()` to Reduce Data Transfer

**When to use:** Don't need all fields from a model

**Example:**
```python
# Only fetch needed fields for list views
products = Product.objects.only(
    'id', 'name', 'price', 'category__name'
)

# Defer large text fields
products = Product.objects.defer('description', 'meta_description')
```

### Pattern 6: Action-Specific Querysets

**When to use:** Different actions need different optimizations

**Example:**
```python
def get_queryset(self):
    if self.action == 'list':
        # Lightweight queryset
        return Product.objects.select_related('category').only('id', 'name')
    elif self.action == 'retrieve':
        # Full queryset with all relations
        return Product.objects.select_related('category').prefetch_related(
            'images', 'variants', 'reviews'
        )
```

---

## Testing for N+1 Queries

### Method 1: Using Test Utilities

```python
from apps.core.test_utils import assert_no_n_plus_one, AssertNumQueriesLessThan

class ProductAPITest(APITestCase):
    @assert_no_n_plus_one
    def test_product_list_no_n_plus_one(self):
        """Ensure product list doesn't have N+1 queries"""
        # Create 100 products
        for i in range(100):
            Product.objects.create(name=f"Product {i}", category=self.category)

        response = self.client.get('/api/v1/products/')
        self.assertEqual(response.status_code, 200)
        # Test will fail if N+1 detected

    def test_product_list_query_count(self):
        """Ensure product list uses minimal queries"""
        with AssertNumQueriesLessThan(5):
            response = self.client.get('/api/v1/products/')
            self.assertEqual(response.status_code, 200)
```

### Method 2: Using Django Debug Toolbar

Add to development settings:
```python
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

Check the "SQL" panel to see all queries executed.

### Method 3: Using Management Command

```bash
# Audit all endpoints
python manage.py audit_queries

# With custom threshold
python manage.py audit_queries --threshold 5

# Output as JSON
python manage.py audit_queries --output json > query_audit.json
```

---

## Monitoring

### Query Count Monitoring

Monitor query counts in Grafana:

```promql
# Average queries per request
rate(django_db_queries_total[5m])
/
rate(django_http_requests_total[5m])

# P95 query execution time
histogram_quantile(0.95,
  rate(django_db_query_duration_seconds_bucket[5m])
)
```

### Slow Query Logging

PostgreSQL configuration:
```sql
-- In postgresql.conf
log_min_duration_statement = 100  -- Log queries > 100ms
log_statement = 'all'  -- Log all statements (development only)
```

Query slow query log:
```sql
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Best Practices

### DO

1. **Always use `select_related()` for ForeignKey**
   ```python
   Product.objects.select_related('category')
   ```

2. **Use `prefetch_related()` for reverse relations and ManyToMany**
   ```python
   Product.objects.prefetch_related('images', 'tags')
   ```

3. **Use `Prefetch()` objects for filtered prefetching**
   ```python
   Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
   ```

4. **Use `only()` for list views with many fields**
   ```python
   Product.objects.only('id', 'name', 'price')
   ```

5. **Test for N+1 queries in all new endpoints**
   ```python
   @assert_no_n_plus_one
   def test_endpoint(self):
       ...
   ```

6. **Use different querysets for list vs detail actions**
   ```python
   if self.action == 'list':
       return Model.objects.only('id', 'name')
   ```

7. **Profile queries during development**
   ```python
   from django.db import connection
   print(len(connection.queries))
   ```

### DON'T

1. **Don't access related objects without prefetching**
   ```python
   # BAD: N+1 query
   for product in Product.objects.all():
       print(product.category.name)
   ```

2. **Don't use `all()` when you need `count()`**
   ```python
   # BAD: Fetches all objects
   len(product.images.all())

   # GOOD: Database COUNT query
   product.images.count()
   ```

3. **Don't use `exists()` after fetching**
   ```python
   # BAD: Already fetched
   products = Product.objects.all()
   if products.exists():  # Too late

   # GOOD: Use exists() before fetching
   if Product.objects.filter(category=cat).exists():
       products = Product.objects.filter(category=cat)
   ```

4. **Don't iterate over querysets multiple times**
   ```python
   # BAD: Queries database twice
   products = Product.objects.all()
   for p in products: ...
   for p in products: ...  # Another query!

   # GOOD: Convert to list if needed
   products = list(Product.objects.all())
   for p in products: ...
   for p in products: ...  # No query
   ```

---

## Common Scenarios

### Scenario: Product List with Category and Image

```python
# OPTIMAL: 2 queries
products = Product.objects.select_related('category').prefetch_related(
    Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
).only('id', 'name', 'price', 'category__name')
```

### Scenario: Order Detail with Items and Products

```python
# OPTIMAL: 3 queries
order = Order.objects.select_related('user').prefetch_related(
    'items__product',
    'items__variant'
).get(id=order_id)
```

### Scenario: User with Orders and Order Items

```python
# OPTIMAL: 4 queries
user = User.objects.select_related('profile').prefetch_related(
    'orders',
    'orders__items',
    'orders__items__product'
).get(id=user_id)
```

---

## Troubleshooting

### Issue: Still seeing multiple queries

**Solution:** Check serializer - it might be accessing relations

```python
# BAD: Serializer accessing related object
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name')  # N+1 if not prefetched

# GOOD: Ensure view prefetches
queryset = Product.objects.select_related('category')
```

### Issue: Prefetch not working

**Solution:** Check if you're filtering after prefetch

```python
# BAD: Filtering nullifies prefetch
products = Product.objects.prefetch_related('images')
for product in products.filter(is_active=True):  # New query!
    ...

# GOOD: Filter before prefetch
products = Product.objects.filter(is_active=True).prefetch_related('images')
```

---

## References

- [Django select_related documentation](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#select-related)
- [Django prefetch_related documentation](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#prefetch-related)
- [Database Query Optimization](https://docs.djangoproject.com/en/4.2/topics/db/optimization/)

---

**Document Owner:** Backend Team
**Review Schedule:** After each major feature addition
**Version:** 1.0
**Last Reviewed:** 2025-12-20
