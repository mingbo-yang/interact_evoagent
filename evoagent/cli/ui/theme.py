"""EvoAgent terminal UI theme — a cohesive, modern palette.

Soft, low-saturation colours (sky / violet / amber) give a premium, calm feel
similar to high-end commercial agent CLIs. Rich automatically downgrades the
truecolor hex values on 256/16-colour terminals.
"""

from rich.style import Style
from rich.theme import Theme

# ── Core palette ──────────────────────────────────────────────────────
_ACCENT = "#7DD3FC"      # sky — primary brand accent
_ACCENT_DIM = "#38BDF8"  # deeper sky
_VIOLET = "#C4B5FD"      # secondary
_GREEN = "#86EFAC"       # success
_AMBER = "#FCD34D"       # warning / highlight
_RED = "#FCA5A5"         # error
_MUTED = "#8B93A7"       # secondary text
_FAINT = "#5B6478"       # tertiary / borders
_TEXT = "#E5E9F0"        # primary text

EVO_THEME = Theme({
    # Brand / structure
    "evo.primary": Style(color=_ACCENT, bold=True),
    "evo.secondary": Style(color=_VIOLET),
    "evo.accent": Style(color=_ACCENT_DIM),
    "evo.logo": Style(color=_ACCENT, bold=True),
    "evo.heading": Style(color=_ACCENT, bold=True),
    "evo.border": Style(color=_FAINT),
    "evo.text": Style(color=_TEXT),

    # Semantic
    "evo.success": Style(color=_GREEN),
    "evo.warning": Style(color=_AMBER),
    "evo.error": Style(color=_RED, bold=True),
    "evo.muted": Style(color=_MUTED),
    "evo.faint": Style(color=_FAINT),

    # Conversation surfaces
    "evo.tool": Style(color=_ACCENT),
    "evo.tool.name": Style(color=_ACCENT, bold=True),
    "evo.tool.args": Style(color=_MUTED),
    "evo.tool.out": Style(color=_MUTED),
    "evo.reasoning": Style(color=_MUTED, italic=True),
    "evo.user": Style(color=_TEXT),
    "evo.prompt": Style(color=_ACCENT, bold=True),
    "evo.spinner": Style(color=_VIOLET),

    # Mode badges
    "evo.plan": Style(color=_AMBER, bold=True),
    "evo.auto": Style(color=_VIOLET, bold=True),
    "evo.default": Style(color=_ACCENT, bold=True),

    # Key/value rows
    "evo.key": Style(color=_MUTED),
    "evo.value": Style(color=_TEXT),
})

# Mode → accent colour (used by prompt + badges).
MODE_COLORS = {"default": _ACCENT, "plan": _AMBER, "auto": _VIOLET}
