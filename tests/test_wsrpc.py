import pytest
import msgpack
import asyncio
import websockets
import wsrpc


class SampleHandler:
    def __init__(self, rpc):
        self.remote = rpc

    async def rpc_add(self, a, b):
        await asyncio.sleep(0.001)
        return a + b

    async def rpc_foo(self):
        await asyncio.sleep(1)


async def run_client(port):
    async with websockets.connect(f"ws://127.0.0.1:{port}/") as ws:
        client = wsrpc.WebsocketRPC(ws=ws, client_mode=True)
        client.max_id = 5
        for i in range(10):
            r = await client.request.add(3, i)
            assert r == 3 + i
        r = await client.notify.add(3, 4)
        assert r is None
        await ws.send(msgpack.packb([3, "a"]))
        with pytest.raises(wsrpc.RemoteCallError):
            r = await client.request.none(3, 5)
        await client.notify.foo()
    await client.close()


async def go(ws, path):
    rpc = wsrpc.WebsocketRPC(ws, SampleHandler)

    @rpc.exception
    def exc_handler(e):
        pass

    @rpc.exception
    async def async_exc_handler(e):
        pass

    await rpc.run()


def test_rpc(unused_tcp_port):
    start_server = websockets.serve(go, "127.0.0.1", unused_tcp_port)
    loop = asyncio.get_event_loop()
    server = loop.run_until_complete(start_server)
    loop.run_until_complete(run_client(unused_tcp_port))
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
