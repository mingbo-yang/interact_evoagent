"""EvoAgent welcome banner — a refined, single rounded card."""

import shutil

from rich import box
from rich.cells import cell_len
from rich.panel import Panel
from rich.text import Text

from evoagent.cli.ui.symbols import sym

# Compact geometric wordmark.
LOGO_LINES = [
    "▟█▙",
    "▜█▛",
]

_PAD = 3  # horizontal panel padding


def _pad_to(text: Text, width: int) -> Text:
    """Right-pad a Text with spaces to an exact display width."""
    gap = width - cell_len(text.plain)
    if gap > 0:
        text.append(" " * gap)
    return text


def render_banner(version: str, model_label: str, mode: str, workspace: str,
                  context_pct: int = 0, billing: str = "API") -> Panel:
    """Render the welcome banner as a single cohesive rounded card.

    Args:
        version: Version string like 'v1.0.0'.
        model_label: e.g. 'deepseek:chat'.
        mode: Agent mode (default/plan/auto).
        workspace: Current workspace path.
        context_pct: Context usage percentage.
        billing: Billing type.
    """
    term_width = shutil.get_terminal_size((80, 24)).columns
    panel_width = min(term_width, 88)
    inner = panel_width - 2 - 2 * _PAD  # borders + horizontal padding
    is_narrow = panel_width < 72

    lines: list[Text] = []

    # Logo / tagline.
    logo = Text()
    logo.append("▟█▙  ", style="evo.logo")
    logo.append("autonomous coding agent", style="evo.muted")
    lines.append(_pad_to(logo, inner))
    lines.append(Text(" " * inner))

    # Info rows — manual two-column layout for perfect alignment.
    key_w = 9
    lines.append(_info_row("model", Text(model_label, style="evo.value"), key_w, inner))
    lines.append(_info_row("mode", _mode_text(mode), key_w, inner))
    lines.append(_info_row("billing", Text(billing, style="evo.value"), key_w, inner))
    lines.append(_info_row("context", _context_bar(context_pct), key_w, inner))
    lines.append(Text(" " * inner))

    # Hint row.
    items = ([("/help", "commands"), ("/model", "switch model"), ("/exit", "quit")]
             if is_narrow else
             [("/help", "commands"), ("/model", "switch model"),
              ("/mode", "change mode"), ("/exit", "quit")])
    hint = Text()
    dot = sym("dot")
    for i, (cmd, desc) in enumerate(items):
        if i:
            hint.append(f"   {dot}   ", style="evo.faint")
        hint.append(cmd, style="evo.accent")
        hint.append(f" {desc}", style="evo.muted")
    lines.append(_pad_to(hint, inner))

    body = Text("\n").join(lines)
    body.justify = "left"

    title = Text()
    title.append(" EvoAgent ", style="evo.heading")
    title.append(version, style="evo.muted")
    subtitle = Text(_shorten_path(workspace, max(20, inner)), style="evo.faint")

    return Panel(
        body,
        title=title,
        title_align="left",
        subtitle=subtitle,
        subtitle_align="right",
        border_style="evo.border",
        box=box.ROUNDED,
        padding=(1, _PAD),
        width=panel_width,
    )


def _info_row(key: str, value: Text, key_w: int, inner: int) -> Text:
    row = Text()
    row.append(key, style="evo.key")
    row.append(" " * max(1, key_w - len(key)))
    row.append_text(value)
    return _pad_to(row, inner)


def _mode_text(mode: str) -> Text:
    style = {"plan": "evo.plan", "auto": "evo.auto"}.get(mode, "evo.default")
    return Text(mode, style=style)


def _context_bar(pct: int, width: int = 16) -> Text:
    pct = max(0, min(100, int(pct)))
    filled = round(width * pct / 100)
    bar = Text()
    bar.append("█" * filled, style="evo.accent")
    bar.append("░" * (width - filled), style="evo.faint")
    bar.append(f"  {pct}%", style="evo.muted")
    return bar


def _shorten_path(path: str, limit: int) -> str:
    if len(path) <= limit:
        return path
    return "…" + path[-(limit - 1):]


def render_simple_startup(version: str, model_label: str, mode: str):
    """Plain-text startup for non-TTY environments."""
    print(f"EvoAgent {version}")
    print(f"Model: {model_label}  Mode: {mode}")
    print("Type /help for commands, /exit to quit.\n")


# Backwards-compatible alias: some callers used a Columns layout previously.
def render_welcome(*args, **kwargs) -> Panel:  # pragma: no cover - thin alias
    return render_banner(*args, **kwargs)
