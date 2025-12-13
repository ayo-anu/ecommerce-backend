"""
Shared configuration management
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Django Backend Integration
    # SECURITY FIX: Use Docker DNS names as defaults (not localhost)
    DJANGO_BACKEND_URL: str = "http://backend:8000"
    DJANGO_API_KEY: str = ""

    # ==============================================================================
    # DATABASE ACCESS - DEPRECATED
    # ==============================================================================
    # WARNING: Direct database access from AI services is deprecated and will be
    # removed in a future release. AI services MUST communicate with the backend
    # via the API (DJANGO_BACKEND_URL) for all data operations.
    #
    # These fields are kept as None for backward compatibility but should not be used.
    # ==============================================================================
    DATABASE_URL: str = None  # DEPRECATED: Use DJANGO_BACKEND_URL instead
    DB_POOL_SIZE: int = None  # DEPRECATED: Not applicable for API-based access
    DB_MAX_OVERFLOW: int = None  # DEPRECATED: Not applicable for API-based access

    # Redis
    # SECURITY FIX: Use Docker DNS names as defaults (not localhost)
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # Qdrant Vector DB
    # SECURITY FIX: Use Docker DNS names as defaults (not localhost)
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_PRODUCTS: str = "products"
    QDRANT_VECTOR_SIZE: int = 384
    
    # ==============================================================================
    # Security & Authentication
    # ==============================================================================
    # NOTE: Service secrets should be loaded from Vault in production
    # For now, these are loaded from environment variables
    # Future: Integrate with backend's Vault client for service-level secrets
    SECRET_KEY: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Service-to-Service Authentication
    # REQUIRED: Unique per service, should be managed via Vault in production
    SERVICE_AUTH_SECRET: str = ""
    SERVICE_NAME: str = "unknown"

    # API Gateway needs all service secrets to inject headers
    SERVICE_AUTH_SECRET_RECOMMENDATION_ENGINE: str = ""
    SERVICE_AUTH_SECRET_SEARCH_ENGINE: str = ""
    SERVICE_AUTH_SECRET_PRICING_ENGINE: str = ""
    SERVICE_AUTH_SECRET_CHATBOT_RAG: str = ""
    SERVICE_AUTH_SECRET_FRAUD_DETECTION: str = ""
    SERVICE_AUTH_SECRET_FORECASTING: str = ""
    SERVICE_AUTH_SECRET_VISUAL_RECOGNITION: str = ""

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    GATEWAY_HOST: str = "0.0.0.0"
    GATEWAY_PORT: int = 8080
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Service URLs
    # SECURITY FIX: Use Docker DNS names as defaults (not localhost)
    RECOMMENDATION_SERVICE_URL: str = "http://recommender:8001"
    SEARCH_SERVICE_URL: str = "http://search:8002"
    PRICING_SERVICE_URL: str = "http://pricing:8003"
    CHATBOT_SERVICE_URL: str = "http://chatbot:8004"
    FRAUD_SERVICE_URL: str = "http://fraud:8005"
    FORECAST_SERVICE_URL: str = "http://forecasting:8006"
    VISION_SERVICE_URL: str = "http://vision:8007"
    
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
