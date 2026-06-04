"""evoagent run — execute a one-shot task."""

import asyncio

import typer

from evoagent.cli.main import app
from evoagent.cli.utils import console, create_agent


@app.command("run")
def run_task(
    task: str = typer.Argument(..., help="Task description."),
    mock: bool = typer.Option(False, "--mock", help="Use mock LLM (no API key needed)."),
    max_steps: int = typer.Option(20, "--max-steps", help="Maximum execution steps."),
):
    """Run a one-shot agent task."""
    c = console()

    async def _run():
        agent = create_agent(mock=mock)
        c.print(f"[bold]Task:[/bold] {task}")
        c.print("[dim]Running...[/dim]")
        result = await agent.run(task)
        c.print(f"[bold]Success:[/bold] {'✅' if result.success else '❌'}")
        c.print(f"[bold]Answer:[/bold] {result.final_answer or result.error}")
        c.print(f"[bold]Steps:[/bold] {result.steps_taken}")
        if result.error:
            c.print(f"[dim]Error: {result.error}[/dim]")

    asyncio.run(_run())
