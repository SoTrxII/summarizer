"""
This module export the Dapr Workflow Runtime as a singleton
"""
import asyncio
from functools import wraps

from dapr.ext.workflow import WorkflowRuntime

wfr = WorkflowRuntime()


def async_activity(func):
    """
    Decorator to wrap an async function as a Dapr workflow activity.
    It converts the async function into a sync function using asyncio.run().
    """
    @wfr.activity()  # type: ignore
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper
