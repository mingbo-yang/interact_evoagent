"""Multi-agent collaboration — supervisor, debate, pipeline.

Provides:
- RoleAgent: role-specific agent with LLM, tools, memory
- RoleAgentConfig: configuration for role agents
- MultiAgentMessage: inter-agent messaging
- PipelineProtocol / DebateProtocol / SupervisorProtocol
- MultiAgentManager: register and run protocols
- Team: pre-configured agent teams
- Built-in roles: Planner, Coder, Tester, Critic, Researcher, Memory, Manager
"""

from evoagent.multi_agent.base import RoleAgent, RoleAgentConfig  # noqa: F401
from evoagent.multi_agent.manager import MultiAgentManager  # noqa: F401
from evoagent.multi_agent.messages import MultiAgentMessage  # noqa: F401
from evoagent.multi_agent.protocols import (  # noqa: F401
    DebateProtocol,
    PipelineProtocol,
    ProtocolResult,
    SupervisorProtocol,
)
from evoagent.multi_agent.roles import (  # noqa: F401
    create_coder,
    create_critic,
    create_manager,
    create_memory_agent,
    create_planner,
    create_researcher,
    create_tester,
)
from evoagent.multi_agent.team import Team  # noqa: F401
