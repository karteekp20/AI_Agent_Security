"""
Retry with Exponential Backoff
Automatic retry of failed operations with increasing delays
"""

from typing import Callable, Optional, Type
from functools import wraps
import time
import random
from pydantic import BaseModel


class RetryConfig(BaseModel):
    """Retry configuration"""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
):
    """
    Decorator for retrying functions with exponential backoff

    Usage:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        def unreliable_function():
            # ... code that may fail ...

    Args:
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff (2.0 = double each time)
        jitter: Add random jitter to prevent thundering herd
        exceptions: Tuple of exceptions to retry on
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            last_exception = None

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e
                    attempt += 1

                    if attempt >= max_attempts:
                        # Max attempts reached, raise the exception
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        initial_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )

                    # Add jitter
                    if jitter:
                        delay = delay * (0.5 + random.random())  # Random between 50-150%

                    print(f"Retry attempt {attempt}/{max_attempts} after {delay:.2f}s: {e}")
                    time.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator
