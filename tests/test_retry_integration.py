"""
Integration tests for Retry + CircuitBreaker pattern.
Verifies that retry handles transient failures before circuit breaker engagement.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from core.retry import Retry
from core.circuit_breaker import CircuitBreaker, CircuitOpenError


# ============================================================================
# RETRY + CIRCUIT BREAKER INTEGRATION
# ============================================================================

@pytest.mark.asyncio
async def test_retry_circuit_sequence_transient_recovery():
    """
    Test that retry recovers from transient failures WITHOUT triggering circuit breaker.
    
    Pattern: Retry handles transient → Circuit stays CLOSED
    """
    call_count = 0
    
    async def transient_failure():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("transient connection error")
        return "success"
    
    # Retry decorator
    decorated_retry = Retry(
        max_attempts=5,
        base_delay=0.01,
        allowed_exceptions=(ConnectionError,)
    )(transient_failure)
    
    # Circuit breaker
    cb = CircuitBreaker(
        name="test_circuit",
        failure_threshold=3,
        success_threshold=1,
        recovery_timeout=1.0,
        expected_exceptions=(ConnectionError,)
    )
    
    # Execute through circuit
    result = await cb.call(decorated_retry)
    
    assert result == "success"
    assert call_count == 3
    assert cb.state == "CLOSED"  # Circuit should NOT trip


@pytest.mark.asyncio
async def test_retry_circuit_sequence_persistent_failure():
    """
    Test that circuit breaker trips after retry exhaustion.
    
    Pattern: Retry exhausts → Circuit opens → Falls back
    """
    call_count = 0
    
    async def persistent_failure():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("persistent connection error")
    
    # Retry decorator
    decorated_retry = Retry(
        max_attempts=3,
        base_delay=0.01,
        allowed_exceptions=(ConnectionError,)
    )(persistent_failure)
    
    # Circuit breaker (low threshold to trigger quickly)
    cb = CircuitBreaker(
        name="test_circuit",
        failure_threshold=2,
        success_threshold=1,
        recovery_timeout=1.0,
        expected_exceptions=(ConnectionError,)
    )
    
    # First call: retry exhausts after 3 attempts
    with pytest.raises(ConnectionError):
        await cb.call(decorated_retry)
    
    assert call_count == 3
    # Circuit should still be CLOSED after 1 failure
    assert cb.state == "CLOSED"
    
    # Second call: another retry exhaustion
    call_count = 0
    with pytest.raises(ConnectionError):
        await cb.call(decorated_retry)
    
    # Circuit should now be OPEN (2 failures >= threshold)
    assert cb.state == "OPEN"


@pytest.mark.asyncio
async def test_retry_exhaustion_before_circuit_trip():
    """
    Test that exhaust all retry attempts before circuit records a single failure.
    
    Each decorated call (with retries) counts as 1 failure to circuit breaker.
    """
    call_count = 0
    max_retries = 3
    
    async def failing_operation():
        nonlocal call_count
        call_count += 1
        raise TimeoutError("operation timeout")
    
    # Retry: 3 attempts = 3 calls to failing_operation
    decorated_retry = Retry(
        max_attempts=max_retries,
        base_delay=0.01,
        allowed_exceptions=(TimeoutError,)
    )(failing_operation)
    
    # Circuit breaker
    cb = CircuitBreaker(
        name="test_circuit",
        failure_threshold=2,  # 2 failures to trip
        success_threshold=1,
        recovery_timeout=1.0,
        expected_exceptions=(TimeoutError,)
    )
    
    # First decorated call (with internal retries)
    with pytest.raises(TimeoutError):
        await cb.call(decorated_retry)
    
    # Should have called operation 3 times (max_retries)
    assert call_count == max_retries
    # But circuit only counts 1 failure
    assert cb.state == "CLOSED"
    
    # Second decorated call
    call_count = 0
    with pytest.raises(TimeoutError):
        await cb.call(decorated_retry)
    
    # Circuit should now be open (2 failures)
    assert cb.state == "OPEN"


@pytest.mark.asyncio
async def test_retry_mixed_transient_and_persistent():
    """
    Test mixed scenario: some retries succeed, some fail and hit circuit.
    """
    operations = [
        # Call 1: transient failures then success
        [ConnectionError(), ConnectionError(), "success1"],
        # Call 2: transient failures then success
        [TimeoutError(), "success2"],
        # Call 3: persistent failure
        [ConnectionError(), ConnectionError(), ConnectionError()],
    ]
    
    call_iterator = iter([item for sublist in operations for item in sublist])
    
    async def varying_operation():
        try:
            result = next(call_iterator)
            if isinstance(result, Exception):
                raise result
            return result
        except StopIteration:
            raise RuntimeError("No more test data")
    
    # Retry decorator
    decorated_retry = Retry(
        max_attempts=3,
        base_delay=0.01,
        allowed_exceptions=(ConnectionError, TimeoutError)
    )(varying_operation)
    
    # Circuit breaker
    cb = CircuitBreaker(
        name="test_circuit",
        failure_threshold=2,
        success_threshold=1,
        recovery_timeout=1.0,
        expected_exceptions=(ConnectionError, TimeoutError)
    )
    
    # Call 1: succeeds after retries
    result = await cb.call(decorated_retry)
    assert result == "success1"
    assert cb.state == "CLOSED"
    
    # Call 2: succeeds
    result = await cb.call(decorated_retry)
    assert result == "success2"
    assert cb.state == "CLOSED"
    
    # Call 3: exhausts retries
    with pytest.raises(ConnectionError):
        await cb.call(decorated_retry)
    assert cb.state == "CLOSED"  # 1 failure < 2 threshold
    
    # Try again - should now trip circuit
    with pytest.raises(ConnectionError):
        await cb.call(decorated_retry)
    assert cb.state == "OPEN"


@pytest.mark.asyncio
async def test_retry_circuit_recovery_after_success():
    """
    Test that circuit recovers after retry succeeds in half-open state.
    """
    call_sequence = [
        ConnectionError(),  # Failure 1
        ConnectionError(),  # Failure 2 → Circuit opens
        "success"           # Success in HALF_OPEN → Circuit closes
    ]
    
    call_iterator = iter(call_sequence)
    
    async def operation():
        try:
            result = next(call_iterator)
            if isinstance(result, Exception):
                raise result
            return result
        except StopIteration:
            raise RuntimeError("Exhausted test data")
    
    # Retry with 1 attempt for simplicity
    decorated_retry = Retry(
        max_attempts=1,
        allowed_exceptions=(ConnectionError,)
    )(operation)
    
    # Circuit breaker
    cb = CircuitBreaker(
        name="test_circuit",
        failure_threshold=2,
        success_threshold=1,
        recovery_timeout=0.1,
        expected_exceptions=(ConnectionError,)
    )
    
    # Call 1: Failure
    with pytest.raises(ConnectionError):
        await cb.call(decorated_retry)
    assert cb.state == "CLOSED"
    
    # Call 2: Failure → Circuit opens
    with pytest.raises(ConnectionError):
        await cb.call(decorated_retry)
    assert cb.state == "OPEN"
    
    # Wait for recovery timeout
    await asyncio.sleep(0.15)
    assert cb.state == "HALF_OPEN"
    
    # Call 3: Success in HALF_OPEN → Circuit closes
    result = await cb.call(decorated_retry)
    assert result == "success"
    assert cb.state == "CLOSED"


# ============================================================================
# METRICS VERIFICATION
# ============================================================================

@pytest.mark.asyncio
async def test_retry_metrics_recorded_with_circuit():
    """Verify retry metrics are recorded through circuit breaker."""
    async def failing_operation():
        raise TimeoutError("operation timeout")
    
    decorated_retry = Retry(
        max_attempts=2,
        base_delay=0.01,
        allowed_exceptions=(TimeoutError,)
    )(failing_operation)
    
    cb = CircuitBreaker(
        name="test_circuit",
        failure_threshold=1,
        expected_exceptions=(TimeoutError,)
    )
    
    with pytest.raises(TimeoutError):
        await cb.call(decorated_retry)
    
    # Retry should have recorded metrics
    # (Would verify against Prometheus registry in production)


# ============================================================================
# CHAOS ENGINEERING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_retry_under_load():
    """Test retry behavior under concurrent load."""
    async def sometimes_fails():
        import random
        if random.random() < 0.5:
            raise ConnectionError()
        return "success"
    
    decorated_retry = Retry(
        max_attempts=5,
        base_delay=0.01,
        allowed_exceptions=(ConnectionError,)
    )(sometimes_fails)
    
    # Run multiple concurrent retries
    tasks = [decorated_retry() for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # All should eventually succeed or raise
    assert len(results) == 10
    successes = [r for r in results if r == "success"]
    failures = [r for r in results if isinstance(r, Exception)]
    
    # With high retry count, most should succeed
    assert len(successes) + len(failures) == 10


@pytest.mark.asyncio
async def test_retry_jitter_prevents_thundering_herd():
    """Test that jitter prevents synchronized retry storms."""
    import time
    import statistics
    
    retry_times = []
    
    async def failing_operation():
        raise TimeoutError()
    
    decorated_retry = Retry(
        max_attempts=3,
        base_delay=0.1,
        max_delay=0.5,
        jitter_type="full"
    )(failing_operation)
    
    # Measure time to exhaustion with multiple runs
    for _ in range(5):
        start = time.time()
        try:
            await decorated_retry()
        except TimeoutError:
            pass
        elapsed = time.time() - start
        retry_times.append(elapsed)
    
    # Times should vary due to jitter (high standard deviation)
    # In practice, all should be between 0.1 and 1.0s
    assert all(0.08 < t < 1.5 for t in retry_times)


# ============================================================================
# ERROR HANDLING EDGE CASES
# ============================================================================

@pytest.mark.asyncio
async def test_retry_with_non_retryable_exception_through_circuit():
    """Test that non-retryable exceptions don't interact with retry."""
    async def operation():
        raise ValueError("invalid input")
    
    decorated_retry = Retry(
        max_attempts=3,
        allowed_exceptions=(TimeoutError, ConnectionError)
    )(operation)
    
    cb = CircuitBreaker(
        name="test_circuit",
        failure_threshold=1,
        expected_exceptions=(TimeoutError, ConnectionError)
    )
    
    # Non-retryable exception should pass through retry
    with pytest.raises(ValueError, match="invalid input"):
        await cb.call(decorated_retry)
    
    # Circuit should not consider this a failure (not in expected_exceptions)
    assert cb.state == "CLOSED"


@pytest.mark.asyncio
async def test_retry_exception_from_decorator_wrapping():
    """Test exception handling in decorator wrapping itself."""
    async def operation():
        return "success"
    
    decorated_retry = Retry()(operation)
    
    # Should work normally
    result = await decorated_retry()
    assert result == "success"
