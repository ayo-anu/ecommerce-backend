"""
Start Chatbot RAG Service
Run this script to launch the chatbot service on port 8004
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🤖 STARTING CHATBOT RAG SERVICE")
    print("=" * 60)
    print("Port: 8004")
    print("Features:")
    print("  ✓ Conversational AI")
    print("  ✓ Retrieval-Augmented Generation (RAG)")
    print("  ✓ Vector Knowledge Base")
    print("  ✓ Intent Detection")
    print("  ✓ Multi-turn Conversations")
    print("  ✓ Context Awareness")
    print("  ✓ Product Q&A")
    print("  ✓ Order Tracking")
    print("  ✓ Suggested Actions")
    print("=" * 60)
    print()
    
    uvicorn.run(
        "services.chatbot_rag.main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )
