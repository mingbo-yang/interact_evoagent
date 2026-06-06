"""Tool output hygiene — central size caps and head/tail truncation.

Large tool outputs (huge file dumps, verbose command logs, giant search
results) waste the model's context window and can crowd out the actual task.
To keep every tool's output bounded and self-describing, ``BaseTool.arun``
runs the result through :func:`truncate_head_tail`, which keeps the head and
tail of oversized text and drops the middle, leaving an explicit marker plus
structured metadata so the model knows the output is incomplete and how to
narrow its request.
"""

from __future__ import annotations

# Default per-tool character cap applied to ``output`` (and ``error``). About
# ~7.5k tokens at the len/4 heuristic — small enough that a few large tool
# results do not blow the context, large enough for normal output to pass
# through untouched.
DEFAULT_MAX_OUTPUT_CHARS = 30_000

# Never cap below this: the truncation marker itself is a few hundred chars,
# so a tiny budget would leave no room for real content.
_MIN_MAX_CHARS = 500


def truncate_head_tail(
    text: str,
    max_chars: int | None = DEFAULT_MAX_OUTPUT_CHARS,
    *,
    kind: str = "output",
) -> tuple[str, dict]:
    """Cap ``text`` to ``max_chars`` by keeping its head and tail.

    Keeps roughly the first two thirds and last third of the budget, dropping
    the middle and replacing it with a marker that states how much was omitted
    and how to narrow the request. The omitted middle is explicitly flagged so
    the model does not assume it is empty or unchanged.

    Args:
        text: The text to bound.
        max_chars: Maximum characters to keep, or ``None`` to disable.
        kind: Label for the marker and metadata keys (e.g. ``"output"`` or
            ``"error"``).

    Returns:
        ``(text, meta)``. ``meta`` is empty when no truncation happened;
        otherwise it carries ``{kind}_truncated``, ``{kind}_total_chars``,
        ``{kind}_omitted_chars`` and ``{kind}_total_lines``.
    """
    if not text or max_chars is None:
        return text, {}
    budget = max(int(max_chars), _MIN_MAX_CHARS)
    if len(text) <= budget:
        return text, {}

    total_chars = len(text)
    total_lines = text.count("\n") + 1
    head_budget = (budget * 2) // 3
    tail_budget = budget - head_budget
    head = text[:head_budget]
    tail = text[total_chars - tail_budget:]
    omitted = total_chars - head_budget - tail_budget

    marker = (
        f"\n\n... [{kind} truncated: {omitted} of {total_chars} chars "
        f"({total_lines} total lines) omitted from the middle. The omitted "
        f"content is NOT shown here — do not assume it is empty or unchanged. "
        f"Narrow your request (a more specific path/pattern, grep, head/tail, "
        f"or a smaller max_results) to see the rest.] ...\n\n"
    )
    meta = {
        f"{kind}_truncated": True,
        f"{kind}_total_chars": total_chars,
        f"{kind}_omitted_chars": omitted,
        f"{kind}_total_lines": total_lines,
    }
    return head + marker + tail, meta
