#!/usr/bin/env python3
"""
Start the API Gateway
"""
import uvicorn
from shared.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 STARTING API GATEWAY")
    print("=" * 70)
    print(f"\n📍 URL: http://{settings.GATEWAY_HOST}:{settings.GATEWAY_PORT}")
    print(f"📚 Docs: http://{settings.GATEWAY_HOST}:{settings.GATEWAY_PORT}/docs")
    print(f"💚 Health: http://{settings.GATEWAY_HOST}:{settings.GATEWAY_PORT}/health")
    print(f"📊 Metrics: http://{settings.GATEWAY_HOST}:{settings.GATEWAY_PORT}/metrics")
    print("\n" + "=" * 70 + "\n")
    
    uvicorn.run(
        "api_gateway.main:app",
        host=settings.GATEWAY_HOST,
        port=settings.GATEWAY_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
