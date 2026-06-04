"""evoagent code — code agent mode."""

import asyncio

import typer

from evoagent.cli.main import app
from evoagent.cli.utils import console


@app.command("code")
def code_task(
    task: str = typer.Argument(None, help="Code task description."),
    mock: bool = typer.Option(False, "--mock", help="Use mock mode (no API key needed)."),
):
    """Run the Code Agent on a software task."""
    from pathlib import Path

    from evoagent.code.agent import CodeAgent

    c = console()

    if not task:
        task = typer.prompt("Task")

    async def _run():
        agent = CodeAgent(workspace=Path.cwd(), max_iterations=3)
        c.print(f"[bold]Code Task:[/bold] {task}")
        result = await agent.run(task)
        c.print(f"[bold]Success:[/bold] {'✅' if result.success else '❌'}")
        c.print(f"[bold]Changed:[/bold] {result.changed_files}")
        if result.diff:
            c.print(f"[dim]{result.diff[:500]}[/dim]")
        if result.errors:
            c.print(f"[red]Errors: {result.errors}[/red]")

    asyncio.run(_run())
