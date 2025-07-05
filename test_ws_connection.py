#!/usr/bin/env python3
"""Quick test of the WebSocket endpoint"""

import asyncio
import websockets
import json

async def test_websocket():
    """Test the WebSocket endpoint"""
    uri = "ws://127.0.0.1:8000/ws/chat"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")

            # Wait for welcome message
            welcome = await websocket.recv()
            print(f"📨 Welcome: {welcome}")

            # Send a test message
            test_message = {
                "action": "chat",
                "request_id": "test-123",
                "payload": {"message": "Hello from test client"}
            }

            await websocket.send(json.dumps(test_message))
            print(f"📤 Sent: {test_message}")

            # Receive responses
            for _ in range(5):  # Get a few responses
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"📥 Response: {response}")
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break

    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
