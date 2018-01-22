# websocket-rpc
msgpack rpc over websocket

## Examples

server:
```python
import asyncio
from sanic import Sanic
from wsrpc import WebsocketRPC
app = Sanic(__name__)


class SampleHandler:
    def __init__(self, rpc):
        self.remote = rpc

    async def add(self, a, b):
        await asyncio.sleep(5)
        return a + b

    async def test(self):
        return 23


@app.websocket('/')
async def home(request, ws):
    await WebsocketRPC(ws, SampleHandler).run()
app.run(host="0.0.0.0", port=5555, debug=False)
```

client:
```python
import asyncio
import websockets
from wsrpc import WebsocketRPC
loop = asyncio.get_event_loop()


async def go():
    async with websockets.connect('ws://127.0.0.1:5555/') as ws:
        rpc = WebsocketRPC(ws=ws, client_mode=True)
        jobs = [rpc.request.add(a, b) for a, b in zip(range(10), range(5, 15))]
        r = await asyncio.gather(*jobs)
        print(r)
        r = await rpc.notify.add(2, 3)
        print(r)


loop.run_until_complete(go())
```
