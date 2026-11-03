"""
Pytest Performance SLA Validation Test
Enforces latency limits and throughput standards as an automated quality gate.
"""
import pytest
from tests.performance.load_engine import LoadTestEngine

def test_system_performance_under_concurrency(app):
    """Ensure system handles concurrent traffic within SLA bounds."""
    engine = LoadTestEngine(app=app)
    stats = engine.run_benchmark(total_requests=60, concurrency=4)
    
    # Assertions for SLA Quality Gate
    assert stats["error_rate_pct"] == 0.0, f"Error rate too high: {stats['error_rate_pct']}%"
    assert stats["p95_latency_ms"] < 350.0, f"P95 latency exceeded SLA: {stats['p95_latency_ms']}ms"
    assert stats["sla_passed"] is True
