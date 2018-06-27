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


@app.websocket("/")
async def home(request, ws):
    await WebsocketRPC(ws, SampleHandler).run()


app.run(host="0.0.0.0", port=5555, debug=False)
