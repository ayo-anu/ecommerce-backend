"""
Base Service Class for AI Microservices.

Provides common functionality for all AI services including:
- Standardized startup/shutdown lifecycle
- Health check endpoints
- Prometheus metrics
- Exception handling
- Input validation
- Distributed tracing
- Structured logging

Usage:
    from shared.base_service import BaseAIService

    class MyService(BaseAIService):
        def __init__(self):
            super().__init__(
                service_name="my_service",
                version="1.0.0",
                description="My AI service description",
                dependencies=["postgres", "redis"]
            )

        async def on_startup_hook(self):
            # Custom startup logic
            self.ml_model = load_model()

        async def on_shutdown_hook(self):
            # Custom shutdown logic
            cleanup_resources()

    # Create and configure the service
    service = MyService()
    app = service.create_app()
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from prometheus_client import make_asgi_app
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from shared.health import create_health_router
from shared.exceptions import setup_exception_handlers
from shared.validation import InputValidationMiddleware
from shared.monitoring import setup_monitoring, service_up
from shared.logger import setup_logger
from shared.tracing import setup_tracing


class BaseAIService:
    """
    Base class for all AI microservices.

    Provides common infrastructure:
    - FastAPI app creation and configuration
    - Health checks with dependency monitoring
    - Prometheus metrics collection
    - Global exception handling
    - Input validation middleware
    - Distributed tracing
    - Structured logging
    - CORS configuration
    - Lifecycle management
    """

    def __init__(
        self,
        service_name: str,
        version: str = "1.0.0",
        description: str = "",
        dependencies: Optional[List[str]] = None,
        enable_cors: bool = True,
        cors_origins: List[str] = ["*"],
        port: Optional[int] = None,
    ):
        """
        Initialize base AI service.

        Args:
            service_name: Name of the service (e.g., "fraud_detection")
            version: Service version (semantic versioning)
            description: Service description for API docs
            dependencies: List of dependencies for health checks
                         (e.g., ["postgres", "redis", "elasticsearch"])
            enable_cors: Whether to enable CORS middleware
            cors_origins: Allowed CORS origins (default: ["*"] for dev)
            port: Service port number (for documentation)
        """
        self.service_name = service_name
        self.version = version
        self.description = description
        self.dependencies = dependencies or []
        self.enable_cors = enable_cors
        self.cors_origins = cors_origins
        self.port = port

        # Setup logging
        self.logger = setup_logger(service_name)

        # App instance (created later)
        self.app: Optional[FastAPI] = None
        self.tracer = None

    async def on_startup_hook(self):
        """
        Override this method to add custom startup logic.

        Example:
            async def on_startup_hook(self):
                self.ml_model = await load_ml_model()
                self.logger.info("ML model loaded")
        """
        pass

    async def on_shutdown_hook(self):
        """
        Override this method to add custom shutdown logic.

        Example:
            async def on_shutdown_hook(self):
                await self.ml_model.cleanup()
                self.logger.info("ML model cleaned up")
        """
        pass

    def get_startup_message(self) -> List[str]:
        """
        Override this to customize startup log messages.

        Returns:
            List of startup messages to log

        Example:
            def get_startup_message(self) -> List[str]:
                return [
                    "ML-based fraud detection enabled",
                    "Rule-based system active",
                    "Real-time scoring ready"
                ]
        """
        return [f"{self.service_name} service initialized"]

    def register_routes(self, app: FastAPI):
        """
        Override this to register custom routes.

        Args:
            app: FastAPI application instance

        Example:
            def register_routes(self, app: FastAPI):
                from .routers import fraud
                app.include_router(fraud.router)
        """
        pass

    def create_app(self) -> FastAPI:
        """
        Create and configure FastAPI application with all standard middleware.

        Returns:
            Configured FastAPI application
        """
        # Create lifespan manager
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Startup and shutdown events"""
            # Startup
            self.logger.info(f"{'='*60}")
            self.logger.info(f"Starting {self.service_name} v{self.version}")
            self.logger.info(f"{'='*60}")

            # Log startup messages
            for message in self.get_startup_message():
                self.logger.info(f"  • {message}")

            # Call custom startup hook
            try:
                await self.on_startup_hook()
            except Exception as e:
                self.logger.error(f"Startup hook failed: {e}", exc_info=True)
                raise

            # Mark service as up
            service_up.labels(service_name=self.service_name).set(1)
            port_msg = f" on port {self.port}" if self.port else ""
            self.logger.info(f"✅ {self.service_name} ready{port_msg}")

            yield

            # Shutdown
            self.logger.info(f"Shutting down {self.service_name}...")

            # Call custom shutdown hook
            try:
                await self.on_shutdown_hook()
            except Exception as e:
                self.logger.error(f"Shutdown hook failed: {e}", exc_info=True)

            # Mark service as down
            service_up.labels(service_name=self.service_name).set(0)
            self.logger.info(f"{self.service_name} shutdown complete")

        # Create FastAPI app
        self.app = FastAPI(
            title=self.service_name.replace('_', ' ').title(),
            description=self.description,
            version=self.version,
            docs_url="/docs",
            redoc_url="/redoc",
            lifespan=lifespan
        )

        # Setup CORS if enabled
        if self.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            self.logger.info(f"✅ CORS enabled for origins: {self.cors_origins}")

        # Setup global exception handlers
        setup_exception_handlers(self.app)
        self.logger.info("✅ Exception handlers registered")

        # Add input validation middleware
        self.app.add_middleware(InputValidationMiddleware)
        self.logger.info("✅ Input validation middleware enabled")

        # Setup monitoring (adds /metrics endpoint)
        setup_monitoring(self.app, self.service_name)
        self.logger.info("✅ Prometheus metrics endpoint: /metrics")

        # Setup distributed tracing
        self.tracer = setup_tracing(self.app, self.service_name)
        self.logger.info("✅ Distributed tracing enabled")

        # Include standardized health checks
        health_router = create_health_router(
            service_name=self.service_name,
            version=self.version,
            dependencies=self.dependencies
        )
        self.app.include_router(health_router)
        self.logger.info("✅ Health checks: /health, /health/live, /health/ready")

        # Register custom routes
        self.register_routes(self.app)

        # Add root endpoint
        @self.app.get("/", tags=["info"])
        async def root() -> Dict[str, Any]:
            """Service information endpoint"""
            return {
                "service": self.service_name,
                "version": self.version,
                "status": "operational",
                "description": self.description,
                "endpoints": {
                    "health": "/health",
                    "health_live": "/health/live",
                    "health_ready": "/health/ready",
                    "metrics": "/metrics",
                    "docs": "/docs",
                    "redoc": "/redoc",
                }
            }

        self.logger.info(f"✅ Service initialized: {self.service_name} v{self.version}")

        return self.app

    def run(self, host: str = "0.0.0.0", port: Optional[int] = None, **kwargs):
        """
        Run the service with uvicorn.

        Args:
            host: Host to bind to
            port: Port to bind to (uses self.port if not specified)
            **kwargs: Additional uvicorn options
        """
        import uvicorn

        if self.app is None:
            self.app = self.create_app()

        port = port or self.port or 8000

        self.logger.info(f"Starting {self.service_name} on {host}:{port}...")

        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info",
            **kwargs
        )
