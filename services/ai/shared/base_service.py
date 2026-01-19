"""Base service for AI microservices."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from prometheus_client import make_asgi_app
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from shared.health import create_health_router
from shared.exceptions import setup_exception_handlers
from shared.validation import InputValidationMiddleware
from shared.monitoring import setup_monitoring, service_up
from shared.logger import setup_logger
from shared.tracing import setup_tracing


class BaseAIService:
    """Base class for AI microservices."""

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
        self.service_name = service_name
        self.version = version
        self.description = description
        self.dependencies = dependencies or []
        self.enable_cors = enable_cors
        self.cors_origins = cors_origins
        self.port = port

        self.logger = setup_logger(service_name)

        self.app: Optional[FastAPI] = None
        self.tracer = None

    async def on_startup_hook(self):
        """Optional startup hook."""
        return None

    async def on_shutdown_hook(self):
        """Optional shutdown hook."""
        return None

    def get_startup_message(self) -> List[str]:
        """Startup log messages."""
        return [f"{self.service_name} service initialized"]

    def register_routes(self, app: FastAPI):
        """Optional route registration."""
        return None

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI app."""
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            self.logger.info(f"{'='*60}")
            self.logger.info(f"Starting {self.service_name} v{self.version}")
            self.logger.info(f"{'='*60}")

            for message in self.get_startup_message():
                self.logger.info(f"  • {message}")

            try:
                await self.on_startup_hook()
            except Exception as e:
                self.logger.error(f"Startup hook failed: {e}", exc_info=True)
                raise

            service_up.labels(service_name=self.service_name).set(1)
            port_msg = f" on port {self.port}" if self.port else ""
            self.logger.info(f"✅ {self.service_name} ready{port_msg}")

            yield

            self.logger.info(f"Shutting down {self.service_name}...")

            try:
                await self.on_shutdown_hook()
            except Exception as e:
                self.logger.error(f"Shutdown hook failed: {e}", exc_info=True)

            service_up.labels(service_name=self.service_name).set(0)
            self.logger.info(f"{self.service_name} shutdown complete")

        self.app = FastAPI(
            title=self.service_name.replace('_', ' ').title(),
            description=self.description,
            version=self.version,
            docs_url="/docs",
            redoc_url="/redoc",
            lifespan=lifespan
        )

        if self.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            self.logger.info(f"✅ CORS enabled for origins: {self.cors_origins}")

        setup_exception_handlers(self.app)
        self.logger.info("✅ Exception handlers registered")

        self.app.add_middleware(InputValidationMiddleware)
        self.logger.info("✅ Input validation middleware enabled")

        setup_monitoring(self.app, self.service_name)
        self.logger.info("✅ Prometheus metrics endpoint: /metrics")

        self.tracer = setup_tracing(self.app, self.service_name)
        self.logger.info("✅ Distributed tracing enabled")

        health_router = create_health_router(
            service_name=self.service_name,
            version=self.version,
            dependencies=self.dependencies
        )
        self.app.include_router(health_router)
        self.logger.info("✅ Health checks: /health, /health/live, /health/ready")

        self.register_routes(self.app)

        @self.app.get("/", tags=["info"])
        async def root() -> Dict[str, Any]:
            """Service info."""
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
        """Run the service with uvicorn."""
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
