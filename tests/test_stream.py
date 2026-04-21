#!/usr/bin/env python3
"""
Test script for /input/stream endpoint
Tests NDJSON streaming response
"""

import asyncio
import json
import sys
sys.path.insert(0, "/mnt/usb-storage/neron/server")

import httpx
from serverVNext.serverVNext.core.config import settings

BASE_URL = f"http://localhost:{settings.SERVER_PORT}"
API_KEY = settings.API_KEY
TIMEOUT = 30.0

async def test_stream():
    """Test streaming endpoint"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        
        # Test 1: Stream default mode
        print("\n✓ Testing POST /input/stream (default mode)")
        try:
            payload = {
                "text": "Dis bonjour et présente-toi",
                "mode": "default",
                "context": "test"
            }
            headers = {"X-API-Key": API_KEY} if API_KEY else {}
            
            chunk_count = 0
            error_msg = None
            complete = False
            
            async with client.stream(
                "POST", 
                "/input/stream", 
                json=payload, 
                headers=headers
            ) as resp:
                print(f"  Status: {resp.status_code}")
                assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
                
                print("  Stream content:")
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            msg_type = data.get("type")
                            
                            if msg_type == "chunk":
                                print(f"    {data.get('data')}", end="", flush=True)
                                chunk_count += 1
                            elif msg_type == "metadata":
                                print(f"\n  [Metadata: intent={data.get('intent')}, confidence={data.get('confidence')}]")
                            elif msg_type == "complete":
                                complete = True
                                print(f"\n  [Complete]")
                            elif msg_type == "error":
                                error_msg = data.get("message")
                                print(f"\n  [Error: {error_msg}]")
                        except json.JSONDecodeError as e:
                            print(f"\n  Invalid JSON: {line[:50]}")
                
                print(f"\n  Chunks received: {chunk_count}")
                if error_msg:
                    print(f"  Error: {error_msg}")
                print(f"  Stream complete: {complete}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()

        # Test 2: Stream plan mode
        print("\n✓ Testing POST /input/stream (plan mode)")
        try:
            payload = {
                "text": "Comment faire un gâteau?",
                "mode": "plan"
            }
            headers = {"X-API-Key": API_KEY} if API_KEY else {}
            
            chunk_count = 0
            async with client.stream(
                "POST", 
                "/input/stream", 
                json=payload, 
                headers=headers
            ) as resp:
                print(f"  Status: {resp.status_code}")
                async for line in resp.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        if data["type"] == "chunk":
                            chunk_count += 1
                
                print(f"  Chunks: {chunk_count}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

        # Test 3: Stream with empty text
        print("\n✓ Testing POST /input/stream (empty text - error test)")
        try:
            payload = {"text": "", "mode": "default"}
            headers = {"X-API-Key": API_KEY} if API_KEY else {}
            
            async with client.stream(
                "POST", 
                "/input/stream", 
                json=payload, 
                headers=headers
            ) as resp:
                print(f"  Status: {resp.status_code}")
                async for line in resp.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        if data["type"] == "error":
                            print(f"  Expected error: {data['message']}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

        print("\n✅ All stream tests completed!")

if __name__ == "__main__":
    try:
        asyncio.run(test_stream())
    except KeyboardInterrupt:
        print("\n⏹ Tests interrupted")
        sys.exit(0)
