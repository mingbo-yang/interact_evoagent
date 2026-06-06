"""Context management — token estimation + history compaction (P0.6).

Long agent runs accumulate large message histories (especially verbose tool
outputs) that eventually overflow the model's context window. This module
provides a cheap token estimate and a compaction routine that, once a token
budget is exceeded, replaces the older part of the conversation with a compact
structured digest while keeping the recent messages verbatim.

The digest deliberately preserves the state the agent needs to keep working:
the original task, files changed, recent failures, the latest progress note,
and (when available) the current todo list. Compaction never splits an
assistant/tool-call group, so the resulting history stays valid for providers.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from evoagent.core.message import Message, MessageRole

DEFAULT_TOKEN_BUDGET = 48_000
DEFAULT_KEEP_RECENT_TOKENS = 24_000

# Tools whose calls mean a file was created/modified — surfaced in the digest.
_WRITE_TOOLS = {
    "write_file", "edit_file", "multi_edit", "apply_patch",
    "create_file", "delete_file",
}
# Substrings that mark a tool result as a failure worth remembering.
_FAILURE_HINTS = ("error", "failed", "traceback", "exception", "permission denied",
                  "not found", "exit code")


def estimate_tokens(text: str | None) -> int:
    """Cheap, provider-agnostic token estimate (~4 chars/token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def message_tokens(m: Message) -> int:
    """Approximate token cost of a single message, including tool calls."""
    total = 8  # per-message role/formatting overhead
    total += estimate_tokens(m.content)
    if m.name:
        total += 2
    for tc in (m.tool_calls or []):
        total += 8 + estimate_tokens(tc.name)
        try:
            total += estimate_tokens(json.dumps(tc.arguments))
        except (TypeError, ValueError):
            total += estimate_tokens(str(tc.arguments))
    return total


def messages_tokens(messages: list[Message]) -> int:
    return sum(message_tokens(m) for m in messages)


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + " …"


def _looks_failed(content: str) -> bool:
    low = (content or "").lower()
    return any(h in low for h in _FAILURE_HINTS)


def summarize_dropped(dropped: list[Message], extra_state: str | None = None) -> str:
    """Build a compact structured digest of the messages being compacted."""
    lines = ["[Earlier conversation was compacted to save context. Summary of "
             "what happened so far:]"]

    # Carry forward an earlier compaction summary so the chain of original
    # task / constraints is not lost across repeated compactions.
    prior = [m for m in dropped if m.metadata.get("compacted") and m.content]
    if prior:
        lines.append("Earlier summary:\n" + _clip(prior[-1].content, 1500))

    users = [m for m in dropped
             if m.role == MessageRole.USER and m.content and not m.metadata.get("compacted")]
    if users:
        lines.append("Original task: " + _clip(users[0].content, 800))
        later = users[1:]
        if later:
            lines.append("Additional user instructions:\n"
                         + "\n".join(f"- {_clip(u.content, 300)}" for u in later[-5:]))

    files: list[str] = []
    for m in dropped:
        for tc in (m.tool_calls or []):
            if tc.name in _WRITE_TOOLS:
                args = tc.arguments if isinstance(tc.arguments, dict) else {}
                path = args.get("path") or args.get("file_path")
                if path and path not in files:
                    files.append(str(path))
    if files:
        lines.append("Files changed: " + ", ".join(files[:25]))

    successes = [
        _clip(m.content, 200)
        for m in dropped
        if m.role == MessageRole.TOOL and m.content and not _looks_failed(m.content)
    ]
    if successes:
        lines.append("Recent successful observations:\n"
                     + "\n".join(f"- {s}" for s in successes[-3:]))

    failures = [
        _clip(m.content, 240)
        for m in dropped
        if m.role == MessageRole.TOOL and m.content and _looks_failed(m.content)
    ]
    if failures:
        lines.append("Notable earlier failures:\n"
                     + "\n".join(f"- {f}" for f in failures[-5:]))

    last_note = next((m for m in reversed(dropped)
                      if m.role == MessageRole.ASSISTANT and m.content), None)
    if last_note:
        lines.append("Most recent progress note: " + _clip(last_note.content, 500))

    if extra_state:
        lines.append(extra_state.strip())

    return "\n".join(lines)


def compact_messages(
    messages: list[Message],
    *,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    keep_recent_tokens: int = DEFAULT_KEEP_RECENT_TOKENS,
    state_provider: Callable[[], str | None] | None = None,
    summarizer: Callable[[list[Message]], str] | None = None,
) -> tuple[list[Message], bool]:
    """Return a possibly-compacted copy of ``messages`` and whether it changed.

    When the estimated token count exceeds ``token_budget``, the oldest
    messages are replaced by a single summary message while the most recent
    messages (up to ``keep_recent_tokens``) are kept verbatim. The cut point is
    chosen so it never lands inside an assistant/tool-call group, keeping the
    history valid for providers.
    """
    if token_budget <= 0 or messages_tokens(messages) <= token_budget:
        return messages, False

    # Walk back from the end accumulating the recent window to keep.
    keep_start = len(messages)
    acc = 0
    for idx in range(len(messages) - 1, -1, -1):
        acc += message_tokens(messages[idx])
        keep_start = idx
        if acc >= keep_recent_tokens:
            break

    # The kept region must not begin with an orphan tool message (its owning
    # assistant turn would be in the dropped part). Push such tool messages
    # into the dropped/summarized side.
    while keep_start < len(messages) and messages[keep_start].role == MessageRole.TOOL:
        keep_start += 1

    if keep_start <= 0:
        return messages, False  # nothing old enough to drop safely

    dropped = messages[:keep_start]
    kept = messages[keep_start:]
    extra_state = state_provider() if state_provider else None
    if summarizer is not None:
        summary_text = summarizer(dropped)
    else:
        summary_text = summarize_dropped(dropped, extra_state)

    summary_msg = Message(role=MessageRole.USER, content=summary_text,
                          metadata={"compacted": True, "dropped": len(dropped)})
    new_messages = [summary_msg, *kept]
    # Guard against pathological no-progress compaction (e.g. a single huge
    # recent message that cannot be dropped): if we did not actually shrink the
    # history, leave it unchanged so the loop does not rebuild a summary every
    # step.
    if messages_tokens(new_messages) >= messages_tokens(messages):
        return messages, False
    return new_messages, True
