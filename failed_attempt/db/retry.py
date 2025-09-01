"""
Database retry logic and circuit breaker patterns for production resilience.
"""
import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar, Union, Type, Tuple
from sqlalchemy.exc import (
    DisconnectionError,
    OperationalError,
    TimeoutError as SQLTimeoutError,
    InterfaceError,
)

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])

# Transient errors that should be retried
TRANSIENT_ERRORS = (
    DisconnectionError,
    OperationalError,
    SQLTimeoutError,
    InterfaceError,
    ConnectionError,
    OSError,  # Network-related errors
)


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for database operations.
    
    Prevents cascading failures by temporarily stopping requests
    when error rate exceeds threshold.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def __call__(self, func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half-open"
                else:
                    raise CircuitBreakerError("Circuit breaker is open")
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
        
        return wrapper  # type: ignore[return-value]
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Reset circuit breaker on successful operation."""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failure and potentially open circuit breaker."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


def db_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    transient_errors: Tuple[Type[Exception], ...] = TRANSIENT_ERRORS,
) -> Callable[[F], F]:
    """
    Decorator for retrying database operations with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delay
        transient_errors: Tuple of exception types to retry on
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except transient_errors as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Last attempt failed, re-raise the exception
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_attempts}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    
                    await asyncio.sleep(delay)
                except Exception as e:
                    # Non-transient error, don't retry
                    logger.error(f"Non-transient error in {func.__name__}: {e}")
                    raise e
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper  # type: ignore[return-value]
    return decorator


# Global circuit breaker for database operations
db_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception,
)


@db_retry(max_attempts=3, base_delay=1.0)
@db_circuit_breaker
async def execute_with_retry(func: Callable, *args, **kwargs):
    """
    Execute a database function with retry logic and circuit breaker.
    
    This is a utility function that can be used to wrap any database operation
    that needs retry logic and circuit breaker protection.
    """
    return await func(*args, **kwargs)


def db_operation(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    use_circuit_breaker: bool = True,
) -> Callable[[F], F]:
    """
    Comprehensive decorator for database operations.
    
    Combines retry logic and circuit breaker pattern for maximum resilience.
    """
    def decorator(func: F) -> F:
        # Apply retry decorator
        retry_func = db_retry(
            max_attempts=max_attempts,
            base_delay=base_delay,
        )(func)
        
        # Apply circuit breaker if requested
        if use_circuit_breaker:
            return db_circuit_breaker(retry_func)
        else:
            return retry_func  # type: ignore[return-value]
    
    return decorator
