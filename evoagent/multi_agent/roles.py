"""Built-in role agents with default system prompts."""

from evoagent.multi_agent.base import RoleAgent, RoleAgentConfig

PLANNER_PROMPT = """You are a Planner agent. Your job is to analyze tasks and create clear step-by-step plans.
Output structured plans with numbered steps. Be concise."""

CODER_PROMPT = """You are a Coder agent. Your job is to write, review, and suggest code changes.
Provide specific code snippets. Use the available tools for file operations."""

TESTER_PROMPT = """You are a Tester agent. Your job is to design tests and verify behavior.
Suggest test cases, edge cases, and validation steps. Think about what could go wrong."""

CRITIC_PROMPT = """You are a Critic agent. Your job is to review outputs and identify issues.
Be constructive — point out problems AND suggest improvements. Rate confidence."""

RESEARCHER_PROMPT = """You are a Researcher agent. Your job is to find and synthesize information.
Search documentation, recall relevant memories, and provide factual answers."""

MEMORY_PROMPT = """You are a Memory agent. Your job is to manage the agent's memory system.
Decide what to remember, what to forget, and how to prioritize information."""

MANAGER_PROMPT = """You are a Manager agent. Your job is to coordinate other agents.
Decompose tasks, assign to the right agent, collect results, and synthesize final output.
Available agents: planner, coder, tester, critic, researcher."""


def create_planner(model_router=None, trace_recorder=None) -> RoleAgent:
    return RoleAgent(
        RoleAgentConfig(name="Planner", role="planner", system_prompt=PLANNER_PROMPT, model_role="planner"),
        model_router=model_router, trace_recorder=trace_recorder,
    )


def create_coder(model_router=None, tool_registry=None, trace_recorder=None) -> RoleAgent:
    return RoleAgent(
        RoleAgentConfig(name="Coder", role="coder", system_prompt=CODER_PROMPT, model_role="executor"),
        model_router=model_router, tool_registry=tool_registry, trace_recorder=trace_recorder,
    )


def create_tester(model_router=None, trace_recorder=None) -> RoleAgent:
    return RoleAgent(
        RoleAgentConfig(name="Tester", role="tester", system_prompt=TESTER_PROMPT, model_role="executor"),
        model_router=model_router, trace_recorder=trace_recorder,
    )


def create_critic(model_router=None, trace_recorder=None) -> RoleAgent:
    return RoleAgent(
        RoleAgentConfig(name="Critic", role="critic", system_prompt=CRITIC_PROMPT, model_role="critic"),
        model_router=model_router, trace_recorder=trace_recorder,
    )


def create_researcher(model_router=None, trace_recorder=None) -> RoleAgent:
    return RoleAgent(
        RoleAgentConfig(name="Researcher", role="researcher", system_prompt=RESEARCHER_PROMPT, model_role="executor"),
        model_router=model_router, trace_recorder=trace_recorder,
    )


def create_memory_agent(model_router=None, memory_store=None, trace_recorder=None) -> RoleAgent:
    return RoleAgent(
        RoleAgentConfig(name="Memory", role="memory", system_prompt=MEMORY_PROMPT, model_role="default"),
        model_router=model_router, memory_store=memory_store, trace_recorder=trace_recorder,
    )


def create_manager(model_router=None, trace_recorder=None) -> RoleAgent:
    return RoleAgent(
        RoleAgentConfig(name="Manager", role="manager", system_prompt=MANAGER_PROMPT, model_role="planner"),
        model_router=model_router, trace_recorder=trace_recorder,
    )
