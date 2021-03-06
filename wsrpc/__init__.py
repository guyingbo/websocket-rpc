"""msgpack rpc over websockets"""
import asyncio
import inspect
import itertools
import logging
import typing

import msgpack  # type: ignore

logger = logging.getLogger(__name__)
__version__ = "0.0.6"


class RPCError(Exception):
    pass


class RemoteCallError(Exception):
    pass


class WebsocketRPC:
    REQUEST = 0
    RESPONSE = 1
    NOTIFY = 2
    client_task: typing.Optional[asyncio.Future]

    def __init__(
        self,
        ws,
        handler_cls: type = None,
        *,
        client_mode: bool = False,
        timeout: int = 10,
        http_request=None,
        method_prefix: str = "rpc_"
    ):
        self.ws = ws
        self.timeout = timeout
        self._packer = msgpack.Packer(use_bin_type=1)
        self._request_table: typing.Dict[int, asyncio.Future] = {}
        self._tasks: typing.Set[asyncio.Future] = set()
        self.notify = NotifyProxy(self)
        self.request = RequestProxy(self)
        self._iter = itertools.count()
        self.client_mode = client_mode
        self.max_id = 2 ** 32
        self.http_request = http_request
        self.method_prefix = method_prefix
        self.handler = handler_cls(self) if handler_cls else None
        self._exc_handlers: typing.List[typing.Callable] = []
        if self.client_mode:
            self.client_task = asyncio.ensure_future(self.run())
        else:
            self.client_task = None

    def _next_msgid(self) -> int:
        i = next(self._iter)
        if i < self.max_id:
            return i
        self._iter = itertools.count()
        return self._next_msgid()

    async def run(self) -> None:
        async for data in self.ws:
            try:
                await self._on_data(data)
            except Exception as e:
                logger.exception(e)
                for exc_handler in self._exc_handlers:
                    if asyncio.iscoroutinefunction(exc_handler):
                        await exc_handler(e)
                    else:
                        exc_handler(e)
        try:
            await asyncio.shield(self._join())
        except asyncio.CancelledError:
            await self._join()

    async def close(self) -> None:
        if self.client_mode:
            await self.ws.close()
        if self.client_task:
            await self.client_task

    async def _join(self) -> None:
        if self._tasks:
            await asyncio.wait(self._tasks, timeout=self.timeout)

    def exception(self, func: typing.Callable) -> None:
        self._exc_handlers.append(func)

    async def _on_data(self, data: bytes) -> None:
        msg = msgpack.unpackb(data)
        assert type(msg) == list, "unknown message format"
        assert len(msg) > 0, "error message length"
        msgtype = msg[0]
        task: typing.Optional[asyncio.Future]
        if msgtype == self.REQUEST:
            msgid, method_name, params = msg[1:]
            method_name = method_name
            task = asyncio.ensure_future(self._on_request(msgid, method_name, params))
        elif msgtype == self.RESPONSE:
            msgid, error, result = msg[1:]
            self._on_response(msgid, error, result)
            task = None
        elif msgtype == self.NOTIFY:
            method_name, params = msg[1:]
            method_name = method_name
            task = asyncio.ensure_future(self._on_notify(method_name, params))
        else:
            raise RPCError("unknown msgtype")
        if task:
            self._tasks.add(task)
            task.add_done_callback(self._tasks.remove)

    async def _on_request(self, msgid: int, method_name: str, params: tuple) -> None:
        try:
            method_name = self.method_prefix + method_name
            method = getattr(self.handler, method_name)
            result = method(*params)
            # if asyncio.iscoroutine(result):
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            await self._send_response(msgid, 1, str(e))
        else:
            await self._send_response(msgid, 0, result)

    def _on_response(self, msgid: int, error: int, result) -> None:
        fut = self._request_table.pop(msgid)
        if error == 0:
            fut.set_result(result)
        else:
            fut.set_exception(RemoteCallError(error, result))

    async def _on_notify(self, method_name: str, params: tuple) -> None:
        method_name = self.method_prefix + method_name
        method = getattr(self.handler, method_name)
        result = method(*params)
        # if asyncio.iscoroutine(result):
        if inspect.isawaitable(result):
            result = await result

    async def _send_response(self, msgid: int, error: int, result) -> None:
        message = [self.RESPONSE, msgid, error, result]
        data = self._packer.pack(message)
        await self.ws.send(data)

    async def _send_request(self, method: str, params: tuple) -> typing.Any:
        msgid = self._next_msgid()
        message = [self.REQUEST, msgid, method, params]
        data = self._packer.pack(message)
        fut: asyncio.Future = asyncio.Future()
        self._request_table[msgid] = fut
        await self.ws.send(data)
        return await fut

    async def _send_notify(self, method: str, params: tuple) -> None:
        message = [self.NOTIFY, method, params]
        data = self._packer.pack(message)
        await self.ws.send(data)


class NotifyProxy:
    __slots__ = ("rpc",)

    def __init__(self, rpc: WebsocketRPC):
        self.rpc = rpc

    def __getattr__(self, name: str):
        async def func(*args):
            await self.rpc._send_notify(name, args)

        return func


class RequestProxy:
    __slots__ = ("rpc",)

    def __init__(self, rpc: WebsocketRPC):
        self.rpc = rpc

    def __getattr__(self, name: str):
        async def func(*args):
            return await self.rpc._send_request(name, args)

        return func
