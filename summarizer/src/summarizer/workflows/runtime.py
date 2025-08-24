"""
This module export the Dapr Workflow Runtime as a singleton
"""
import asyncio
import contextvars
from functools import wraps
from threading import Thread
from typing import Any, Callable, Coroutine, Optional, TypeVar

from dapr.ext.workflow import WorkflowRuntime

wfr = WorkflowRuntime()


T = TypeVar("T")


def async_activity(_func: Optional[Callable[..., Coroutine[Any, Any, T]]] = None, *, name: Optional[str] = None):
    """
    Decorator to register an async function as a Dapr workflow activity.
    - If no event loop is running: use asyncio.run(coro)
    - If an event loop is running: run the coro in a fresh loop on a worker thread
    - Copies contextvars for tracing/telemetry continuity
    - Optional: @async_activity(name="my-activity")

    Usage:
        @async_activity
        async def my_activity(...): ...

        @async_activity(name="transcribe-audio")
        async def transcribe_audio(...): ...
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]):
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # Preserve context (e.g., OpenTelemetry)
            ctx = contextvars.copy_context()

            # Case 1: No running loop → safe to use asyncio.run
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                # no running loop in this thread
                return asyncio.run(ctx.run(func, *args, **kwargs))

            # Case 2: A loop is already running in this thread
            # → run in a dedicated loop on a worker thread and block until done
            result_container: dict[str, Any] = {}
            exc_container: dict[str, BaseException] = {}

            def runner():
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    result_container["result"] = loop.run_until_complete(
                        ctx.run(func, *args, **kwargs))
                except BaseException as e:
                    exc_container["exc"] = e
                finally:
                    try:
                        loop.run_until_complete(asyncio.sleep(0))
                    finally:
                        loop.close()

            t = Thread(target=runner, daemon=True)
            t.start()
            t.join()
            if "exc" in exc_container:
                raise exc_container["exc"]
            return result_container["result"]

        # Register with Dapr
        if name:
            return wfr.activity(name=name)(sync_wrapper)
        return wfr.activity()(sync_wrapper)

    return decorator if _func is None else decorator(_func)
