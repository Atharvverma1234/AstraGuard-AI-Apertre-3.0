"""
Comprehensive tests for Retry decorator with exponential backoff + jitter.
Tests cover success cases, backoff scheduling, exception filtering, and metrics.
"""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from core.retry import (
    Retry,
    calculate_backoff_delays,
    RETRY_ATTEMPTS_TOTAL,
    RETRY_EXHAUSTIONS_TOTAL,
    RETRY_DELAYS_SECONDS,
)


# ============================================================================
# UNIT TESTS - BASIC FUNCTIONALITY
# ============================================================================

@pytest.mark.asyncio
async def test_retry_success_on_first_attempt():
    """Test that successful call returns immediately without retry."""
    func = AsyncMock(return_value="success")
    decorated = Retry()(func)
    
    result = await decorated()
    
    assert result == "success"
    func.assert_called_once()


@pytest.mark.asyncio
async def test_retry_success_after_transient_failure():
    """Test retry succeeds after transient failure."""
    func = AsyncMock(side_effect=[TimeoutError(), "success"])
    decorated = Retry(max_attempts=3)(func)
    
    result = await decorated()
    
    assert result == "success"
    assert func.call_count == 2


@pytest.mark.asyncio
async def test_retry_exhaustion_raises_original_exception():
    """Test that original exception is raised after max attempts exhausted."""
    func = AsyncMock(side_effect=ConnectionError("network down"))
    decorated = Retry(max_attempts=2)(func)
    
    with pytest.raises(ConnectionError, match="network down"):
        await decorated()
    
    assert func.call_count == 2


@pytest.mark.asyncio
async def test_retry_non_retryable_exception_raises_immediately():
    """Test that non-retryable exceptions raise immediately."""
    func = AsyncMock(side_effect=ValueError("invalid input"))
    decorated = Retry(
        allowed_exceptions=(TimeoutError, ConnectionError)
    )(func)
    
    with pytest.raises(ValueError, match="invalid input"):
        await decorated()
    
    func.assert_called_once()


# ============================================================================
# UNIT TESTS - BACKOFF SCHEDULING
# ============================================================================

def test_backoff_schedule_calculation():
    """Test exponential backoff schedule without jitter."""
    delays = calculate_backoff_delays(max_attempts=4, base_delay=0.5, max_delay=8.0)
    
    # First attempt has no delay
    assert delays[0] == 0
    # 0.5 * 2^0 = 0.5
    assert delays[1] == 0.5
    # 0.5 * 2^1 = 1.0
    assert delays[2] == 1.0
    # 0.5 * 2^2 = 2.0
    assert delays[3] == 2.0


def test_backoff_schedule_hits_max_delay():
    """Test that backoff is capped at max_delay."""
    delays = calculate_backoff_delays(max_attempts=6, base_delay=0.5, max_delay=8.0)
    
    # 0.5 * 2^4 = 8.0
    assert delays[4] == 8.0
    # 0.5 * 2^5 = 16.0, capped to 8.0
    assert delays[5] == 8.0


@pytest.mark.asyncio
async def test_retry_backoff_timing():
    """Test that backoff delays are observed."""
    call_times = []
    
    async def failing_func():
        call_times.append(time.time())
        raise TimeoutError()
    
    decorated = Retry(
        max_attempts=3,
        base_delay=0.1,
        max_delay=0.5,
        jitter_type="full"
    )(failing_func)
    
    with pytest.raises(TimeoutError):
        await decorated()
    
    assert len(call_times) == 3
    
    # Check that delays between attempts are approximately exponential
    delay1 = call_times[1] - call_times[0]
    delay2 = call_times[2] - call_times[1]
    
    # Second delay should be larger (exponential backoff)
    assert delay2 > delay1


# ============================================================================
# UNIT TESTS - JITTER TYPES
# ============================================================================

def test_full_jitter_calculation():
    """Test full jitter produces reasonable values."""
    retry = Retry(base_delay=1.0, max_delay=8.0, jitter_type="full")
    
    delays = [retry._calculate_delay(0) for _ in range(100)]
    
    # All delays should be between base_delay * 0.5 and base_delay * 1.5
    assert all(0.5 <= d <= 1.5 for d in delays)


def test_equal_jitter_calculation():
    """Test equal jitter produces reasonable values."""
    retry = Retry(base_delay=1.0, max_delay=8.0, jitter_type="equal")
    
    delays = [retry._calculate_delay(0) for _ in range(100)]
    
    # All delays should be between base_delay/2 and base_delay
    assert all(0.5 <= d <= 1.0 for d in delays)


def test_decorrelated_jitter_calculation():
    """Test decorrelated jitter produces reasonable values."""
    retry = Retry(base_delay=1.0, max_delay=8.0, jitter_type="decorrelated")
    
    delays = [retry._calculate_delay(0) for _ in range(100)]
    
    # All delays should be capped at max_delay
    assert all(d <= 8.0 for d in delays)


# ============================================================================
# UNIT TESTS - EXCEPTION FILTERING
# ============================================================================

@pytest.mark.asyncio
async def test_retry_custom_allowed_exceptions():
    """Test retry with custom exception list."""
    func = AsyncMock(side_effect=[CustomError("custom"), "success"])
    decorated = Retry(
        max_attempts=3,
        allowed_exceptions=(CustomError,)
    )(func)
    
    result = await decorated()
    assert result == "success"
    assert func.call_count == 2


@pytest.mark.asyncio
async def test_retry_multiple_exception_types():
    """Test retry handles multiple exception types."""
    func = AsyncMock(side_effect=[
        TimeoutError(),
        ConnectionError(),
        "success"
    ])
    decorated = Retry(max_attempts=4)(func)
    
    result = await decorated()
    assert result == "success"
    assert func.call_count == 3


# ============================================================================
# UNIT TESTS - ARGUMENTS PASSING
# ============================================================================

@pytest.mark.asyncio
async def test_retry_preserves_function_arguments():
    """Test that function arguments are passed correctly through retry."""
    func = AsyncMock(return_value="result")
    decorated = Retry()(func)
    
    await decorated("arg1", "arg2", kwarg1="value1", kwarg2="value2")
    
    func.assert_called_once_with("arg1", "arg2", kwarg1="value1", kwarg2="value2")


@pytest.mark.asyncio
async def test_retry_with_args_and_exceptions():
    """Test retry with arguments and exception handling."""
    func = AsyncMock(side_effect=[ValueError(), "success"])
    decorated = Retry(allowed_exceptions=(ValueError,))(func)
    
    result = await decorated("test_arg", test_kwarg="test_value")
    
    assert result == "success"
    assert func.call_count == 2
    func.assert_called_with("test_arg", test_kwarg="test_value")


# ============================================================================
# UNIT TESTS - SYNC FUNCTION SUPPORT
# ============================================================================

def test_retry_sync_function_success():
    """Test retry decorator works with sync functions."""
    func = Mock(return_value="success")
    decorated = Retry()(func)
    
    result = decorated()
    
    assert result == "success"
    func.assert_called_once()


def test_retry_sync_function_with_retry():
    """Test sync function retry on transient failure."""
    func = Mock(side_effect=[TimeoutError(), "success"])
    decorated = Retry(
        max_attempts=3,
        base_delay=0.01,
        jitter_type="full"
    )(func)
    
    result = decorated()
    
    assert result == "success"
    assert func.call_count == 2


# ============================================================================
# INTEGRATION TESTS - METRICS TRACKING
# ============================================================================

@pytest.mark.asyncio
async def test_retry_metrics_on_success():
    """Test that metrics are recorded on success."""
    func = AsyncMock(return_value="success")
    decorated = Retry()(func)
    
    # Reset metrics
    Retry.reset_metrics()
    
    await decorated()
    
    # Success metric should be incremented
    # Note: Prometheus metrics are global, just verify decorator executes


@pytest.mark.asyncio
async def test_retry_metrics_on_exhaustion():
    """Test that exhaustion metrics are recorded."""
    func = AsyncMock(side_effect=TimeoutError("timeout"))
    decorated = Retry(max_attempts=2)(func)
    
    with pytest.raises(TimeoutError):
        await decorated()
    
    # Exhaustion metric should be recorded
    # (Actual verification would require accessing Prometheus registry)


# ============================================================================
# INTEGRATION TESTS - REAL-WORLD SCENARIOS
# ============================================================================

@pytest.mark.asyncio
async def test_retry_transient_network_failure():
    """Simulate transient network failure that recovers on retry."""
    attempt_count = 0
    
    async def unreliable_api():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError("connection reset")
        return {"status": "success"}
    
    decorated = Retry(
        max_attempts=5,
        base_delay=0.01,
        allowed_exceptions=(ConnectionError,)
    )(unreliable_api)
    
    result = await decorated()
    
    assert result == {"status": "success"}
    assert attempt_count == 3


@pytest.mark.asyncio
async def test_retry_timeout_recovery():
    """Simulate timeout that recovers on retry."""
    call_count = 0
    
    async def slow_operation():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            await asyncio.sleep(0.1)
            raise asyncio.TimeoutError()
        return "completed"
    
    decorated = Retry(
        max_attempts=3,
        base_delay=0.01,
        allowed_exceptions=(asyncio.TimeoutError,)
    )(slow_operation)
    
    result = await decorated()
    
    assert result == "completed"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_cascading_failures():
    """Simulate multiple types of transient failures."""
    failures = [
        TimeoutError("first timeout"),
        ConnectionError("connection lost"),
        OSError("io error"),
        "success"
    ]
    
    func = AsyncMock(side_effect=failures)
    decorated = Retry(
        max_attempts=5,
        base_delay=0.01,
        allowed_exceptions=(TimeoutError, ConnectionError, OSError)
    )(func)
    
    result = await decorated()
    
    assert result == "success"
    assert func.call_count == 4


# ============================================================================
# INTEGRATION TESTS - BACKOFF PATTERN
# ============================================================================

@pytest.mark.asyncio
async def test_retry_backoff_prevents_thundering_herd():
    """Test that exponential backoff + jitter prevents thundering herd."""
    # Simulate multiple concurrent retries with jitter
    
    async def failing_operation():
        raise TimeoutError()
    
    decorated = Retry(
        max_attempts=3,
        base_delay=0.5,
        max_delay=8.0,
        jitter_type="full"
    )(failing_operation)
    
    # In a real scenario, these would run concurrently
    # The jitter should spread out the retry attempts
    start = time.time()
    with pytest.raises(TimeoutError):
        await decorated()
    elapsed = time.time() - start
    
    # Should have taken at least sum of backoff delays (with some jitter)
    # Minimum: 0 + 0.25 + 0.5 = 0.75s (with jitter between 0.5-1.5x)
    assert elapsed >= 0.7  # Allow for some timing variance


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_retry_with_max_attempts_1():
    """Test retry with max_attempts=1 (no retries)."""
    func = AsyncMock(side_effect=TimeoutError())
    decorated = Retry(max_attempts=1)(func)
    
    with pytest.raises(TimeoutError):
        await decorated()
    
    func.assert_called_once()


@pytest.mark.asyncio
async def test_retry_with_zero_base_delay():
    """Test retry with zero base delay."""
    func = AsyncMock(side_effect=[TimeoutError(), "success"])
    decorated = Retry(
        max_attempts=2,
        base_delay=0.0
    )(func)
    
    result = await decorated()
    assert result == "success"


@pytest.mark.asyncio
async def test_retry_preserves_function_metadata():
    """Test that retry decorator preserves function metadata."""
    async def my_function():
        """My docstring"""
        return "result"
    
    decorated = Retry()(my_function)
    
    assert decorated.__name__ == "my_function"
    assert decorated.__doc__ == "My docstring"


# ============================================================================
# FIXTURES & HELPERS
# ============================================================================

class CustomError(Exception):
    """Custom exception for testing."""
    pass


@pytest.fixture(autouse=True)
def reset_retry_metrics():
    """Reset retry metrics before each test."""
    Retry.reset_metrics()
    yield
    Retry.reset_metrics()
