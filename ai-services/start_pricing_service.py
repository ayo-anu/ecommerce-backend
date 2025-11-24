"""
Start Pricing Engine Service
Run this script to launch the pricing engine on port 8005
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("💰 STARTING PRICING ENGINE SERVICE")
    print("=" * 60)
    print("Port: 8005")
    print("Features:")
    print("  ✓ Dynamic Pricing Algorithm")
    print("  ✓ Competitor Price Analysis")
    print("  ✓ Discount Optimization")
    print("  ✓ Price Elasticity Calculation")
    print("  ✓ A/B Testing")
    print("  ✓ Revenue Maximization")
    print("  ✓ Margin Protection")
    print("  ✓ Demand-based Pricing")
    print("  ✓ Bulk Pricing Updates")
    print("=" * 60)
    print()
    
    uvicorn.run(
        "services.pricing_engine.main:app",
        host="0.0.0.0",
        port=8005,
        reload=True,
        log_level="info"
    )
