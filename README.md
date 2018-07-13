# websocket-rpc

[![Build Status](https://travis-ci.org/guyingbo/websocket-rpc.svg?branch=master)](https://travis-ci.org/guyingbo/websocket-rpc)
[![Python Version](https://img.shields.io/pypi/pyversions/websocket-rpc.svg)](https://pypi.python.org/pypi/websocket-rpc)
[![Version](https://img.shields.io/pypi/v/websocket-rpc.svg)](https://pypi.python.org/pypi/websocket-rpc)
[![Format](https://img.shields.io/pypi/format/websocket-rpc.svg)](https://pypi.python.org/pypi/websocket-rpc)
[![License](https://img.shields.io/pypi/l/websocket-rpc.svg)](https://pypi.python.org/pypi/websocket-rpc)
[![codecov](https://codecov.io/gh/guyingbo/websocket-rpc/branch/master/graph/badge.svg)](https://codecov.io/gh/guyingbo/websocket-rpc)

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
    await rpc.close()


loop.run_until_complete(go())
```
