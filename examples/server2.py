import asyncio
import websockets
from wsrpc import WebsocketRPC


class SampleHandler:
    def __init__(self, rpc):
        self.remote = rpc

    async def add(self, a, b):
        await asyncio.sleep(5)
        return a + b

    async def test(self):
        return 23


async def go(ws, path):
    await WebsocketRPC(ws, SampleHandler).run()


start_server = websockets.serve(go, "127.0.0.1", 5555)
asyncio.get_event_loop().run_until_complete(start_server)
try:
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    pass
