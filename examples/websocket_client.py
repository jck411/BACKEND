#!/usr/bin/env python3
"""
Example WebSocket client for testing the gateway.

This is an example/demo file, not part of the main codebase.
Added 2025-07-05: Manual test client for WebSocket functionality.
"""

import asyncio
import json

import websockets  # type: ignore


async def test_websocket():
    """Test WebSocket connection and message handling."""
    uri = "ws://127.0.0.1:8000/ws"

    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            # Receive welcome message
            welcome = await websocket.recv()
            print(f"Received welcome: {welcome}")

            # Send a test message
            test_message = {
                "action": "chat",
                "payload": {"text": "Hello from test client!"},
                "request_id": "test-client-001",
            }

            print(f"Sending message: {json.dumps(test_message, indent=2)}")
            await websocket.send(json.dumps(test_message))

            # Receive responses
            print("\nReceiving responses:")
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    print(f"Status: {data['status']}")

                    if data.get("chunk"):
                        print(f"Chunk: {data['chunk']['data']}")

                    if data["status"] == "complete":
                        print("Message processing complete!")
                        break

                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
                except Exception as e:
                    print(f"Error: {e}")
                    break

    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
