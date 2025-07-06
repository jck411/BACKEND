#!/usr/bin/env python3
"""
Simple WebSocket client for testing real chat functionality.

Usage:
    python examples/websocket_client.py
"""

import asyncio
import json
import uuid

import websockets  # type: ignore


async def test_simple_chat():
    """Test basic chat functionality with OpenAI."""
    uri = "ws://127.0.0.1:8000/ws/chat"

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")

            # Wait for welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"Welcome: {welcome_data.get('status', 'unknown')}")

            # Test chat message
            chat_message = {
                "action": "chat",
                "payload": {"text": "Hello! Please tell me a short joke."},
                "request_id": str(uuid.uuid4())
            }

            print(f"\n📤 Sending: {chat_message['payload']['text']}")
            await websocket.send(json.dumps(chat_message))

            print("📥 Receiving response:")
            response_content = ""

            async for message in websocket:
                try:
                    response = json.loads(message)
                    status = response.get('status', 'unknown')

                    if status == 'chunk':
                        chunk = response.get('chunk', {})
                        if chunk.get('type') == 'text':
                            content = chunk.get('data', '')
                            response_content += content
                            print(content, end='', flush=True)

                    elif status == 'complete':
                        print("\n\n✅ Chat completed!")
                        print(f"📊 Full response: {response_content}")
                        break

                    elif status == 'error':
                        print(f"\n❌ Error: {response.get('error', 'Unknown error')}")
                        break

                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse JSON: {e}")
                    print(f"Raw message: {message}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_simple_chat())
