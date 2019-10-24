#!/usr/bin/env python

# WS client example
import asyncio
import websockets
import json


async def hello():
    """ Simple test that sends a JSON-RPC message to the server.
        Just to check if it is possible to create a Python client for
        interacting with Kurento
    """
    uri = "ws://localhost:8888/kurento"
    async with websockets.connect(uri) as websocket:
        message = {
            "jsonrpc": "2.0",
            "method": "ping",
            "params": {"interval": 5000},
            "id": 0
        }
        json_message = json.dumps(message)

        await websocket.send(json_message)
        print(f"> {json_message}")

        greeting = await websocket.recv()
        print(f"< {greeting}")

asyncio.get_event_loop().run_until_complete(hello())
