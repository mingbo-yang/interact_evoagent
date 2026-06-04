"""Multi-agent debugging example — Pipeline: Planner → Coder → Tester → Critic."""

import asyncio

from evoagent.models.factory import MockLLMProvider
from evoagent.models.router import ModelRouter
from evoagent.multi_agent.manager import MultiAgentManager
from evoagent.multi_agent.protocols import PipelineProtocol
from evoagent.multi_agent.roles import (
    create_coder,
    create_critic,
    create_planner,
    create_tester,
)


async def main():
    # Mock LLM for all roles
    mock = MockLLMProvider(fixed_text="Analysis complete. The bug is in the authentication module. Fix: add input validation on line 42.")
    router = ModelRouter(providers={"planner": mock, "executor": mock, "critic": mock, "default": mock})

    # Create agents
    planner = create_planner(model_router=router)
    coder = create_coder(model_router=router)
    tester = create_tester(model_router=router)
    critic = create_critic(model_router=router)

    # Setup manager
    mgr = MultiAgentManager()
    mgr.register("Planner", planner)
    mgr.register("Coder", coder)
    mgr.register("Tester", tester)
    mgr.register("Critic", critic)

    # Run pipeline
    protocol = PipelineProtocol(order=["Planner", "Coder", "Tester", "Critic"])
    result = await mgr.run("Fix the login timeout bug", protocol)

    print(f"Success: {result.success}")
    print(f"Final:   {result.final_answer[:200]}")
    print(f"Agents:  {list(result.agent_outputs.keys())}")
    print(f"Messages: {len(result.messages)}")


if __name__ == "__main__":
    asyncio.run(main())
