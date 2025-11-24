"""
Shared configuration management
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Django Backend Integration
    DJANGO_BACKEND_URL: str = "http://localhost:8000"
    DJANGO_API_KEY: str = ""
    
    # Database
    DATABASE_URL: str = "postgresql://ecommerce_ai:ecommerce_ai123@localhost:5433/ecommerce_ai"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Qdrant Vector DB
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_PRODUCTS: str = "products"
    QDRANT_VECTOR_SIZE: int = 384
    
    # Security
    SECRET_KEY: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    GATEWAY_HOST: str = "0.0.0.0"
    GATEWAY_PORT: int = 8080
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Service URLs
    RECOMMENDATION_SERVICE_URL: str = "http://localhost:8001"
    SEARCH_SERVICE_URL: str = "http://localhost:8002"
    PRICING_SERVICE_URL: str = "http://localhost:8003"
    CHATBOT_SERVICE_URL: str = "http://localhost:8004"
    FRAUD_SERVICE_URL: str = "http://localhost:8005"
    FORECAST_SERVICE_URL: str = "http://localhost:8006"
    VISION_SERVICE_URL: str = "http://localhost:8007"
    
    # ML Models
    MODEL_PATH: str = "./models"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    USE_GPU: bool = False
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
