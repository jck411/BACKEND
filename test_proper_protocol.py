#!/usr/bin/env python3
"""Test proper backend protocol"""

import asyncio
import websockets
import json

async def test_proper_protocol():
    """Test with proper backend message format"""
    uri = "ws://127.0.0.1:8000/ws/chat"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")

            # Wait for welcome message
            welcome = await websocket.recv()
            print(f"📨 Welcome: {welcome}")

            # Send a test message in proper backend format
            test_message = {
                "action": "chat",
                "request_id": "proper-test-123",
                "payload": {"message": "Hello with proper protocol"}
            }

            await websocket.send(json.dumps(test_message))
            print(f"📤 Sent: {test_message}")

            # Receive responses
            for i in range(10):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    parsed = json.loads(response)
                    print(f"📥 Response {i+1}: status={parsed.get('status')}")
                    if parsed.get('chunk'):
                        chunk = parsed['chunk']
                        print(f"    Chunk type: {chunk.get('type')}, content: {str(chunk.get('data', ''))[:50]}...")
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break

    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_proper_protocol())
