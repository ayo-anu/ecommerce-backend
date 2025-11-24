"""
Demand Forecasting Service - Main Application
Time series forecasting and inventory optimization
Port: 8006
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from .routers import forecasting
from shared.monitoring import setup_monitoring
from shared.logger import setup_logger

logger = setup_logger("demand_forecasting")

app = FastAPI(
    title="E-commerce Demand Forecasting",
    description="Time series forecasting and inventory optimization",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_monitoring(app, "demand_forecasting")
app.include_router(forecasting.router)


@app.on_event("startup")
async def startup_event():
    logger.info("📈 Demand Forecasting Service starting...")
    logger.info("  - Time series forecasting")
    logger.info("  - Seasonality & trend detection")
    logger.info("  - Inventory optimization")
    logger.info("  - Anomaly detection")
    logger.info("Service ready on port 8006")


@app.get("/")
async def root():
    return {
        "service": "demand_forecasting",
        "version": "1.0.0",
        "status": "running",
        "capabilities": [
            "time_series_forecasting",
            "seasonality_detection",
            "trend_analysis",
            "inventory_optimization",
            "promotional_impact",
            "anomaly_detection",
            "accuracy_evaluation"
        ],
        "methods": [
            "moving_average",
            "exponential_smoothing",
            "linear_regression",
            "seasonal_naive"
        ],
        "endpoints": {
            "forecast": "/forecast/demand",
            "seasonality": "/forecast/seasonality",
            "trend": "/forecast/trend",
            "optimize_inventory": "/forecast/inventory/optimize",
            "promotional_impact": "/forecast/promotional/impact",
            "anomalies": "/forecast/anomalies",
            "accuracy": "/forecast/accuracy",
            "stats": "/forecast/stats",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "demand_forecasting"}


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Demand Forecasting Service on port 8006...")
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=True, log_level="info")
