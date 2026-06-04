"""evoagent config — show configuration."""

import typer

from evoagent.cli.main import config_app

try:
    from rich import print as rprint
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


@config_app.command("show")
def config_show(
    path: str = typer.Option("evoagent.yaml", "--path", help="Path to config file."),
):
    """Display the current EvoAgent configuration."""
    from pathlib import Path

    import yaml

    p = Path(path)
    if not p.exists():
        typer.echo(f"No config found at {path}. Run 'evoagent init' first.")
        raise typer.Exit(1)

    data = yaml.safe_load(p.read_text())
    if HAS_RICH:
        rprint(data)
    else:
        import json
        typer.echo(json.dumps(data, indent=2, default=str))
