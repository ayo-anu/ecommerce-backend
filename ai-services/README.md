# 🛍️ E-Commerce AI Platform - Enterprise Grade

> Production-ready FastAPI microservices platform with 7 AI systems integrated with your DRF backend

## 🎯 Overview

This AI platform seamlessly integrates with your existing Django REST Framework e-commerce backend, providing:

- **Recommendation Engine** - Personalized product recommendations
- **Intelligent Search** - Semantic + visual search capabilities  
- **Dynamic Pricing AI** - Price optimization and competitor analysis
- **AI Chatbot (RAG)** - Customer support with context awareness
- **Fraud Detection** - Real-time transaction risk scoring
- **Demand Forecasting** - Inventory and demand prediction
- **Visual Recognition** - Product image classification and tagging

## 📊 Architecture

```
┌─────────────────────────────────────────┐
│    Your Django DRF Backend (Port 8000)  │
│         (Existing E-commerce)            │
└─────────────────────────────────────────┘
                    ↓ REST API Calls
┌─────────────────────────────────────────┐
│    AI Gateway (FastAPI) - Port 8080     │
│    Authentication & Rate Limiting        │
└─────────────────────────────────────────┘
                    ↓
    ┌───────────────────────────────┐
    │   AI Microservices Cluster     │
    └───────────────────────────────┘
    ↓       ↓       ↓       ↓       ↓
 Port:8001 8002   8003   8004   8005-8007
  Recom.  Search  Price  Chat  Fraud/etc.
```

## 🚀 Quick Start (Windows PowerShell)

### Prerequisites
- Python 3.11+
- Docker Desktop
- 8GB+ RAM
- Your Django backend running

### Step 1: Setup
```powershell
# Navigate to project
cd ecommerce-ai-platform

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment
```powershell
# Copy environment template
cp .env.example .env

# Edit .env with your settings (especially DJANGO_BACKEND_URL)
notepad .env
```

### Step 3: Start Infrastructure
```powershell
# Start PostgreSQL, Redis, Qdrant, RabbitMQ
docker-compose up -d

# Wait for services to be ready (30 seconds)
Start-Sleep -Seconds 30

# Check services are running
docker-compose ps
```

### Step 4: Generate Synthetic Data
```powershell
# Since you have no historical data, generate realistic synthetic data
python data/synthetic_generator.py --products 10000 --users 5000 --orders 50000

# This creates realistic e-commerce data matching your Django models
```

### Step 5: Train Initial Models
```powershell
# Train recommendation models
python ml_pipeline/train_recommendations.py

# Train fraud detection model
python ml_pipeline/train_fraud_model.py

# Train forecasting models
python ml_pipeline/train_forecasting.py

# Train visual models (optional, uses pre-trained)
python ml_pipeline/train_visual_models.py
```

### Step 6: Start AI Services
```powershell
# Option A: Start all services with one command
python start_all_services.py

# Option B: Start individually for development
# Terminal 1: API Gateway
uvicorn api_gateway.main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 2: Recommendation Service
uvicorn services.recommendation_engine.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 3: Search Service
uvicorn services.search_engine.main:app --host 0.0.0.0 --port 8002 --reload

# ... and so on for other services
```

### Step 7: Test Integration
```powershell
# Health check
curl http://localhost:8080/health

# API Documentation
# Open browser: http://localhost:8080/docs

# Test recommendation endpoint
curl http://localhost:8080/api/v1/recommendations/user/YOUR_USER_UUID
```

## 🔗 Integration with Django Backend

### In Your Django Views:

```python
# apps/products/views.py
import httpx
from rest_framework.decorators import api_view
from rest_framework.response import Response

AI_GATEWAY_URL = "http://localhost:8080"
AI_API_KEY = "your-ai-api-key"  # From .env

@api_view(['GET'])
async def get_product_recommendations(request, product_id):
    """Get AI-powered product recommendations"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AI_GATEWAY_URL}/api/v1/recommendations/product/{product_id}/similar",
            headers={"Authorization": f"Bearer {AI_API_KEY}"}
        )
        return Response(response.json())

@api_view(['POST'])
async def check_fraud_score(request):
    """Check fraud score for transaction"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AI_GATEWAY_URL}/api/v1/fraud/score-transaction",
            headers={"Authorization": f"Bearer {AI_API_KEY}"},
            json=request.data
        )
        return Response(response.json())

@api_view(['GET'])
async def smart_search(request):
    """Semantic search for products"""
    query = request.GET.get('q', '')
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AI_GATEWAY_URL}/api/v1/search/semantic?q={query}",
            headers={"Authorization": f"Bearer {AI_API_KEY}"}
        )
        return Response(response.json())
```

### Add to requirements (Django):
```
httpx==0.25.2
```

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Get API token
- `POST /api/v1/auth/refresh` - Refresh token

### Recommendations (Port 8001)
- `GET /api/v1/recommendations/user/{user_id}` - Personalized recommendations
- `GET /api/v1/recommendations/product/{product_id}/similar` - Similar products
- `POST /api/v1/recommendations/batch` - Batch recommendations

### Search (Port 8002)
- `GET /api/v1/search/text?q={query}` - Text search
- `POST /api/v1/search/semantic` - Semantic search
- `POST /api/v1/search/visual` - Visual/image search

### Pricing (Port 8003)
- `GET /api/v1/pricing/optimize/{product_id}` - Optimal price
- `POST /api/v1/pricing/dynamic` - Dynamic pricing
- `GET /api/v1/pricing/competitor-analysis` - Market analysis

### Chatbot (Port 8004)
- `POST /api/v1/chat/message` - Send message
- `GET /api/v1/chat/history/{session_id}` - Conversation history
- `POST /api/v1/chat/feedback` - Feedback on response

### Fraud Detection (Port 8005)
- `POST /api/v1/fraud/score-transaction` - Score transaction
- `GET /api/v1/fraud/user-risk/{user_id}` - User risk profile
- `POST /api/v1/fraud/batch-analysis` - Batch analysis

### Forecasting (Port 8006)
- `POST /api/v1/forecast/demand` - Demand forecast
- `GET /api/v1/forecast/product/{product_id}` - Product forecast
- `POST /api/v1/forecast/inventory-optimization` - Optimize inventory

### Visual AI (Port 8007)
- `POST /api/v1/vision/classify` - Classify product image
- `POST /api/v1/vision/extract-attributes` - Extract attributes
- `POST /api/v1/vision/find-similar` - Find similar images

## 🔐 Security Features

- JWT Authentication (compatible with Django)
- API Key Management
- Rate Limiting (100 req/min per user)
- Request Validation (Pydantic)
- Input Sanitization
- CORS Configuration
- Encrypted Secrets

## 📊 Monitoring

Access monitoring dashboards:
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Flower (Celery)**: http://localhost:5555

## 🧪 Testing

```powershell
# Run all tests
pytest tests/ -v

# Run specific service tests
pytest tests/test_recommendations.py -v

# Load testing
locust -f tests/load_test.py --host=http://localhost:8080
```

## 📦 Project Structure

```
ecommerce-ai-platform/
├── api_gateway/              # Main API Gateway (Port 8080)
├── services/                 # AI Microservices
│   ├── recommendation_engine/  (Port 8001)
│   ├── search_engine/          (Port 8002)
│   ├── pricing_engine/         (Port 8003)
│   ├── chatbot_rag/            (Port 8004)
│   ├── fraud_detection/        (Port 8005)
│   ├── demand_forecasting/     (Port 8006)
│   └── visual_recognition/     (Port 8007)
├── shared/                   # Shared utilities
├── ml_pipeline/             # Model training
├── data/                    # Data & migrations
├── tests/                   # Test suite
├── deployment/              # Docker & deployment
└── monitoring/              # Monitoring configs
```

## 🚢 Deployment

### Local Development
```powershell
.\deployment\scripts\deploy_local.ps1
```

### Production (Cloud)

**AWS:**
```powershell
.\deployment\scripts\deploy_aws.ps1
```

**Azure:**
```powershell
.\deployment\scripts\deploy_azure.ps1
```

**GCP:**
```powershell
.\deployment\scripts\deploy_gcp.ps1
```

## 🔧 Configuration

Key environment variables in `.env`:

```env
# Django Backend Integration
DJANGO_BACKEND_URL=http://localhost:8000
DJANGO_API_KEY=your-django-api-key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/ecommerce_ai

# Redis
REDIS_URL=redis://localhost:6379/0

# Vector DB
QDRANT_URL=http://localhost:6333

# Security
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
```

## 📚 Documentation

- **API Docs**: http://localhost:8080/docs
- **Architecture**: docs/ARCHITECTURE.md
- **Deployment**: docs/DEPLOYMENT.md
- **Development**: docs/DEVELOPMENT.md

## 🐛 Troubleshooting

### Services won't start
```powershell
# Check Docker services
docker-compose ps

# Restart services
docker-compose restart

# Check logs
docker-compose logs -f
```

### Port conflicts
```powershell
# Check what's using a port
netstat -ano | findstr :8080

# Kill process
taskkill /PID <process_id> /F
```

### Database connection failed
```powershell
# Restart PostgreSQL
docker-compose restart postgres

# Check connection
docker-compose exec postgres pg_isready
```

## 📈 Performance Metrics

Target performance:
- API Response Time: <200ms (p95)
- Model Inference: <100ms
- Search Latency: <50ms
- Concurrent Users: 10,000+
- Throughput: 1,000 req/sec
- Uptime: 99.9%

## 🤝 Support

Issues? Questions?
- GitHub Issues: [Create Issue]
- Documentation: docs/
- Email: support@yourcompany.com

## 📄 License

MIT License - see LICENSE file

---

**Built with ❤️ for E-commerce Excellence**
