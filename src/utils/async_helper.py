"""
Async helper utilities to simplify event loop management.

This module provides utilities to run async functions from synchronous contexts,
eliminating the need for repetitive event loop creation and management.

Following SOLID principles:
- Single Responsibility: Only handles async/sync bridge
- Dependency Inversion: Works with any async callable
"""

import asyncio
import logging
from typing import TypeVar, Callable, Any, Awaitable

logger = logging.getLogger(__name__)

T = TypeVar('T')


def run_async(async_func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
    """
    Run an async function from a synchronous context.
    
    This utility creates a new event loop, runs the async function,
    and properly cleans up the loop afterwards. Use this to eliminate
    repetitive event loop creation patterns.
    
    Args:
        async_func: The async function to run
        *args: Positional arguments to pass to async_func
        **kwargs: Keyword arguments to pass to async_func
        
    Returns:
        The result of the async function
        
    Raises:
        Any exception raised by the async function
        
    Example:
        >>> async def fetch_data(id: int) -> dict:
        ...     return {"id": id, "data": "value"}
        >>> result = run_async(fetch_data, 123)
        >>> print(result)
        {'id': 123, 'data': 'value'}
    """
    loop = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(async_func(*args, **kwargs))
    finally:
        if loop is not None:
            try:
                loop.close()
            except Exception as e:
                logger.warning(f"Error closing event loop: {e}")


def run_async_safe(
    async_func: Callable[..., Awaitable[T]], 
    *args: Any,
    default: T = None,
    log_errors: bool = True,
    **kwargs: Any
) -> T:
    """
    Run an async function with error handling and default fallback.
    
    This is a safer version of run_async that catches exceptions
    and returns a default value instead of propagating the error.
    Useful for UI contexts where you want graceful degradation.
    
    Args:
        async_func: The async function to run
        *args: Positional arguments to pass to async_func
        default: Value to return if function fails (default: None)
        log_errors: Whether to log errors (default: True)
        **kwargs: Keyword arguments to pass to async_func
        
    Returns:
        The result of the async function, or default value on error
        
    Example:
        >>> async def risky_fetch(id: int) -> dict:
        ...     raise ValueError("Network error")
        >>> result = run_async_safe(risky_fetch, 123, default={})
        >>> print(result)
        {}
    """
    try:
        return run_async(async_func, *args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error running async function {async_func.__name__}: {e}", exc_info=True)
        return default
