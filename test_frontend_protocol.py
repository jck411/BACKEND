#!/usr/bin/env python3
"""Test frontend protocol compatibility"""

import asyncio
import websockets
import json

async def test_frontend_protocol():
    """Test with frontend message format"""
    uri = "ws://127.0.0.1:8000/ws/chat"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")

            # Wait for welcome message
            welcome = await websocket.recv()
            print(f"📨 Welcome: {welcome}")

            # Send a test message in frontend format
            test_message = {
                "type": "text_message",
                "id": "test-frontend-123",
                "content": "Hello from frontend format"
            }

            await websocket.send(json.dumps(test_message))
            print(f"📤 Sent: {test_message}")

            # Receive responses
            for i in range(10):  # Get more responses
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    parsed = json.loads(response)
                    print(f"📥 Response {i+1}: type={parsed.get('type')}, content={parsed.get('content', '')[:50]}...")
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
                except json.JSONDecodeError:
                    print(f"📥 Raw response {i+1}: {response}")

    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_frontend_protocol())
