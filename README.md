# E-Commerce Backend

Production-grade Django REST API for e-commerce platform.

## Features

- User authentication & authorization (JWT)
- Product catalog management
- Order processing
- Payment integration (Stripe)
- Analytics & reporting
- Real-time notifications
- Full-text search (Elasticsearch)
- Admin dashboard

## Tech Stack

- Django 5.0
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Elasticsearch
- Stripe

## Quick Start

### Development

```bash
# Clone repository
git clone <repo-url>
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/development.txt

# Copy environment file
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Using Docker

```bash
docker-compose up -d
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

## API Documentation

- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/docs/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=apps --cov-report=html

# Run specific test
pytest apps/products/tests/test_models.py
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## License

MIT