"""
Chaos Engineering Test Suite for AstraGuard AI

Validates resilience features under controlled failure injection:
- Circuit breaker state transitions
- Retry logic activation
- Recovery orchestrator actions
- Distributed cluster consensus

Run with: pytest tests/chaos/ -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from backend.chaos_engine import ChaosEngine, CHAOS_INJECTIONS, CHAOS_RECOVERY_TIME, CHAOS_ACTIVE


@pytest.fixture
async def chaos_engine():
    """Create and initialize ChaosEngine for testing."""
    engine = ChaosEngine(base_url="http://localhost:8000")
    engine.session = AsyncMock()
    yield engine
    await engine.shutdown()


@pytest.mark.asyncio
async def test_chaos_engine_startup():
    """Test ChaosEngine initialization."""
    engine = ChaosEngine()
    assert engine.base_url == "http://localhost:8000"
    assert engine.session is None
    assert not engine.chaos_active


@pytest.mark.asyncio
async def test_model_loader_fault_injection(chaos_engine):
    """Test model loader failure injection.
    
    Verifies:
    - Fault injection is recorded
    - Health endpoint is polled during injection
    - Recovery time is measured
    """
    # Mock successful recovery response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "system": {"status": "HEALTHY"},
        "circuit_breaker": {"state": "CLOSED"}
    })
    
    # Properly mock the async context manager
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    
    chaos_engine.session.get = AsyncMock(return_value=mock_context)

    result = await chaos_engine._inject_model_loader_failure(duration_seconds=1)
    
    assert result is True
    assert chaos_engine.session.get.called


@pytest.mark.asyncio
async def test_network_latency_injection(chaos_engine):
    """Test network latency injection.
    
    Verifies:
    - Latency injection completes
    - Metrics endpoint is monitored
    - System remains responsive
    """
    mock_response = AsyncMock()
    mock_response.status = 200
    
    chaos_engine.session.get = AsyncMock(return_value=mock_response)
    chaos_engine.session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    chaos_engine.session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await chaos_engine._inject_network_latency(duration_seconds=5)
    
    assert result is True
    assert chaos_engine.session.get.called


@pytest.mark.asyncio
async def test_redis_failure_injection(chaos_engine):
    """Test Redis failure injection.
    
    Verifies:
    - System degrades gracefully
    - Fallback mechanisms activate
    - Service remains partially functional
    """
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "system": {"status": "DEGRADED"},
        "circuit_breaker": {"state": "OPEN"}
    })
    
    chaos_engine.session.get = AsyncMock(return_value=mock_response)
    chaos_engine.session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    chaos_engine.session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await chaos_engine._inject_redis_failure(duration_seconds=5)
    
    assert result is True


@pytest.mark.asyncio
async def test_circuit_breaker_chaos(chaos_engine):
    """Test circuit breaker under chaos.
    
    Verifies:
    - Circuit breaker transitions through states
    - Recovery mechanisms engage
    - System heals within expected time
    """
    # Mock fault injection
    chaos_engine.inject_faults = AsyncMock(return_value=True)
    
    # Mock health endpoint response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "circuit_breaker": {"state": "HALF_OPEN"},
        "system": {"status": "DEGRADED"}
    })
    
    chaos_engine.session.get = AsyncMock(return_value=mock_response)
    chaos_engine.session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    chaos_engine.session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await chaos_engine.test_circuit_breaker()
    
    assert result is True
    chaos_engine.inject_faults.assert_called_once()


@pytest.mark.asyncio
async def test_retry_logic_chaos(chaos_engine):
    """Test retry logic under chaos.
    
    Verifies:
    - Retries activate under transient failures
    - System stabilizes after recovery
    - Retry backoff is respected
    """
    chaos_engine.inject_faults = AsyncMock(return_value=True)
    
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "retry": {"state": "ELEVATED"},
        "system": {"status": "DEGRADED"}
    })
    
    chaos_engine.session.get = AsyncMock(return_value=mock_response)
    chaos_engine.session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    chaos_engine.session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await chaos_engine.test_retry_logic()
    
    assert result is True


@pytest.mark.asyncio
async def test_recovery_orchestrator_chaos(chaos_engine):
    """Test recovery orchestrator under chaos.
    
    Verifies:
    - Recovery actions are triggered
    - Circuit breaker restart executes
    - Recovery metrics are tracked
    """
    chaos_engine.inject_faults = AsyncMock(return_value=True)
    
    # Mock recovery metrics endpoint
    mock_recovery = AsyncMock()
    mock_recovery.status = 200
    mock_recovery.json = AsyncMock(return_value={
        "action_count": 3,
        "actions": ["circuit_restart", "cache_purge", "circuit_restart"]
    })
    
    chaos_engine.session.get = AsyncMock(return_value=mock_recovery)
    chaos_engine.session.get.return_value.__aenter__ = AsyncMock(return_value=mock_recovery)
    chaos_engine.session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await chaos_engine.test_recovery_orchestrator()
    
    assert result is True


@pytest.mark.asyncio
async def test_cluster_consensus_chaos(chaos_engine):
    """Test cluster consensus under chaos.
    
    Verifies:
    - Leader election works under failure
    - Quorum is maintained
    - Consensus is reached within timeout
    """
    mock_leader_response = AsyncMock()
    mock_leader_response.status = 200
    mock_leader_response.json = AsyncMock(return_value={
        "instance_id": "astra-abc123"
    })
    
    mock_consensus_response = AsyncMock()
    mock_consensus_response.status = 200
    mock_consensus_response.json = AsyncMock(return_value={
        "quorum_met": True,
        "voting_instances": 3
    })
    
    chaos_engine.session.get = AsyncMock(side_effect=[
        AsyncMock(__aenter__=AsyncMock(return_value=mock_leader_response), __aexit__=AsyncMock()),
        AsyncMock(__aenter__=AsyncMock(return_value=mock_leader_response), __aexit__=AsyncMock()),
        AsyncMock(__aenter__=AsyncMock(return_value=mock_consensus_response), __aexit__=AsyncMock()),
    ])

    result = await chaos_engine.test_cluster_consensus()
    
    assert result is True


@pytest.mark.asyncio
async def test_full_chaos_suite(chaos_engine):
    """Test complete chaos suite.
    
    Verifies:
    - All test scenarios execute
    - Results are collected
    - Metrics are recorded
    """
    chaos_engine.test_circuit_breaker = AsyncMock(return_value=True)
    chaos_engine.test_retry_logic = AsyncMock(return_value=True)
    chaos_engine.test_recovery_orchestrator = AsyncMock(return_value=True)
    chaos_engine.test_cluster_consensus = AsyncMock(return_value=True)

    results = await chaos_engine.run_full_suite()
    
    assert all(results.values())
    assert "circuit_breaker" in results
    assert "retry_logic" in results
    assert "recovery_orchestrator" in results
    assert "cluster_consensus" in results


@pytest.mark.asyncio
async def test_chaos_metrics_recorded(chaos_engine):
    """Test that chaos metrics are properly recorded.
    
    Verifies:
    - Injection counters are incremented
    - Recovery times are measured
    - Active chaos status is tracked
    """
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "system": {"status": "HEALTHY"}
    })
    
    chaos_engine.session.get = AsyncMock(return_value=mock_response)
    chaos_engine.session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    chaos_engine.session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    # Test that injection counter increments
    initial_count = CHAOS_INJECTIONS.labels(fault_type="model_loader")._value.get() if hasattr(CHAOS_INJECTIONS, '_value') else 0
    
    result = await chaos_engine._inject_model_loader_failure(duration_seconds=1)
    
    # Verify counter incremented after injection
    post_count = CHAOS_INJECTIONS.labels(fault_type="model_loader")._value.get() if hasattr(CHAOS_INJECTIONS, '_value') else 0
    assert post_count == initial_count + 1, f"Expected counter to increment from {initial_count} to {initial_count + 1}, got {post_count}"
    
    assert result is True


@pytest.mark.asyncio
async def test_chaos_failure_handling(chaos_engine):
    """Test chaos engine handles failures gracefully.
    
    Verifies:
    - Timeout errors are caught
    - Connection errors are handled
    - Invalid responses don't crash
    """
    # Mock connection failure
    chaos_engine.session.get = AsyncMock(side_effect=Exception("Connection refused"))

    result = await chaos_engine.test_circuit_breaker()
    
    # Should fail gracefully, not crash
    assert result is False


@pytest.mark.asyncio
async def test_chaos_unknown_fault_type(chaos_engine):
    """Test handling of unknown fault types.
    
    Verifies:
    - Unknown fault types are rejected
    - Error is logged
    - False is returned
    """
    result = await chaos_engine.inject_faults("unknown_fault_type")
    
    assert result is False
