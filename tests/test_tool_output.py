"""Tests for central tool output hygiene (P0.7)."""

import pytest
from pydantic import BaseModel

from evoagent.tools.base import BaseTool, RiskLevel
from evoagent.tools.output import (
    DEFAULT_MAX_OUTPUT_CHARS,
    truncate_head_tail,
)
from evoagent.tools.schema import ToolResult

# ── truncate_head_tail ────────────────────────────────────────────────


def test_short_text_passes_through():
    text = "hello world"
    out, meta = truncate_head_tail(text, max_chars=1000)
    assert out == text
    assert meta == {}


def test_empty_and_disabled():
    assert truncate_head_tail("", max_chars=1000) == ("", {})
    big = "x" * 100_000
    assert truncate_head_tail(big, max_chars=None) == (big, {})


def test_long_text_is_head_tail_truncated():
    text = "A" * 40_000 + "B" * 40_000
    out, meta = truncate_head_tail(text, max_chars=3000)
    # Head and tail are both preserved; the middle is dropped.
    assert out.startswith("A")
    assert out.endswith("B")
    assert "truncated" in out
    assert "do not assume it is empty" in out
    # The kept content (excluding marker) respects the budget.
    assert meta["output_truncated"] is True
    assert meta["output_total_chars"] == 80_000
    assert meta["output_omitted_chars"] > 0
    assert meta["output_total_lines"] == 1


def test_total_lines_counted():
    text = "line\n" * 20_000  # 100k chars, 20001 lines
    _, meta = truncate_head_tail(text, max_chars=2000)
    assert meta["output_total_lines"] == 20_001


def test_kind_label_changes_keys_and_marker():
    text = "z" * 5000
    out, meta = truncate_head_tail(text, max_chars=1000, kind="error")
    assert "error truncated" in out
    assert meta["error_truncated"] is True
    assert "error_total_chars" in meta


def test_tiny_budget_is_floored():
    text = "q" * 5000
    out, meta = truncate_head_tail(text, max_chars=10)
    # Floor prevents an unusably small budget; still truncated with metadata.
    assert meta["output_truncated"] is True
    assert out.startswith("q")
    assert out.endswith("q")


# ── BaseTool.arun integration ─────────────────────────────────────────


class _BigInput(BaseModel):
    pass


class _BigOutputTool(BaseTool):
    name = "big_output"
    description = "Returns a large output for testing."
    input_schema = _BigInput
    risk_level = RiskLevel.LOW

    def __init__(self, payload: str, error: str | None = None):
        self._payload = payload
        self._error = error

    async def run(self, **kwargs):
        return ToolResult(
            call_id="call_x", name=self.name,
            success=self._error is None,
            output=self._payload, error=self._error,
        )


@pytest.mark.asyncio
async def test_arun_truncates_oversized_output():
    payload = "C" * (DEFAULT_MAX_OUTPUT_CHARS + 50_000)
    tool = _BigOutputTool(payload)
    result = await tool.arun({})
    assert len(result.output) < len(payload)
    assert result.metadata.get("output_truncated") is True
    assert result.metadata["output_total_chars"] == len(payload)


@pytest.mark.asyncio
async def test_arun_leaves_small_output_untouched():
    tool = _BigOutputTool("small output")
    result = await tool.arun({})
    assert result.output == "small output"
    assert "output_truncated" not in result.metadata


@pytest.mark.asyncio
async def test_arun_truncates_oversized_error():
    tool = _BigOutputTool("", error="E" * (DEFAULT_MAX_OUTPUT_CHARS + 10_000))
    result = await tool.arun({})
    assert result.success is False
    assert "error truncated" in result.error
    assert result.metadata.get("error_truncated") is True


@pytest.mark.asyncio
async def test_arun_opt_out_with_none_cap():
    payload = "D" * (DEFAULT_MAX_OUTPUT_CHARS + 20_000)
    tool = _BigOutputTool(payload)
    tool.max_output_chars = None
    result = await tool.arun({})
    assert result.output == payload
    assert "output_truncated" not in result.metadata
