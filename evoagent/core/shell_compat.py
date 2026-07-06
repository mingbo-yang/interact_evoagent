"""Cross-platform normalization for simple shell commands used by tools/tests."""

import os
import re
import sys


def normalize_shell_command(command: str) -> str:
    """Normalize a subset of POSIX-only commands for Windows cmd.exe."""
    if os.name != "nt":
        return command

    cmd = (command or "").strip()
    if not cmd:
        return command

    if re.fullmatch(r"true", cmd, flags=re.IGNORECASE):
        return f'"{sys.executable}" -c "import sys; sys.exit(0)"'
    if re.fullmatch(r"false", cmd, flags=re.IGNORECASE):
        return f'"{sys.executable}" -c "import sys; sys.exit(1)"'

    m = re.fullmatch(r"sleep\s+(\d+(?:\.\d+)?)", cmd, flags=re.IGNORECASE)
    if m:
        return f'"{sys.executable}" -c "import time; time.sleep({m.group(1)})"'

    return command

