"""Team — pre-configured group of agents with shared resources."""

from dataclasses import dataclass, field

from evoagent.multi_agent.base import RoleAgent
from evoagent.multi_agent.manager import MultiAgentManager
from evoagent.multi_agent.protocols import BaseProtocol, ProtocolResult


@dataclass
class Team:
    """A pre-configured team of agents.

    Usage:
        team = Team(name="dev_team", agents=[coder, tester, critic], protocol=PipelineProtocol(...))
        result = await team.run("Fix the bug")
    """

    name: str = ""
    agents: list[RoleAgent] = field(default_factory=list)
    protocol: BaseProtocol | None = None
    shared_tools: list | None = None
    shared_memory: object | None = None

    async def run(self, task: str) -> ProtocolResult:
        """Run the team on a task."""
        manager = MultiAgentManager()
        for agent in self.agents:
            manager.register(agent.name, agent)
        if not self.protocol:
            from evoagent.multi_agent.protocols import PipelineProtocol
            self.protocol = PipelineProtocol(order=[a.name for a in self.agents])
        return await manager.run(task, self.protocol)
