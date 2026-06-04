"""ID generation utilities."""

import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with an optional prefix.

    Args:
        prefix: Optional prefix, e.g. "run", "step", "msg".

    Returns:
        A string like "run_a1b2c3d4" or "a1b2c3d4" if no prefix.
    """
    short = uuid.uuid4().hex[:12]
    return f"{prefix}_{short}" if prefix else short
