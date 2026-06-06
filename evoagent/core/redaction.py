"""Central secret redaction for telemetry, logs, and session persistence.

Two entry points:

* :func:`redact_text` — redact secrets from a free-form string. Patterns are
  written to stop at structural delimiters (quotes, commas, braces, whitespace)
  so that redacting a string that *happens* to contain serialized JSON does not
  corrupt the surrounding structure.
* :func:`redact_obj` — recursively redact a JSON-compatible Python structure
  (dict/list/scalars) **before** it is serialized. String leaves are passed
  through :func:`redact_text`; dict values whose key looks sensitive (``token``,
  ``api_key``, ``password``, ``secret``, ``authorization``, …) are replaced
  wholesale. Operating on the structure rather than the serialized string is the
  safe way to redact reloadable JSON (e.g. ``state.json``, ``session.json``):
  the output always round-trips through ``json.loads``.

Only telemetry / persistence sinks should be redacted. Never run redaction over
content destined for the user's actual workspace files.
"""

import re
from typing import Any

REDACTED = "***REDACTED***"

# Keys whose *value* is always sensitive, regardless of content. Matched
# case-insensitively against the final path segment of a dict key.
_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "api-key",
    "authorization",
    "auth_token",
    "access_token",
    "refresh_token",
    "token",
    "password",
    "passwd",
    "secret",
    "client_secret",
    "private_key",
    "session_token",
}

# Value charset for ``key=value`` / ``key: value`` matches: stop at the first
# structural delimiter so we never swallow a closing JSON quote, comma, or brace.
_VALUE = r'[^\s"\',}{)\]]+'

_PATTERNS: list[re.Pattern[str]] = [
    # Bearer tokens — token charset only (won't eat a trailing quote/comma).
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=\-]+"),
    # OpenAI / DeepSeek style keys.
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"),
    # GitHub tokens (ghp_, gho_, ghu_, ghs_, ghr_) and fine-grained PATs.
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    # AWS access key IDs.
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # Slack tokens.
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    # Google API keys.
    re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}"),
    # key=value / key: value for sensitive identifiers (redact only the value).
    re.compile(
        r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|"
        r"client[_-]?secret|password|passwd|secret|token)"
        r"(\s*[:=]\s*)(['\"]?)(" + _VALUE + r")",
    ),
]

# Index of the value group within the last (key=value) pattern.
_KV_PATTERN = _PATTERNS[-1]


def _sub_kv(match: re.Match[str]) -> str:
    """Replacement for the key=value pattern: keep key/sep/quote, redact value."""
    key, sep, quote, _value = match.group(1), match.group(2), match.group(3), match.group(4)
    return f"{key}{sep}{quote}{REDACTED}"


def redact_text(text: str) -> str:
    """Redact secrets from a free-form string.

    Safe to call on strings that embed serialized JSON: patterns stop at
    structural delimiters, so surrounding syntax is preserved.
    """
    if not text:
        return text
    for pattern in _PATTERNS:
        if pattern is _KV_PATTERN:
            text = pattern.sub(_sub_kv, text)
        else:
            text = pattern.sub(REDACTED, text)
    return text


def _is_sensitive_key(key: str) -> bool:
    return key.strip().lower() in _SENSITIVE_KEYS


def redact_obj(obj: Any) -> Any:
    """Recursively redact a JSON-compatible structure before serialization.

    * ``dict`` — values under sensitive keys are replaced with ``REDACTED``;
      other values are redacted recursively.
    * ``list`` / ``tuple`` — each element is redacted recursively.
    * ``str`` — passed through :func:`redact_text`.
    * other scalars — returned unchanged.

    The returned structure is JSON-serializable and round-trips through
    ``json.loads`` (no syntax corruption), unlike redacting a serialized string.
    """
    if isinstance(obj, dict):
        out: dict[Any, Any] = {}
        for key, value in obj.items():
            if isinstance(key, str) and _is_sensitive_key(key):
                out[key] = REDACTED
            else:
                out[key] = redact_obj(value)
        return out
    if isinstance(obj, (list, tuple)):
        return [redact_obj(item) for item in obj]
    if isinstance(obj, str):
        return redact_text(obj)
    return obj
