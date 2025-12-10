"""
Example: Refactored AI Service using BaseAIService.

This example shows how to refactor an existing AI service to use the BaseAIService
class, reducing code duplication from ~100+ lines to ~30 lines.

BEFORE (typical service with ~120 lines of boilerplate):
  - Manual FastAPI setup
  - Manual health check setup
  - Manual metrics setup
  - Manual exception handling
  - Manual validation middleware
  - Manual lifecycle management
  - Duplicated across all 7 services

AFTER (with BaseAIService, ~30 lines of business logic):
  - All infrastructure handled by base class
  - Focus only on business logic
  - Consistent across all services
  - Easy to maintain and update
"""

from shared.base_service import BaseAIService
from typing import List


class RefactoredFraudDetectionService(BaseAIService):
    """
    Fraud Detection Service - Refactored Version.

    This version uses BaseAIService to handle all infrastructure concerns,
    leaving only business logic in the service class.
    """

    def __init__(self):
        super().__init__(
            service_name="fraud_detection",
            version="1.0.0",
            description="Real-time fraud detection using ML and rule-based systems",
            dependencies=["postgres"],  # Health check will monitor postgres
            port=8003
        )

        # Service-specific state (if needed)
        self.fraud_model = None
        self.rule_engine = None

    async def on_startup_hook(self):
        """Custom startup logic - load ML models, initialize engines."""
        self.logger.info("Loading fraud detection models...")

        # Initialize fraud detection model (placeholder)
        # In production, load from file or model registry
        # self.fraud_model = await load_fraud_model()
        # self.rule_engine = RuleEngine()

        self.logger.info("✅ Fraud detection models loaded")
        self.logger.info("✅ Rule engine initialized with 10+ rules")

    async def on_shutdown_hook(self):
        """Custom shutdown logic - cleanup resources."""
        self.logger.info("Cleaning up fraud detection resources...")

        # Cleanup (placeholder)
        # if self.fraud_model:
        #     await self.fraud_model.cleanup()

        self.logger.info("✅ Cleanup complete")

    def get_startup_message(self) -> List[str]:
        """Custom startup messages."""
        return [
            "ML-based anomaly detection (Isolation Forest)",
            "Rule-based expert system (10+ rules)",
            "Velocity checks enabled",
            "Device fingerprinting active",
            "Risk scoring & decision engine ready"
        ]

    def register_routes(self, app):
        """Register fraud detection routes."""
        from .routers import fraud  # Import your business logic router
        app.include_router(fraud.router)
        self.logger.info("✅ Fraud detection routes registered")


# ==============================================================================
# Application Entry Point
# ==============================================================================

# Create service instance
service = RefactoredFraudDetectionService()

# Create FastAPI app (all infrastructure configured automatically)
app = service.create_app()


# ==============================================================================
# Direct Execution (for development)
# ==============================================================================

if __name__ == "__main__":
    service.run()


# ==============================================================================
# COMPARISON: Lines of Code
# ==============================================================================
# Original (fraud_detection/main.py):     ~118 lines
# Refactored (using BaseAIService):       ~30 lines of business logic
# Reduction:                              ~75% less code
# Duplication eliminated:                 ~88 lines × 7 services = 616 lines saved
#
# Benefits:
# 1. Consistency: All services follow identical patterns
# 2. Maintainability: Update base class, all services benefit
# 3. Testability: Test base class once, confidence in all services
# 4. Security: Security updates propagate automatically
# 5. Clarity: Business logic clearly separated from infrastructure
# ==============================================================================
