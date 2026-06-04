"""evoagent chat — interactive chat mode."""

import asyncio

import typer

from evoagent.cli.main import app
from evoagent.cli.utils import create_agent


@app.command("chat")
def chat(
    mock: bool = typer.Option(False, "--mock", help="Use mock LLM (no API key needed)."),
):
    """Start an interactive chat session."""
    agent = create_agent(mock=mock)

    async def _chat():
        typer.echo("EvoAgent Chat (type 'exit' to quit)")
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break
            response = await agent.chat(user_input)
            typer.echo(f"Agent: {response}")

    asyncio.run(_chat())
