"""Multi-agent debate example — two agents propose solutions, critic judges."""

import asyncio

from evoagent.models.factory import MockLLMProvider
from evoagent.models.router import ModelRouter
from evoagent.multi_agent.manager import MultiAgentManager
from evoagent.multi_agent.protocols import DebateProtocol
from evoagent.multi_agent.roles import create_coder, create_critic, create_researcher


async def main():
    # Mock LLMs with different responses per agent
    mock_a = MockLLMProvider(fixed_text="Solution A: Use caching with Redis to speed up database queries.")
    mock_b = MockLLMProvider(fixed_text="Solution B: Use connection pooling and query optimization instead of caching.")
    mock_judge = MockLLMProvider(fixed_text="Solution B is better because it addresses the root cause without adding infrastructure complexity.")

    router = ModelRouter(providers={
        "default": mock_a,
        "executor": mock_b,
        "critic": mock_judge,
    })

    researcher = create_researcher(model_router=router)
    coder = create_coder(model_router=ModelRouter(providers={"default": mock_b, "executor": mock_b}))
    critic = create_critic(model_router=router)

    mgr = MultiAgentManager()
    mgr.register("Researcher", researcher)
    mgr.register("Coder", coder)
    mgr.register("Critic", critic)

    protocol = DebateProtocol(judge_name="Critic")
    result = await mgr.run("How to improve database performance?", protocol)

    print(f"Success: {result.success}")
    print(f"Final:   {result.final_answer[:200]}")
    print(f"Agents:  {list(result.agent_outputs.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
