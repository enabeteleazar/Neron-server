#!/usr/bin/env python3
"""
Test script for Neron API endpoints
Tests:
1. GET /
2. GET /status
3. POST /chat
4. POST /input/text (all modes)
"""

import asyncio
import json
import sys
sys.path.insert(0, "/mnt/usb-storage/neron/server")

import httpx
from core.config import settings

BASE_URL = f"http://localhost:{settings.SERVER_PORT}"
API_KEY = settings.API_KEY
TIMEOUT = 10.0

async def test_endpoints():
    """Test all API endpoints"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        
        # Test 1: GET /
        print("\n✓ Testing GET /")
        try:
            resp = await client.get("/")
            print(f"  Status: {resp.status_code}")
            print(f"  Response: {resp.json()}")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        except Exception as e:
            print(f"  ❌ Error: {e}")
            
        # Test 2: GET /status
        print("\n✓ Testing GET /status")
        try:
            resp = await client.get("/status")
            print(f"  Status: {resp.status_code}")
            print(f"  Response: {resp.json()}")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        except Exception as e:
            print(f"  ❌ Error: {e}")
            
        # Test 3: POST /chat
        print("\n✓ Testing POST /chat")
        try:
            payload = {
                "message": "Bonjour, comment tu vas?",
                "context": "test"
            }
            headers = {"X-API-Key": API_KEY} if API_KEY else {}
            resp = await client.post("/chat", json=payload, headers=headers)
            print(f"  Status: {resp.status_code}")
            print(f"  Response: {resp.json()}")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        except Exception as e:
            print(f"  ❌ Error: {e}")
            
        # Test 4: POST /input/text - default mode
        print("\n✓ Testing POST /input/text (default mode)")
        try:
            payload = {
                "text": "Quel est ton nom?",
                "mode": "default",
                "context": "test"
            }
            headers = {"X-API-Key": API_KEY} if API_KEY else {}
            resp = await client.post("/input/text", json=payload, headers=headers)
            print(f"  Status: {resp.status_code}")
            print(f"  Response: {resp.json()}")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()
            assert "response" in data
            assert "success" in data
            assert "mode" in data
        except Exception as e:
            print(f"  ❌ Error: {e}")
            
        # Test 5: POST /input/text - plan mode
        print("\n✓ Testing POST /input/text (plan mode)")
        try:
            payload = {
                "text": "Comment faire un gâteau?",
                "mode": "plan",
                "context": "test"
            }
            headers = {"X-API-Key": API_KEY} if API_KEY else {}
            resp = await client.post("/input/text", json=payload, headers=headers)
            print(f"  Status: {resp.status_code}")
            data = resp.json()
            print(f"  Response fields: {list(data.keys())}")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert "response" in data
            assert "success" in data
            assert "mode" in data
            assert data["mode"] == "plan"
        except Exception as e:
            print(f"  ❌ Error: {e}")
            
        # Test 6: POST /input/text - empty text
        print("\n✓ Testing POST /input/text (empty text)")
        try:
            payload = {
                "text": "",
                "mode": "default"
            }
            headers = {"X-API-Key": API_KEY} if API_KEY else {}
            resp = await client.post("/input/text", json=payload, headers=headers)
            print(f"  Status: {resp.status_code}")
            data = resp.json()
            print(f"  Response: {data['response']}")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert data["success"] == False
            assert "Aucun texte" in data["response"]
        except Exception as e:
            print(f"  ❌ Error: {e}")
            
        # Test 7: POST /input/stream - default mode (streaming)
        print("\n✓ Testing POST /input/stream (default mode)")
        try:
            payload = {
                "text": "Bonjour",
                "mode": "default",
                "context": "test"
            }
            headers = {"X-API-Key": API_KEY} if API_KEY else {}
            resp = await client.post("/input/stream", json=payload, headers=headers)
            print(f"  Status: {resp.status_code}")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            
            # Pour le streaming, on reçoit NDJSON
            stream_lines = []
            async for line in resp.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        stream_lines.append(data)
                        print(f"    Chunk: {data.get('type')} - {data.get('data', data.get('message', ''))[:50]}")
                    except json.JSONDecodeError:
                        print(f"    Invalid JSON: {line[:50]}")
            
            assert len(stream_lines) > 0, "No stream data received"
            print(f"  Total chunks: {len(stream_lines)}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        print("\n✅ All tests completed!")

if __name__ == "__main__":
    try:
        asyncio.run(test_endpoints())
    except KeyboardInterrupt:
        print("\n⏹ Tests interrupted")
        sys.exit(0)
