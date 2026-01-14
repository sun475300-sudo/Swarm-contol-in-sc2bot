#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for dashboard endpoints
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
ENDPOINTS = [
    "/api/game-state",
    "/api/combat-stats",
    "/api/learning-progress",
    "/api/code-health",
    "/api/bugs"
]

def test_rest_endpoints():
    """Test REST API endpoints"""
    print("=" * 60)
    print("Testing REST API Endpoints")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}\n")

    for endpoint in ENDPOINTS:
        try:
            url = f"{BASE_URL}{endpoint}"
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                print(f"? {endpoint}")
                print(f"  Response preview: {json.dumps(data, ensure_ascii=False)[:120]}...")
            else:
                print(f"? {endpoint} - Status {resp.status_code}")
        except Exception as e:
            print(f"? {endpoint} - Error: {e}")
        print()

def test_websocket():
    """Test WebSocket connection (basic)"""
    print("=" * 60)
    print("WebSocket Test (Informational)")
    print("=" * 60)
    print(f"URL: ws://localhost:8000/ws/game-status")
    print("Note: Run in browser console or use websocket-client library")
    print("""
    Example (Python):
    from websocket import create_connection
    ws = create_connection("ws://localhost:8000/ws/game-status")
    for i in range(3):
        result = ws.recv()
        print(result)
    ws.close()
    """)

def test_post_endpoints():
    """Test POST endpoints"""
    print("=" * 60)
    print("Testing POST Endpoints")
    print("=" * 60)

    endpoints_post = {
        "/api/code-scan": {}
    }

    for endpoint, payload in endpoints_post.items():
        try:
            url = f"{BASE_URL}{endpoint}"
            resp = requests.post(url, json=payload, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                print(f"? {endpoint}")
                print(f"  Response: {json.dumps(data, ensure_ascii=False)}")
            else:
                print(f"? {endpoint} - Status {resp.status_code}")
        except Exception as e:
            print(f"? {endpoint} - Error: {e}")
        print()

if __name__ == "__main__":
    try:
        print(f"Testing dashboard server at {BASE_URL}\n")
        test_rest_endpoints()
        test_post_endpoints()
        test_websocket()
        print("=" * 60)
        print("Test completed!")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\nTest interrupted")
