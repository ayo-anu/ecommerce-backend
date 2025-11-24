"""
Start Demand Forecasting Service
Port: 8006
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("📈 STARTING DEMAND FORECASTING SERVICE")
    print("=" * 60)
    print("Port: 8006")
    print("Features:")
    print("  ✓ Time Series Forecasting (4 methods)")
    print("  ✓ Seasonality Detection")
    print("  ✓ Trend Analysis")
    print("  ✓ Inventory Optimization")
    print("  ✓ Promotional Impact Analysis")
    print("  ✓ Anomaly Detection")
    print("  ✓ Forecast Accuracy Evaluation")
    print("=" * 60)
    print()
    
    uvicorn.run(
        "services.demand_forecasting.main:app",
        host="0.0.0.0",
        port=8006,
        reload=True,
        log_level="info"
    )
