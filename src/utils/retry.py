"""
Retry utility with exponential backoff for ICC application.

Provides configurable retry mechanisms for handling transient failures
in API calls, LLM operations, and other network-dependent operations.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, Union

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.
    
    Attributes:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        strategy: Retry delay strategy
        jitter: Whether to add random jitter to delays
        jitter_factor: Maximum jitter as fraction of delay (0.0-1.0)
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called before each retry
    """
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True
    jitter_factor: float = 0.25
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** attempt)
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * (attempt + 1)
        else:  # CONSTANT
            delay = self.base_delay
        
        # Apply maximum delay cap
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            jitter_amount = delay * self.jitter_factor * random.random()
            delay = delay + jitter_amount
        
        return delay


# Predefined retry configurations for common use cases
class RetryPresets:
    """Predefined retry configurations for common scenarios."""
    
    # Authentication operations
    AUTHENTICATION = RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL,
        jitter=True,
    )
    
    # General API calls
    API_CALL = RetryConfig(
        max_retries=3,
        base_delay=0.5,
        max_delay=5.0,
        strategy=RetryStrategy.EXPONENTIAL,
        jitter=True,
    )
    
    # LLM operations (longer timeouts expected)
    LLM_CALL = RetryConfig(
        max_retries=3,
        base_delay=2.0,
        max_delay=15.0,
        strategy=RetryStrategy.EXPONENTIAL,
        jitter=True,
    )
    
    # Database operations
    DATABASE = RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL,
        jitter=True,
    )
    
    # Quick retry for idempotent operations
    QUICK = RetryConfig(
        max_retries=2,
        base_delay=0.25,
        max_delay=1.0,
        strategy=RetryStrategy.CONSTANT,
        jitter=False,
    )
    
    # Aggressive retry for critical operations
    AGGRESSIVE = RetryConfig(
        max_retries=5,
        base_delay=0.5,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL,
        jitter=True,
    )


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""
    
    def __init__(
        self,
        message: str,
        attempts: int,
        last_exception: Exception,
        total_time: float
    ):
        """
        Initialize retry exhausted error.
        
        Args:
            message: Error message
            attempts: Number of attempts made
            last_exception: The last exception encountered
            total_time: Total time spent retrying
        """
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception
        self.total_time = total_time


def retry(
    config: Optional[RetryConfig] = None,
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
):
    """
    Decorator for adding retry logic to functions.
    
    Can use a predefined config or individual parameters.
    
    Args:
        config: RetryConfig to use (overrides individual params)
        max_retries: Maximum retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        retryable_exceptions: Exception types to retry on
        on_retry: Callback before each retry
        
    Returns:
        Decorated function with retry logic
        
    Usage:
        @retry(config=RetryPresets.API_CALL)
        def api_call():
            ...
            
        @retry(max_retries=3, base_delay=1.0)
        async def async_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Build configuration
        if config is not None:
            cfg = config
        else:
            cfg = RetryConfig(
                max_retries=max_retries or 3,
                base_delay=base_delay or 1.0,
                max_delay=max_delay or 30.0,
                retryable_exceptions=retryable_exceptions or (Exception,),
                on_retry=on_retry,
            )
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return _retry_sync(func, cfg, *args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _retry_async(func, cfg, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def _retry_sync(
    func: Callable,
    config: RetryConfig,
    *args: Any,
    **kwargs: Any
) -> Any:
    """Execute function with sync retry logic."""
    last_exception: Optional[Exception] = None
    start_time = time.time()
    
    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            
            # Check if this was the last attempt
            if attempt >= config.max_retries:
                break
            
            # Calculate delay
            delay = config.calculate_delay(attempt)
            
            # Log retry attempt
            logger.warning(
                f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                f"after {type(e).__name__}: {str(e)[:100]}. "
                f"Waiting {delay:.2f}s before next attempt."
            )
            
            # Call on_retry callback if provided
            if config.on_retry:
                config.on_retry(e, attempt + 1, delay)
            
            # Wait before retry
            time.sleep(delay)
        except Exception as e:
            # Non-retryable exception, re-raise immediately
            logger.error(
                f"Non-retryable exception in {func.__name__}: "
                f"{type(e).__name__}: {str(e)}"
            )
            raise
    
    # All retries exhausted
    total_time = time.time() - start_time
    logger.error(
        f"All {config.max_retries} retries exhausted for {func.__name__} "
        f"after {total_time:.2f}s. Last error: {last_exception}"
    )
    
    raise RetryExhaustedError(
        f"Failed after {config.max_retries} retries",
        attempts=config.max_retries + 1,
        last_exception=last_exception,
        total_time=total_time
    )


async def _retry_async(
    func: Callable,
    config: RetryConfig,
    *args: Any,
    **kwargs: Any
) -> Any:
    """Execute async function with retry logic."""
    last_exception: Optional[Exception] = None
    start_time = time.time()
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            
            # Check if this was the last attempt
            if attempt >= config.max_retries:
                break
            
            # Calculate delay
            delay = config.calculate_delay(attempt)
            
            # Log retry attempt
            logger.warning(
                f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                f"after {type(e).__name__}: {str(e)[:100]}. "
                f"Waiting {delay:.2f}s before next attempt."
            )
            
            # Call on_retry callback if provided
            if config.on_retry:
                config.on_retry(e, attempt + 1, delay)
            
            # Wait before retry (async)
            await asyncio.sleep(delay)
        except Exception as e:
            # Non-retryable exception, re-raise immediately
            logger.error(
                f"Non-retryable exception in {func.__name__}: "
                f"{type(e).__name__}: {str(e)}"
            )
            raise
    
    # All retries exhausted
    total_time = time.time() - start_time
    logger.error(
        f"All {config.max_retries} retries exhausted for {func.__name__} "
        f"after {total_time:.2f}s. Last error: {last_exception}"
    )
    
    raise RetryExhaustedError(
        f"Failed after {config.max_retries} retries",
        attempts=config.max_retries + 1,
        last_exception=last_exception,
        total_time=total_time
    )


async def retry_async_operation(
    operation: Callable,
    config: Optional[RetryConfig] = None,
    *args: Any,
    **kwargs: Any
) -> Any:
    """
    Execute an async operation with retry logic.
    
    Useful for one-off retry operations without decorating.
    
    Args:
        operation: Async callable to execute
        config: Retry configuration (defaults to API_CALL preset)
        *args: Arguments for the operation
        **kwargs: Keyword arguments for the operation
        
    Returns:
        Result of the operation
        
    Raises:
        RetryExhaustedError: If all retries are exhausted
    """
    cfg = config or RetryPresets.API_CALL
    return await _retry_async(operation, cfg, *args, **kwargs)


def retry_sync_operation(
    operation: Callable,
    config: Optional[RetryConfig] = None,
    *args: Any,
    **kwargs: Any
) -> Any:
    """
    Execute a sync operation with retry logic.
    
    Useful for one-off retry operations without decorating.
    
    Args:
        operation: Callable to execute
        config: Retry configuration (defaults to API_CALL preset)
        *args: Arguments for the operation
        **kwargs: Keyword arguments for the operation
        
    Returns:
        Result of the operation
        
    Raises:
        RetryExhaustedError: If all retries are exhausted
    """
    cfg = config or RetryPresets.API_CALL
    return _retry_sync(operation, cfg, *args, **kwargs)


def is_retryable_http_status(status_code: int) -> bool:
    """
    Check if an HTTP status code indicates a retryable error.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        True if the error is retryable
    """
    # 5xx server errors are generally retryable
    if 500 <= status_code < 600:
        return True
    
    # Specific retryable 4xx errors
    retryable_4xx = {
        408,  # Request Timeout
        429,  # Too Many Requests
    }
    
    return status_code in retryable_4xx


def create_http_retry_config(
    max_retries: int = 3,
    retryable_statuses: Optional[Tuple[int, ...]] = None
) -> RetryConfig:
    """
    Create a retry config suitable for HTTP operations.
    
    Args:
        max_retries: Maximum retry attempts
        retryable_statuses: HTTP status codes to retry on
        
    Returns:
        RetryConfig for HTTP operations
    """
    import httpx
    
    retryable_statuses = retryable_statuses or (408, 429, 500, 502, 503, 504)
    
    return RetryConfig(
        max_retries=max_retries,
        base_delay=0.5,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL,
        jitter=True,
        retryable_exceptions=(
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ReadTimeout,
            ConnectionError,
            TimeoutError,
        ),
    )

