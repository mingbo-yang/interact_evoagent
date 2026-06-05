"""EvoAgent terminal UI theme."""

from rich.style import Style
from rich.theme import Theme

EVO_THEME = Theme({
    "evo.primary": Style(color="cyan"),
    "evo.secondary": Style(color="bright_magenta"),
    "evo.accent": Style(color="bright_blue"),
    "evo.success": Style(color="green"),
    "evo.warning": Style(color="yellow"),
    "evo.error": Style(color="red"),
    "evo.muted": Style(color="grey62"),
    "evo.tool": Style(color="blue"),
    "evo.reasoning": Style(color="grey70", italic=True),
    "evo.user": Style(),
    "evo.plan": Style(color="yellow"),
    "evo.auto": Style(color="magenta"),
    "evo.default": Style(color="cyan"),
    "evo.logo": Style(color="cyan", bold=True),
    "evo.prompt": Style(color="bright_cyan", bold=True),
    "evo.spinner": Style(color="bright_magenta"),
    "evo.heading": Style(color="cyan", bold=True),
    "evo.border": Style(color="grey42"),
})

MODE_COLORS = {"default": "cyan", "plan": "yellow", "auto": "magenta"}
