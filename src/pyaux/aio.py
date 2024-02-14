"""
...
"""
from __future__ import annotations

import asyncio
import types
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from typing import Any, TypeVar, overload

__all__ = ("_await",)

TRet = TypeVar("TRet")


@overload
def _await(coro: types.CoroutineType[TRet, None, None]) -> TRet:
    ...


@overload
def _await(awaitable: Callable[..., Awaitable[TRet]], *args: Any, **kwargs: Any) -> TRet:
    ...


def _await(*args: Any, **kwargs: Any) -> Any:
    """
    Run an function from a synchronous code, in a new event loop, and await its
    result.

    Intended for debugging asyncs e.g. from ipython.

    Usage:

        result = _await(awaitable, *args, **kwargs)

    Also usable:

        result = _await(awaitable(*args, **kwargs))

    See also:

      * https://github.com/django/asgiref/blob/master/asgiref/sync.py
      * https://stackoverflow.com/a/48479665
      * https://github.com/ipython/ipython/pull/11155
      * `asyncio.run`
    """
    awaitable, args = args[0], args[1:]

    call_result: Future[Any] = Future()
    if isinstance(awaitable, types.CoroutineType):
        assert not args
        assert not kwargs
        cor = awaitable
    else:
        cor = awaitable(*args, **kwargs)

    async def wrap() -> None:
        try:
            result = await cor
        except Exception as exc:
            call_result.set_exception(exc)
        else:
            call_result.set_result(result)

    try:
        main_loop = asyncio.get_event_loop()
    except RuntimeError:
        main_loop = None
    if main_loop and main_loop.is_running():
        raise RuntimeError(
            "There's already a running loop, you probably shouldn't use this wrapper"
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(wrap())
    finally:
        try:
            if hasattr(loop, "shutdown_asyncgens"):
                loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
            asyncio.set_event_loop(main_loop)

    return call_result.result()
