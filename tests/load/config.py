"""
Load Testing Configuration
"""

# Target URLs
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"
API_GATEWAY_URL = "http://localhost:8080"

# Test scenarios
SCENARIOS = {
    "smoke": {
        "users": 10,
        "spawn_rate": 2,
        "run_time": "2m",
        "description": "Quick smoke test with minimal load"
    },
    "baseline": {
        "users": 50,
        "spawn_rate": 5,
        "run_time": "10m",
        "description": "Baseline performance test"
    },
    "stress": {
        "users": 200,
        "spawn_rate": 20,
        "run_time": "15m",
        "description": "Stress test to find breaking points"
    },
    "spike": {
        "users": 500,
        "spawn_rate": 100,
        "run_time": "5m",
        "description": "Sudden traffic spike (flash sale simulation)"
    },
    "endurance": {
        "users": 100,
        "spawn_rate": 10,
        "run_time": "60m",
        "description": "Extended test for memory leaks and stability"
    }
}

# Performance thresholds
THRESHOLDS = {
    "response_time_p95": 1000,  # 95th percentile response time in ms
    "response_time_p99": 2000,  # 99th percentile response time in ms
    "error_rate": 1.0,           # Maximum acceptable error rate (%)
    "throughput": 100,           # Minimum requests per second
}

# AI Service specific thresholds (longer acceptable response times)
AI_THRESHOLDS = {
    "response_time_p95": 3000,
    "response_time_p99": 5000,
    "error_rate": 2.0,
}
