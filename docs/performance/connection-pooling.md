# Connection Pooling Tuning Guide

**Last Updated:** 2025-12-20
**Owner:** DBA Team & SRE Team
**Target Utilization:** 60-80%

---

## Table of Contents

1. [Overview](#overview)
2. [Current Configuration](#current-configuration)
3. [Tuning Guidelines](#tuning-guidelines)
4. [Monitoring](#monitoring)
5. [Troubleshooting](#troubleshooting)
6. [Best Practices](#best-practices)

---

## Overview

Connection pooling reduces the overhead of creating and destroying database connections by reusing existing connections. This guide covers PgBouncer and Django database connection configuration.

### Why Connection Pooling?

- **Reduces latency**: Reusing connections is faster than creating new ones
- **Reduces load**: Less CPU and memory overhead on PostgreSQL
- **Better scalability**: Support more concurrent users with fewer DB connections
- **Predictable performance**: Avoid connection storms during traffic spikes

### Architecture

```
Django App (1000 clients)
     ↓
PgBouncer (Pool of 25 connections)
     ↓
PostgreSQL (Max 100 connections)
```

---

## Current Configuration

### PgBouncer Configuration

**File:** `infrastructure/docker/pgbouncer/pgbouncer.ini`

```ini
[databases]
ecommerce = host=postgres port=5432 dbname=ecommerce

[pgbouncer]
# Connection mode
pool_mode = transaction  # Recommended for web apps

# Connection limits
max_client_conn = 1000       # Max client connections
default_pool_size = 25       # Pool size per user/database
min_pool_size = 5            # Minimum pool size
reserve_pool_size = 10       # Additional connections when pool is full
max_db_connections = 100     # Max connections to PostgreSQL

# Timeouts
server_idle_timeout = 600    # Close idle server connections after 10 min
server_lifetime = 3600       # Max connection lifetime (1 hour)
server_connect_timeout = 15  # Connection timeout
```

### Django Configuration

**File:** `services/backend/config/settings/production.py`

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'pgbouncer',  # Connect through PgBouncer
        'PORT': 6432,         # PgBouncer port
        'CONN_MAX_AGE': 600,  # Keep connections for 10 minutes
        'CONN_HEALTH_CHECKS': True,  # Check connection health
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

---

## Tuning Guidelines

### Determining Optimal Pool Size

Use the formula:

```
pool_size = (core_count * 2) + effective_spindle_count
```

For typical web applications:
- **8 cores**: pool_size = 20-25
- **16 cores**: pool_size = 35-40
- **32 cores**: pool_size = 65-70

**However**, test with actual load to find optimal size.

### Rule of Thumb

1. **Start conservative**: Begin with pool_size = 20-25
2. **Monitor utilization**: Target 60-80% utilization under normal load
3. **Load test**: Test with expected peak traffic
4. **Adjust gradually**: Increase by 5-10 at a time

### Pool Mode Selection

| Mode | When to Use | Trade-offs |
|------|-------------|------------|
| **session** | Long-lived connections, complex transactions | Higher resource usage |
| **transaction** | Web apps (recommended) | Best balance |
| **statement** | Simple queries, maximum concurrency | Can break transaction semantics |

**Recommendation:** Use `transaction` mode for Django applications.

### Calculating Required Connections

```
Total Clients = Django instances × threads per instance
Example: 3 instances × 8 workers = 24 concurrent clients

Recommended pool_size = Total Clients × 1.2 (20% buffer)
Example: 24 × 1.2 = 29 ≈ 30
```

---

## Tuning Process

### Step 1: Baseline Measurement

Run current configuration under load:

```bash
# Watch pool stats
python manage.py pool_stats --watch

# In another terminal, run load test
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --users 500 --spawn-rate 50 --run-time 5m
```

Record:
- Peak connection count
- Average utilization
- P95 response time
- Error rate

### Step 2: Automated Tuning

Use the tuning script:

```bash
chmod +x scripts/tune_connection_pools.sh
./scripts/tune_connection_pools.sh
```

This will:
1. Test multiple pool sizes
2. Run load tests for each
3. Generate comparison report

### Step 3: Analysis

Review results in `reports/pool_tuning_TIMESTAMP/summary.md`

Look for:
- **Lowest P95 latency**
- **Highest throughput (RPS)**
- **No connection timeouts**
- **Pool utilization 60-80%**

### Step 4: Apply Configuration

Update `infrastructure/docker/pgbouncer/pgbouncer.ini`:

```ini
default_pool_size = [OPTIMAL_SIZE]
min_pool_size = [OPTIMAL_SIZE * 0.2]
reserve_pool_size = [OPTIMAL_SIZE * 0.4]
```

Restart PgBouncer:

```bash
docker-compose -f deploy/docker/compose/production.yml restart pgbouncer
```

---

## Monitoring

### Real-Time Monitoring

```bash
# PostgreSQL connection stats
python manage.py pool_stats

# Watch continuously
python manage.py pool_stats --watch

# Include PgBouncer stats
python manage.py pool_stats --pgbouncer --watch
```

### SQL Queries

**PostgreSQL connection count:**

```sql
SELECT count(*) as total_connections,
       count(*) FILTER (WHERE state = 'active') as active,
       count(*) FILTER (WHERE state = 'idle') as idle,
       (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_conn
FROM pg_stat_activity;
```

**PgBouncer pool stats:**

```sql
-- Connect to PgBouncer admin
psql -h pgbouncer -p 6432 -U postgres pgbouncer

-- Show pools
SHOW POOLS;

-- Show stats
SHOW STATS;

-- Show active clients
SHOW CLIENTS;

-- Show active server connections
SHOW SERVERS;
```

### Grafana Dashboards

Monitor these metrics:

```promql
# Pool utilization
pg_stat_database_numbackends / pg_settings_max_connections * 100

# Active connections
pg_stat_activity_count{state="active"}

# Idle connections
pg_stat_activity_count{state="idle"}

# Connection wait time (PgBouncer)
pgbouncer_pools_cl_waiting > 0
```

**Alert when:**
- Utilization > 80% for 5 minutes
- Waiting clients > 10
- Connection errors > 0

---

## Troubleshooting

### Problem: Pool Exhausted

**Symptoms:**
- Errors: "connection pool exhausted"
- High client waiting count
- Slow response times

**Diagnosis:**

```sql
-- Check pool status
SHOW POOLS;

-- Check waiting clients
SELECT database, user, cl_active, cl_waiting, sv_active, sv_idle
FROM pgbouncer.pools
WHERE cl_waiting > 0;
```

**Solutions:**

1. **Immediate**: Increase pool size
   ```ini
   default_pool_size = 30  # Was 25
   reserve_pool_size = 15  # Was 10
   ```

2. **Short-term**: Scale horizontally
   ```bash
   docker-compose up -d --scale backend=5
   ```

3. **Long-term**: Optimize queries to reduce connection hold time

### Problem: Too Many Idle Connections

**Symptoms:**
- High idle connection count
- Wasted resources

**Solutions:**

1. Reduce server_idle_timeout:
   ```ini
   server_idle_timeout = 300  # 5 minutes instead of 10
   ```

2. Reduce min_pool_size:
   ```ini
   min_pool_size = 3  # Instead of 5
   ```

3. Adjust Django CONN_MAX_AGE:
   ```python
   'CONN_MAX_AGE': 300  # 5 minutes instead of 10
   ```

### Problem: Connection Timeouts

**Symptoms:**
- Errors: "connection timeout"
- High reserve_pool_timeout errors

**Solutions:**

1. Increase timeout:
   ```ini
   reserve_pool_timeout = 5  # Was 3
   server_connect_timeout = 20  # Was 15
   ```

2. Increase reserve pool:
   ```ini
   reserve_pool_size = 15  # Was 10
   ```

3. Increase max_db_connections:
   ```ini
   max_db_connections = 150  # Was 100
   ```

### Problem: Long-Running Queries Blocking Pool

**Diagnosis:**

```sql
SELECT pid, now() - query_start as duration, state, query
FROM pg_stat_activity
WHERE state = 'active'
  AND query_start < now() - interval '1 minute'
ORDER BY duration DESC;
```

**Solutions:**

1. Set query timeout in PostgreSQL:
   ```sql
   ALTER DATABASE ecommerce SET statement_timeout = '30s';
   ```

2. Kill long-running queries:
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'active'
     AND query_start < now() - interval '5 minutes';
   ```

3. Optimize the slow queries

---

## Best Practices

### DO

1. **Use transaction pooling mode** for Django apps
   ```ini
   pool_mode = transaction
   ```

2. **Set reasonable timeouts**
   ```ini
   server_idle_timeout = 600
   server_connect_timeout = 15
   reserve_pool_timeout = 3
   ```

3. **Monitor pool utilization**
   - Target: 60-80% under normal load
   - Alert: > 80% sustained

4. **Use PgBouncer for all database connections**
   ```python
   'HOST': 'pgbouncer',  # Not 'postgres' directly
   'PORT': 6432,
   ```

5. **Enable connection health checks**
   ```python
   'CONN_HEALTH_CHECKS': True
   ```

6. **Test configuration under load before production**
   ```bash
   ./scripts/tune_connection_pools.sh
   ```

7. **Keep connections alive with TCP keepalive**
   ```ini
   tcp_keepalive = 1
   tcp_keepidle = 60
   ```

### DON'T

1. **Don't set pool size too high**
   - More connections = more overhead
   - Start with 20-25, increase if needed

2. **Don't use session mode for web apps**
   - Wastes connections
   - Use transaction mode instead

3. **Don't connect directly to PostgreSQL**
   - Always go through PgBouncer
   - Defeats the purpose of pooling

4. **Don't ignore waiting clients**
   - If clients are waiting, pool is too small
   - Monitor and adjust

5. **Don't set CONN_MAX_AGE too high**
   - Can hold connections unnecessarily
   - 5-10 minutes is usually sufficient

6. **Don't skip health checks**
   - Broken connections can cause errors
   - Always enable CONN_HEALTH_CHECKS

---

## Configuration Cheat Sheet

### Small Deployment (1-2 backend instances)

```ini
[pgbouncer]
pool_mode = transaction
max_client_conn = 200
default_pool_size = 15
min_pool_size = 3
reserve_pool_size = 8
max_db_connections = 50
```

### Medium Deployment (3-5 backend instances)

```ini
[pgbouncer]
pool_mode = transaction
max_client_conn = 500
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 10
max_db_connections = 100
```

### Large Deployment (10+ backend instances)

```ini
[pgbouncer]
pool_mode = transaction
max_client_conn = 2000
default_pool_size = 50
min_pool_size = 10
reserve_pool_size = 20
max_db_connections = 200
```

---

## References

- [PgBouncer Documentation](https://www.pgbouncer.org/config.html)
- [PostgreSQL Connection Pooling](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [Django Database Configuration](https://docs.djangoproject.com/en/4.2/ref/databases/)

---

**Document Owner:** DBA Team & SRE Team
**Review Schedule:** Quarterly or after major traffic changes
**Version:** 1.0
**Last Reviewed:** 2025-12-20
