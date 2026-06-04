"""Basic agent example — uses MockLLMProvider, no real API calls."""

import asyncio
import tempfile
from pathlib import Path

from evoagent.core.agent import Agent
from evoagent.models.factory import MockLLMProvider
from evoagent.models.router import ModelRouter
from evoagent.tools.builtin import create_builtin_registry


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)

        # Create a file for the agent to read
        (workspace / "hello.txt").write_text("Hello, EvoAgent!")
        (workspace / "data.csv").write_text("name,score\nAlice,95\nBob,87")

        # Use MockLLMProvider for planner
        mock = MockLLMProvider(fixed_text='{"risk_level":"low","steps":[{"goal":"List files","action_type":"tool","tool_name":"list_directory","arguments":{"path":"."},"expected_result":"See files"},{"goal":"Read hello.txt","action_type":"tool","tool_name":"read_file","arguments":{"path":"hello.txt"},"expected_result":"File content"},{"goal":"Finish","action_type":"finish"}]}')
        router = ModelRouter(providers={"planner": mock, "default": mock})

        tools = create_builtin_registry(workspace)
        agent = Agent(model_router=router, tool_registry=tools, workspace=workspace)

        result = await agent.run("Show me what's in this directory and read hello.txt")
        print(f"Success: {result.success}")
        print(f"Answer:  {result.final_answer}")
        print(f"Steps:   {result.steps_taken}")
        print(f"Errors:  {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
