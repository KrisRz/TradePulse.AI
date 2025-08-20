#!/usr/bin/env python3
"""Test Trading Brain Endpoints"""

import requests
import json
import time

def test_endpoints():
    base_url = "http://localhost:9002"
    
    print("🧠 Testing Trading Brain Endpoints")
    print("=" * 50)
    
    # Test health
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"Health: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Health failed: {e}")
        return
    
    # Test brain status
    try:
        response = requests.get(f"{base_url}/api/trading/brain/status", timeout=10)
        print(f"Status: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Status failed: {e}")
    
    # Test brain toggle
    try:
        response = requests.post(
            f"{base_url}/api/trading/brain/toggle",
            headers={"Content-Type": "application/json"},
            json={"enabled": True},
            timeout=10
        )
        print(f"Toggle: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Toggle failed: {e}")

if __name__ == "__main__":
    test_endpoints()