#!/usr/bin/env python

# WS client example
import asyncio
import websockets
import json
from pprint import pprint


class Client(object):

    async def listen_for_responses(self):
        print("Listnening for responses")
        while True:
            await asyncio.sleep(0) # Just for a foothold into this method

            try:
                message = await self.ws.recv()
                print(f"< {message}")
                response_obj = json.loads(message)
                
                if "id" in response_obj:
                    self.pending_responses.update({response_obj["id"]: response_obj})
                    print(f"updated pending_responses: {self.pending_responses}")
            except Exception as e:
                print(f"There was an error {e}")
        

    async def get_specific_response(self, id):
        print("Looking for response")
        while True:
            await asyncio.sleep(0)

            if id in self.pending_responses:
                return self.pending_responses[id]
                    

    @classmethod
    async def create(cls, url):
        self = Client()
        self.ws = await websockets.client.connect(url)
        self.pending_responses = {}
        self.response_worker = asyncio.create_task(self.listen_for_responses())
        return self
    

    async def send_message(self):
        message = {
            "jsonrpc": "2.0",
            "method": "ping",
            "params": {"interval": 5000},
            "id": 0
        }
        json_message = json.dumps(message)

        await self.ws.send(json_message)
        print(f"> {json_message}")

        response = await self.get_specific_response(0)
        print(f"found response!: {response}")
        exit(0)


async def main():
    uri = "ws://localhost:8888/kurento"
    client = await Client.create(uri)
    await client.send_message()

asyncio.get_event_loop().run_until_complete(main())
asyncio.get_event_loop().run_forever()
