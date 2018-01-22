import asyncio
import websockets
from wsrpc import WebsocketRPC
loop = asyncio.get_event_loop()


async def go():
    async with websockets.connect('ws://127.0.0.1:5555/') as ws:
        rpc = WebsocketRPC(ws=ws, client_mode=True)
        r = await rpc.request.add(2, 3)
        print(r)
        r = await rpc.notify.add(2, 3)
        print(r)


loop.run_until_complete(go())
