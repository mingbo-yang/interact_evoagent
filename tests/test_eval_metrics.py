"""Tests for Metrics."""

from evoagent.eval.metrics import Metrics
from evoagent.eval.task import EvalResult


def test_success_rate():
    results = [
        EvalResult(task_id="a", run_id="r1", success=True, score=1.0),
        EvalResult(task_id="b", run_id="r2", success=False, score=0.0),
        EvalResult(task_id="c", run_id="r3", success=True, score=1.0),
    ]
    m = Metrics.compute(results)
    assert m["success_rate"] == 2 / 3


def test_avg_duration():
    results = [
        EvalResult(task_id="a", run_id="r1", success=True, duration_ms=100),
        EvalResult(task_id="b", run_id="r2", success=True, duration_ms=200),
    ]
    m = Metrics.compute(results)
    assert m["avg_duration_ms"] == 150


def test_empty_results():
    m = Metrics.compute([])
    assert m["total"] == 0
    assert m["success_rate"] == 0.0


def test_none_metrics():
    """Metrics that are not available should return None."""
    m = Metrics.compute([EvalResult(task_id="a", run_id="r1", success=True)])
    assert m["memory_hit_rate"] is None
