"""Tool agent example — using built-in tools with MockLLMProvider."""

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

        # Create test files
        (workspace / "notes.txt").write_text("Meeting at 3pm\nBuy milk\nCall dentist")

        # Mock LLM returns a plan to list directory and read files
        mock = MockLLMProvider(fixed_text='{"risk_level":"low","steps":[{"goal":"List workspace directory","action_type":"tool","tool_name":"list_directory","arguments":{"path":"."},"expected_result":"List of files"},{"goal":"Read notes.txt","action_type":"tool","tool_name":"read_file","arguments":{"path":"notes.txt"},"expected_result":"File content"},{"goal":"Finish","action_type":"finish"}]}')
        router = ModelRouter(providers={"planner": mock, "default": mock, "executor": mock})

        tools = create_builtin_registry(workspace)
        agent = Agent(model_router=router, tool_registry=tools, workspace=workspace)

        result = await agent.run("List files and read notes.txt")
        print(f"Success: {result.success}")
        print(f"Steps:   {result.steps_taken}")
        print(f"Tools:   {result.tool_calls}")
        print(f"Result:  {result.final_answer}")


if __name__ == "__main__":
    asyncio.run(main())
