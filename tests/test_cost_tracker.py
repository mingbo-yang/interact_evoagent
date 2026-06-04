"""Tests for CostTracker."""

from evoagent.core.cost import DEFAULT_PRICING, CostSnapshot


def test_cost_snapshot_empty():
    cs = CostSnapshot()
    assert cs.total_tokens == 0
    assert cs.cost_usd == 0.0


def test_cost_snapshot_add_call():
    cs = CostSnapshot()
    cs.add_call("deepseek-chat", prompt_tokens=1000, completion_tokens=500)
    assert cs.prompt_tokens == 1000
    assert cs.completion_tokens == 500
    assert cs.total_tokens == 1500
    # deepseek-chat: $0.00027/1k input, $0.0011/1k output
    expected = (1000 / 1000) * 0.00027 + (500 / 1000) * 0.0011
    assert abs(cs.cost_usd - expected) < 0.000001


def test_cost_snapshot_by_model():
    cs = CostSnapshot()
    cs.add_call("deepseek-chat", prompt_tokens=1000, completion_tokens=0)
    cs.add_call("deepseek-reasoner", prompt_tokens=500, completion_tokens=500)
    assert len(cs.by_model) == 2
    assert cs.by_model["deepseek-chat"]["calls"] == 1
    assert cs.by_model["deepseek-reasoner"]["calls"] == 1


def test_cost_snapshot_summary():
    cs = CostSnapshot()
    cs.add_call("deepseek-chat", prompt_tokens=2000, completion_tokens=1000)
    s = cs.summary()
    assert "total_tokens" in s
    assert "cost_usd" in s
    assert "by_model" in s


def test_default_pricing():
    assert "deepseek-chat" in DEFAULT_PRICING
    assert "gpt-4o" in DEFAULT_PRICING


def test_custom_pricing():
    cs = CostSnapshot()
    cs.add_call("custom-model", prompt_tokens=1000, completion_tokens=1000,
                input_price=0.01, output_price=0.02)
    expected = (1000 / 1000) * 0.01 + (1000 / 1000) * 0.02
    assert abs(cs.cost_usd - expected) < 0.000001
