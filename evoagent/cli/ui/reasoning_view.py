"""Reasoning view — display public reasoning summaries, never hidden chain-of-thought."""


def render_reasoning(text: str) -> str:
    """Render a public reasoning summary line."""
    return f"  {text}"


def format_tool_count(count: int, duration_s: float = 0) -> str:
    """Format tool call count and duration summary."""
    if count == 0:
        return ""
    parts = [f"{count} tool calls"]
    if duration_s > 0:
        parts.append(f"{duration_s:.1f}s")
    return " · ".join(parts)
