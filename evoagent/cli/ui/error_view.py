"""Error view — clean error display with secret redaction."""

from evoagent.core.ids import generate_id
from evoagent.core.redaction import redact_text


def redact_secrets(text: str) -> str:
    """Redact API keys, tokens, and passwords from text.

    Thin backward-compatible wrapper over the central
    :func:`evoagent.core.redaction.redact_text`.
    """
    return redact_text(text)


def render_error(exception: Exception, debug: bool = False) -> str:
    """Render a clean error message.

    Args:
        exception: The caught exception.
        debug: If True, include full traceback (still redacted).

    Returns:
        Formatted error string.
    """
    from evoagent.cli.ui.symbols import sym

    error_id = generate_id("err")
    msg = redact_secrets(str(exception))

    lines = [
        f" {sym('fail')} Turn failed",
        f"   {msg[:200]}",
        f"   {sym('dot')} error id {error_id}",
    ]
    if not debug:
        lines.append(f"   {sym('dot')} run /debug for details")
    else:
        import traceback
        tb = traceback.format_exc()
        lines.append(f"\n   {redact_secrets(tb)[:2000]}")

    return "\n".join(lines)
