import asyncio
import msgpack
import logging
import itertools
logger = logging.getLogger(__name__)
__version__ = '0.0.2'


class RPCError(Exception):
    pass


class RemoteCallError(Exception):
    pass


class NotifyProxy:
    def __init__(self, rpc):
        self.rpc = rpc

    def __getattr__(self, name):
        async def func(*args):
            await self.rpc.send_notify(name, args)
        return func


class RequestProxy:
    def __init__(self, rpc):
        self.rpc = rpc

    def __getattr__(self, name):
        async def func(*args):
            return await self.rpc.send_request(name, args)
        return func


class WebsocketRPC:
    REQUEST = 0
    RESPONSE = 1
    NOTIFY = 2

    def __init__(self, ws, handler_cls=None, *, client_mode=False, timeout=10,
                 http_request=None):
        self.ws = ws
        self.timeout = timeout
        self.packer = msgpack.Packer(use_bin_type=1)
        self._request_table = {}
        self.tasks = set()
        self.notify = NotifyProxy(self)
        self.request = RequestProxy(self)
        self.iter = itertools.count()
        self.client_mode = client_mode
        self.max_id = 2 ** 32
        self.http_request = http_request
        self.handler = handler_cls(self) if handler_cls else None
        if self.client_mode:
            asyncio.ensure_future(self.run())

    def next_msgid(self):
        i = next(self.iter)
        if i < self.max_id:
            return i
        self.iter = itertools.count()
        return self.next_msgid()

    async def run(self):
        async for data in self.ws:
            try:
                await self.on_data(data)
            except Exception as e:
                logger.exception(e)
        if self.tasks:
            await asyncio.wait(self.tasks, timeout=self.timeout)

    async def on_data(self, data):
        msg = msgpack.unpackb(data, encoding='utf-8')
        assert type(msg) == list, 'unknown message format'
        assert len(msg) > 0, 'error message length'
        msgtype = msg[0]
        if msgtype == self.REQUEST:
            msgid, method_name, params = msg[1:]
            method_name = method_name
            task = asyncio.ensure_future(
                    self.on_request(msgid, method_name, params))
        elif msgtype == self.RESPONSE:
            msgid, error, result = msg[1:]
            self.on_response(msgid, error, result)
            task = None
        elif msgtype == self.NOTIFY:
            method_name, params = msg[1:]
            method_name = method_name
            task = asyncio.ensure_future(self.on_notify(method_name, params))
        else:
            raise RPCError('unknown msgtype')
        if task:
            self.tasks.add(task)
            task.add_done_callback(self.tasks.remove)

    async def on_request(self, msgid, method_name, params):
        try:
            method = getattr(self.handler, method_name)
            result = method(*params)
            if asyncio.iscoroutine(result):
                result = await result
        except Exception as e:
            await self.send_response(msgid, 1, str(e))
        else:
            await self.send_response(msgid, 0, result)

    def on_response(self, msgid, error, result):
        fut = self._request_table.pop(msgid)
        if error == 0:
            fut.set_result(result)
        else:
            fut.set_exception(RemoteCallError(error, result))

    async def on_notify(self, method_name, params):
        method = getattr(self.handler, method_name)
        result = method(*params)
        if asyncio.iscoroutine(result):
            result = await result

    async def send_response(self, msgid, error, result):
        message = [self.RESPONSE, msgid, error, result]
        data = self.packer.pack(message)
        await self.ws.send(data)

    async def send_request(self, method, params):
        msgid = self.next_msgid()
        message = [self.REQUEST, msgid, method, params]
        data = self.packer.pack(message)
        await self.ws.send(data)
        fut = asyncio.Future()
        self._request_table[msgid] = fut
        return await fut

    async def send_notify(self, method, params):
        message = [self.NOTIFY, method, params]
        data = self.packer.pack(message)
        await self.ws.send(data)
