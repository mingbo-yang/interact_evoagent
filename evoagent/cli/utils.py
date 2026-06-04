"""CLI utilities."""

import os
from pathlib import Path

from evoagent.core.agent import Agent
from evoagent.models.factory import MockLLMProvider
from evoagent.models.router import ModelRouter
from evoagent.tools.builtin import create_builtin_registry


def check_api_key() -> bool:
    """Check if DEEPSEEK_API_KEY is set. Returns True if available."""
    return bool(os.getenv("DEEPSEEK_API_KEY"))


def create_agent(mock: bool = False) -> Agent:
    """Create an Agent instance, optionally using mock LLM."""
    workspace = Path.cwd()
    tools = create_builtin_registry(workspace)

    if mock or not check_api_key():
        if not mock:
            from rich.console import Console
            Console().print("[yellow]No DEEPSEEK_API_KEY found. Using --mock mode.[/yellow]")
        router = ModelRouter(providers={"planner": MockLLMProvider(fixed_text='{"risk_level":"low","steps":[{"goal":"Execute task","action_type":"tool","tool_name":"list_directory","arguments":{"path":"."}},{"goal":"Finish","action_type":"finish"}]}'),
                                        "executor": MockLLMProvider(fixed_text="Task executed."),
                                        "critic": MockLLMProvider(fixed_text="OK"),
                                        "default": MockLLMProvider(fixed_text="Mock response.")})
        return Agent(model_router=router, tool_registry=tools, workspace=workspace)

    # Real agent with DeepSeek
    from evoagent.models.deepseek import DeepSeekProvider
    provider = DeepSeekProvider()
    router = ModelRouter(providers={"planner": provider, "executor": provider, "critic": provider, "default": provider})
    return Agent(model_router=router, tool_registry=tools, workspace=workspace)


def console():
    from rich.console import Console
    return Console()
