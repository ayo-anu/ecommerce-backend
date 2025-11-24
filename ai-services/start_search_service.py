"""
Start Search Engine Service
Run this script to launch the search engine on port 8002
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🔍 STARTING SEARCH ENGINE SERVICE")
    print("=" * 60)
    print("Port: 8002")
    print("Features:")
    print("  ✓ Text Search (keyword matching)")
    print("  ✓ Semantic Search (intent understanding)")
    print("  ✓ Visual Search (image similarity)")
    print("  ✓ Hybrid Search (multi-modal fusion)")
    print("  ✓ Autocomplete")
    print("  ✓ Spell Correction")
    print("  ✓ Filter Extraction")
    print("=" * 60)
    print()
    
    uvicorn.run(
        "services.search_engine.main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
