#!/usr/bin/env python3
"""
Enhanced WebSocket client to test different Router actions.

Added 2025-07-05: Test client for Router functionality.
"""

import asyncio
import json

import websockets  # type: ignore


async def test_chat():
    """Test chat functionality."""
    print("=== Testing Chat Action ===")
    uri = "ws://127.0.0.1:8000/ws"

    async with websockets.connect(uri) as websocket:
        # Skip welcome message
        await websocket.recv()

        # Send chat message
        chat_message = {
            "action": "chat",
            "payload": {"text": "What can you help me with?"},
            "request_id": "chat-test-001"
        }

        print(f"Sending: {chat_message['action']}")
        await websocket.send(json.dumps(chat_message))

        # Receive responses
        while True:
            response = await websocket.recv()
            data = json.loads(response)

            if data['status'] == 'chunk' and data.get('chunk'):
                print(f"Chat chunk: {data['chunk']['data']}")
            elif data['status'] == 'complete':
                print("Chat complete!\n")
                break


async def test_image_generation():
    """Test image generation functionality."""
    print("=== Testing Image Generation Action ===")
    uri = "ws://127.0.0.1:8000/ws"

    async with websockets.connect(uri) as websocket:
        # Skip welcome message
        await websocket.recv()

        # Send image generation message
        image_message = {
            "action": "generate_image",
            "payload": {"prompt": "A beautiful sunset over mountains"},
            "request_id": "image-test-001"
        }

        print(f"Sending: {image_message['action']}")
        await websocket.send(json.dumps(image_message))

        # Receive responses
        while True:
            response = await websocket.recv()
            data = json.loads(response)

            if data['status'] == 'chunk' and data.get('chunk'):
                print(f"Image chunk: {data['chunk']['data']}")
            elif data['status'] == 'complete':
                print("Image generation complete!\n")
                break


async def test_device_control():
    """Test device control functionality."""
    print("=== Testing Device Control Action ===")
    uri = "ws://127.0.0.1:8000/ws"

    async with websockets.connect(uri) as websocket:
        # Skip welcome message
        await websocket.recv()

        # Send device control message
        device_message = {
            "action": "device_control",
            "payload": {"device_id": "living_room_light", "action": "turn_on"},
            "request_id": "device-test-001"
        }

        print(f"Sending: {device_message['action']}")
        await websocket.send(json.dumps(device_message))

        # Receive responses
        while True:
            response = await websocket.recv()
            data = json.loads(response)

            if data['status'] == 'chunk' and data.get('chunk'):
                print(f"Device chunk: {data['chunk']['data']}")
            elif data['status'] == 'complete':
                print("Device control complete!\n")
                break


async def main():
    """Test all Router actions."""
    print("Testing Router Integration with Multiple Actions\n")

    try:
        await test_chat()
        await test_image_generation()
        await test_device_control()

        print("✅ All Router actions tested successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
