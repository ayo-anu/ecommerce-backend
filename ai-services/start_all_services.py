#!/usr/bin/env python3
"""
Start All Services Script
Launches all 7 microservices + gateway in sequence
"""
import subprocess
import time
import sys
import os

SERVICES = [
    {"name": "Recommendation Engine", "port": 8001, "script": "start_recommendation_service.py"},
    {"name": "Search Engine", "port": 8002, "script": "start_search_service.py"},
    {"name": "Fraud Detection", "port": 8003, "script": "start_fraud_service.py"},
    {"name": "Chatbot RAG", "port": 8004, "script": "start_chatbot_service.py"},
    {"name": "Pricing Engine", "port": 8005, "script": "start_pricing_service.py"},
    {"name": "Demand Forecasting", "port": 8006, "script": "start_forecasting_service.py"},
    {"name": "Visual Recognition", "port": 8007, "script": "start_visual_service.py"},
    {"name": "API Gateway", "port": 8000, "script": "start_gateway.py"},
]


def print_banner():
    print("=" * 70)
    print("  E-COMMERCE AI PLATFORM - SERVICE LAUNCHER")
    print("  Starting all 7 microservices + gateway")
    print("=" * 70)
    print()


def start_service(service):
    """Start a single service"""
    print(f"Starting {service['name']} on port {service['port']}...")
    
    # Check if script exists
    if not os.path.exists(service['script']):
        print(f"  ❌ Error: {service['script']} not found!")
        return None
    
    try:
        # Start service in background
        process = subprocess.Popen(
            [sys.executable, service['script']],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if still running
        if process.poll() is None:
            print(f"  ✓ {service['name']} started (PID: {process.pid})")
            return process
        else:
            print(f"  ❌ {service['name']} failed to start")
            stdout, stderr = process.communicate()
            if stderr:
                print(f"  Error: {stderr[:200]}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error starting {service['name']}: {e}")
        return None


def main():
    print_banner()
    
    processes = []
    
    print("Note: Services will start in sequence with 2-second delays\n")
    
    for service in SERVICES:
        process = start_service(service)
        if process:
            processes.append({
                'name': service['name'],
                'port': service['port'],
                'process': process
            })
        time.sleep(1)  # Brief pause between starts
    
    print("\n" + "=" * 70)
    print(f"  {len(processes)} of {len(SERVICES)} services started successfully")
    print("=" * 70)
    print("\nService URLs:")
    
    for proc in processes:
        print(f"  • {proc['name']}: http://localhost:{proc['port']}")
        print(f"    Docs: http://localhost:{proc['port']}/docs")
    
    print("\n" + "=" * 70)
    print("Services are running! Press Ctrl+C to stop all services.")
    print("=" * 70)
    
    try:
        # Keep running
        while True:
            time.sleep(1)
            # Check if any process died
            for proc in processes:
                if proc['process'].poll() is not None:
                    print(f"\n⚠️  Warning: {proc['name']} stopped unexpectedly")
    
    except KeyboardInterrupt:
        print("\n\nStopping all services...")
        for proc in processes:
            print(f"  Stopping {proc['name']}...")
            proc['process'].terminate()
            proc['process'].wait(timeout=5)
        print("\n✓ All services stopped")


if __name__ == '__main__':
    main()
