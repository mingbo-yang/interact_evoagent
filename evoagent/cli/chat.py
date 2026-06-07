"""evoagent chat — interactive chat mode."""

import asyncio

import typer

from evoagent.cli.main import app


@app.command("chat")
def chat(
    mock: bool = typer.Option(False, "--mock", help="Use mock LLM (no API key needed)."),
):
    """Start the full-screen interactive EvoAgent TUI."""
    # ``--mock`` is kept for CLI compatibility. The interactive runtime already
    # falls back to a MockLLMProvider when no provider/API key is configured.
    _ = mock
    from evoagent.cli.interactive import run_interactive

    asyncio.run(run_interactive())
