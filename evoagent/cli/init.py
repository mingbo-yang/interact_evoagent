"""evoagent init — initialize project."""

from pathlib import Path

import typer

from evoagent.cli.main import init_app

DEFAULT_CONFIG = """# EvoAgent configuration
project:
  name: evoagent
  version: "0.1.0"
  work_dir: .

models:
  default:
    provider: deepseek
    model: deepseek-chat
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY

runtime:
  max_turns: 20

permissions:
  mode: review

logging:
  enabled: true
  traces_dir: .runs
"""


@init_app.command("init")
def init_project(
    force: bool = typer.Option(False, "--force", help="Overwrite existing files."),
):
    """Initialize EvoAgent in the current directory."""
    cwd = Path.cwd()
    config_path = cwd / "evoagent.yaml"

    if config_path.exists() and not force:
        typer.echo("evoagent.yaml already exists. Use --force to overwrite.")
        raise typer.Exit(1)

    config_path.write_text(DEFAULT_CONFIG)
    (cwd / ".evoagent").mkdir(exist_ok=True)
    (cwd / ".runs").mkdir(exist_ok=True)

    typer.echo("✓ Created evoagent.yaml")
    typer.echo("✓ Created .evoagent/")
    typer.echo("✓ Created .runs/")
    typer.echo("\nNext: export DEEPSEEK_API_KEY=your-key && evoagent run 'hello'")
