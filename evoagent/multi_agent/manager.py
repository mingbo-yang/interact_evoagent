"""MultiAgentManager — register agents and run protocols."""

from evoagent.core.errors import EvoAgentError
from evoagent.core.ids import generate_id
from evoagent.multi_agent.base import RoleAgent
from evoagent.multi_agent.protocols import BaseProtocol, ProtocolResult


class MultiAgentManager:
    """Central manager for multi-agent collaboration.

    Registers agents, runs protocols, and maintains shared
    execution state (run_id, event tracking).

    Usage:
        mgr = MultiAgentManager()
        mgr.register("planner", planner_agent)
        result = await mgr.run("Build a web app", PipelineProtocol(order=["planner", "coder", "critic"]))
    """

    def __init__(self):
        self._agents: dict[str, RoleAgent] = {}

    def register(self, name: str, agent: RoleAgent) -> None:
        """Register a role agent."""
        self._agents[name] = agent

    def get(self, name: str) -> RoleAgent:
        """Get a registered agent by name.

        Raises:
            EvoAgentError: If agent not found.
        """
        if name not in self._agents:
            raise EvoAgentError(f"Agent '{name}' not registered. Available: {list(self._agents.keys())}")
        return self._agents[name]

    def list_agents(self) -> list[str]:
        return sorted(self._agents.keys())

    async def run(self, task: str, protocol: BaseProtocol) -> ProtocolResult:
        """Run a multi-agent protocol.

        Args:
            task: The task description.
            protocol: The collaboration protocol to use.

        Returns:
            ProtocolResult with success, final_answer, and messages.
        """
        run_id = generate_id("ma_run")
        try:
            return await protocol.run(task, self._agents, run_id=run_id)
        except Exception as e:
            return ProtocolResult(success=False, error=str(e))
