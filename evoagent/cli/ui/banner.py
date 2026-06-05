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
        logo.append(line, style="bold cyan")
        logo.append("\n")

    info = Table.grid(padding=(0, 1))
    info.add_column(style="grey62", width=10)
    info.add_column(style="cyan")
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
    tips.append("Tips for getting started\n", style="bold cyan")
    tips.append("/init    Create project instruction file\n", style="grey62")
    tips.append("/help    View all commands\n", style="grey62")
    tips.append("/mode    Switch runtime mode\n", style="grey62")
    tips.append("/model   Switch model/provider\n", style="grey62")
    tips.append("\n")
    tips.append("What's new\n", style="bold cyan")
    tips.append("• Persistent multi-turn conversation\n")
    tips.append("• Cross-provider model switching\n")
    tips.append("• Interactive plan approval\n")

    right = Panel(tips, title="Getting Started", border_style="grey42")

    if is_narrow:
        content = Table.grid(padding=(1, 0))
        content.add_row(left)
        content.add_row("")
        content.add_row(right)
    else:
        content = Columns([left, right])

    title = Text("EvoAgent ", style="bold cyan")
    title.append(f"{version}", style="cyan")
    title.append(f"  {workspace}", style="grey62")

    return Panel(content, title=title, border_style="grey42")


def render_simple_startup(version: str, model_label: str, mode: str):
    """Plain-text startup for non-TTY environments."""
    print(f"EvoAgent {version}")
    print(f"Model: {model_label}  Mode: {mode}")
    print("Type /help for commands, /exit to quit.\n")
