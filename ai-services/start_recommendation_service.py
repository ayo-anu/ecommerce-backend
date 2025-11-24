#!/usr/bin/env python3
"""
Start the Recommendation Engine Service
"""
import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 STARTING RECOMMENDATION ENGINE SERVICE")
    print("=" * 70)
    print("\n📍 URL: http://localhost:8001")
    print("📚 Docs: http://localhost:8001/docs")
    print("💚 Health: http://localhost:8001/health")
    print("\n" + "=" * 70 + "\n")
    
    uvicorn.run(
        "services.recommendation_engine.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
