# Blue-Green Deployment Strategy

**Version**: 1.0
**Last Updated**: 2025-12-04
**Owner**: DevOps Team

---

## Overview

Blue-Green deployment is a release technique that reduces downtime and risk by running two identical production environments: Blue (current) and Green (new version).

## Architecture

```
┌──────────────┐
│ Load Balancer │
└──────┬───────┘
       │
       ├─────────────┬─────────────┐
       │             │             │
┌──────▼──────┐ ┌───▼──────┐ ┌───▼──────┐
│   Blue      │ │  Green   │ │ Rollback │
│ (Active)    │ │  (New)   │ │ (Option) │
│  v1.0.0     │ │  v1.1.0  │ │  v0.9.9  │
└─────────────┘ └──────────┘ └──────────┘
```

## Kubernetes Implementation

### 1. Service Selector Strategy

```yaml
# Blue Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
      version: blue
  template:
    metadata:
      labels:
        app: backend
        version: blue
    spec:
      containers:
        - name: backend
          image: ghcr.io/org/backend:v1.0.0

---
# Green Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
      version: green
  template:
    metadata:
      labels:
        app: backend
        version: green
    spec:
      containers:
        - name: backend
          image: ghcr.io/org/backend:v1.1.0

---
# Service (switches between blue/green)
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  selector:
    app: backend
    version: blue  # <-- Switch this to 'green' to cutover
  ports:
    - port: 8000
```

### 2. Deployment Script

```bash
#!/bin/bash
# File: scripts/blue-green-deploy.sh

set -e

NAMESPACE="ecommerce-production"
NEW_VERSION=$1
CURRENT_COLOR=$(kubectl get service backend -n $NAMESPACE -o jsonpath='{.spec.selector.version}')

if [ "$CURRENT_COLOR" == "blue" ]; then
    NEW_COLOR="green"
    OLD_COLOR="blue"
else
    NEW_COLOR="blue"
    OLD_COLOR="green"
fi

echo "🚀 Starting Blue-Green Deployment"
echo "Current: $OLD_COLOR"
echo "Target: $NEW_COLOR"
echo "Version: $NEW_VERSION"

# Step 1: Deploy new version to inactive environment
echo "📦 Deploying $NEW_VERSION to $NEW_COLOR environment..."
kubectl set image deployment/backend-$NEW_COLOR \
    backend=ghcr.io/org/backend:$NEW_VERSION \
    -n $NAMESPACE

# Step 2: Wait for rollout
echo "⏳ Waiting for rollout to complete..."
kubectl rollout status deployment/backend-$NEW_COLOR -n $NAMESPACE --timeout=5m

# Step 3: Health check
echo "🏥 Running health checks..."
POD=$(kubectl get pod -n $NAMESPACE -l app=backend,version=$NEW_COLOR -o jsonpath="{.items[0].metadata.name}")
kubectl exec -n $NAMESPACE $POD -- curl -f http://localhost:8000/health || exit 1

# Step 4: Run smoke tests
echo "🧪 Running smoke tests..."
./scripts/smoke-tests.sh $NEW_COLOR || exit 1

# Step 5: Switch traffic
echo "🔄 Switching traffic to $NEW_COLOR..."
kubectl patch service backend -n $NAMESPACE -p "{\"spec\":{\"selector\":{\"version\":\"$NEW_COLOR\"}}}"

# Step 6: Monitor for 5 minutes
echo "👀 Monitoring new version for 5 minutes..."
for i in {1..30}; do
    ERROR_RATE=$(kubectl exec -n $NAMESPACE $POD -- curl -s http://localhost:8000/metrics | grep http_requests_total | grep "5.." | awk '{sum+=$2} END {print sum}')
    echo "Errors in last 30s: $ERROR_RATE"

    if [ "$ERROR_RATE" -gt 10 ]; then
        echo "❌ High error rate detected! Rolling back..."
        kubectl patch service backend -n $NAMESPACE -p "{\"spec\":{\"selector\":{\"version\":\"$OLD_COLOR\"}}}"
        exit 1
    fi

    sleep 10
done

echo "✅ Deployment successful!"
echo "📊 Old version ($OLD_COLOR) is still running and can be used for instant rollback"
```

### 3. Instant Rollback

```bash
#!/bin/bash
# File: scripts/rollback.sh

NAMESPACE="ecommerce-production"
CURRENT_COLOR=$(kubectl get service backend -n $NAMESPACE -o jsonpath='{.spec.selector.version}')

if [ "$CURRENT_COLOR" == "blue" ]; then
    ROLLBACK_TO="green"
else
    ROLLBACK_TO="blue"
fi

echo "🔙 Rolling back to $ROLLBACK_TO..."
kubectl patch service backend -n $NAMESPACE -p "{\"spec\":{\"selector\":{\"version\":\"$ROLLBACK_TO\"}}}"
echo "✅ Rollback complete!"
```

## AWS/CloudFormation Implementation

### Using Target Groups

```yaml
# Two target groups pointing to different deployments
Resources:
  BlueTargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: backend-blue
      Port: 8000
      Protocol: HTTP
      VpcId: !Ref VPC

  GreenTargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: backend-green
      Port: 8000
      Protocol: HTTP
      VpcId: !Ref VPC

  ListenerRule:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      Actions:
        - Type: forward
          TargetGroupArn: !Ref BlueTargetGroup  # Switch to GreenTargetGroup
      Conditions:
        - Field: path-pattern
          Values: ["/*"]
      ListenerArn: !Ref Listener
      Priority: 1
```

## Testing Strategy

### 1. Smoke Tests

```python
# tests/smoke/test_deployment.py

import requests
import pytest

def test_health_endpoint(base_url):
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200

def test_authentication(base_url):
    response = requests.post(f"{base_url}/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "test"
    })
    assert response.status_code in [200, 401]

def test_database_connectivity(base_url):
    response = requests.get(f"{base_url}/api/v1/products/")
    assert response.status_code in [200, 401]
```

### 2. Canary Testing (Progressive Rollout)

```yaml
# Gradually shift traffic from blue to green
apiVersion: split.smi-spec.io/v1alpha1
kind: TrafficSplit
metadata:
  name: backend-split
spec:
  service: backend
  backends:
    - service: backend-blue
      weight: 90  # 90% to blue
    - service: backend-green
      weight: 10  # 10% to green (canary)
```

## Monitoring During Deployment

### Key Metrics to Watch

```yaml
# Prometheus Alert Rules
groups:
  - name: deployment
    rules:
      - alert: HighErrorRateDuringDeployment
        expr: |
          rate(http_requests_total{status=~"5.."}[1m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate during deployment"

      - alert: HighLatencyDuringDeployment
        expr: |
          histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[1m])) > 1
        for: 2m
        labels:
          severity: warning
```

## Best Practices

### 1. Database Migrations

**Forward-Compatible Migrations**:
```python
# Migration 001: Add new column (nullable)
class Migration:
    def forwards(self, orm):
        orm.Product.add_column('new_field', nullable=True)

# Deploy green version (reads new_field)

# Migration 002: Make column non-nullable
class Migration:
    def forwards(self, orm):
        orm.Product.alter_column('new_field', nullable=False)
```

### 2. Shared Resources

- Database: Use same database for both environments
- Cache: Separate Redis namespaces: `blue:*` and `green:*`
- Storage: Shared S3 bucket with versioning
- Message Queue: Separate queues or use message routing

### 3. Configuration

```yaml
# Blue Environment
env:
  - name: ENVIRONMENT_COLOR
    value: "blue"
  - name: CACHE_PREFIX
    value: "blue"

# Green Environment
env:
  - name: ENVIRONMENT_COLOR
    value: "green"
  - name: CACHE_PREFIX
    value: "green"
```

## Automation with ArgoCD

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: backend
spec:
  replicas: 3
  strategy:
    blueGreen:
      activeService: backend
      previewService: backend-preview
      autoPromotionEnabled: false
      scaleDownDelaySeconds: 600  # Keep old version for 10 min
  template:
    spec:
      containers:
        - name: backend
          image: ghcr.io/org/backend:latest
```

## Rollback Decision Matrix

| Metric | Threshold | Action |
|--------|-----------|--------|
| Error Rate | > 5% | Immediate rollback |
| Latency p95 | > 2x baseline | Rollback |
| Memory Usage | > 90% | Rollback |
| CPU Usage | > 95% | Investigate, maybe rollback |
| Failed Health Checks | > 2 in 5 min | Rollback |

## Checklist

### Pre-Deployment
- [ ] Smoke tests passing in staging
- [ ] Database migrations tested
- [ ] Rollback plan documented
- [ ] Monitoring dashboards open
- [ ] Team notified

### During Deployment
- [ ] Monitor error rates
- [ ] Watch latency metrics
- [ ] Check resource usage
- [ ] Run smoke tests
- [ ] Verify database connectivity

### Post-Deployment
- [ ] Monitor for 30 minutes
- [ ] Check logs for errors
- [ ] Verify metrics normal
- [ ] Update documentation
- [ ] Scale down old environment (after 24h)

---

**Document Version**: 1.0
**Next Review**: After each deployment
**Owner**: DevOps Team
