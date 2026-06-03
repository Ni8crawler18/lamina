"""Async helpers."""

import asyncio
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


async def run_chain(fn: Callable[..., T], *args, **kwargs) -> T:
    """Run a blocking chain-adapter call off the event loop.

    web3 / hiero SDKs are synchronous and a transaction can block for seconds;
    offloading to a thread keeps the API responsive under concurrency.
    """
    return await asyncio.to_thread(fn, *args, **kwargs)
