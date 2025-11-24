"""
Start Fraud Detection Service
Run this script to launch the fraud detection service on port 8003
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🛡️ STARTING FRAUD DETECTION SERVICE")
    print("=" * 60)
    print("Port: 8003")
    print("Features:")
    print("  ✓ Real-time Fraud Detection")
    print("  ✓ ML Anomaly Detection (Isolation Forest)")
    print("  ✓ Rule-Based Expert System (10+ rules)")
    print("  ✓ Velocity Checks")
    print("  ✓ Device Fingerprinting")
    print("  ✓ Risk Scoring (0-100)")
    print("  ✓ Auto Decision Engine (Approve/Review/Decline)")
    print("  ✓ Batch Processing")
    print("=" * 60)
    print()
    
    uvicorn.run(
        "services.fraud_detection.main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )
