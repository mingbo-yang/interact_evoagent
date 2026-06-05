"""EvoAgent welcome banner."""

import shutil

from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

LOGO_LINES = [
    "   ◢██◣",
    "  ◥████◤     EvoAgent",
    "    ▀▀",
]


def render_banner(version: str, model_label: str, mode: str, workspace: str,
                  context_pct: int = 0, billing: str = "API") -> Panel:
    """Render the welcome banner.

    Args:
        version: Version string like 'v0.4.1'.
        model_label: e.g. 'deepseek:v4-pro'.
        mode: Agent mode (default/plan/auto).
        workspace: Current workspace path.
        context_pct: Context usage percentage.
        billing: Billing type.
    """
    term_width = shutil.get_terminal_size().columns
    is_narrow = term_width < 80

    # Left panel: Logo + info
    logo = Text()
    for line in LOGO_LINES:
        logo.append(line, style="evo.logo")
        logo.append("\n")

    info = Table.grid(padding=(0, 1))
    info.add_column(style="evo.muted", width=10)
    info.add_column(style="evo.primary")
    info.add_row("Model:", model_label)
    info.add_row("Billing:", billing)
    info.add_row("Mode:", mode)
    info.add_row("Context:", f"{context_pct}%")

    left = Table.grid(padding=(1, 0))
    left.add_row(logo)
    left.add_row("")
    left.add_row(info)

    # Right panel: Tips + What's new
    tips = Text()
    tips.append("Tips for getting started\n", style="evo.heading")
    tips.append("/init    Create project instruction file\n", style="evo.muted")
    tips.append("/help    View all commands\n", style="evo.muted")
    tips.append("/mode    Switch runtime mode\n", style="evo.muted")
    tips.append("/model   Switch model/provider\n", style="evo.muted")
    tips.append("\n")
    tips.append("What's new\n", style="evo.heading")
    tips.append("• Persistent multi-turn conversation\n")
    tips.append("• Cross-provider model switching\n")
    tips.append("• Interactive plan approval\n")

    right = Panel(tips, title="Getting Started", border_style="evo.border")

    if is_narrow:
        content = Table.grid(padding=(1, 0))
        content.add_row(left)
        content.add_row("")
        content.add_row(right)
    else:
        content = Columns([left, right])

    title = Text(f"EvoAgent {version}", style="evo.primary bold")
    title.append(f"  {workspace}", style="evo.muted")

    return Panel(content, title=title, border_style="evo.border")


def render_simple_startup(version: str, model_label: str, mode: str):
    """Plain-text startup for non-TTY environments."""
    print(f"EvoAgent {version}")
    print(f"Model: {model_label}  Mode: {mode}")
    print("Type /help for commands, /exit to quit.\n")
