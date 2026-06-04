# Multi-Agent System

## Why Multi-Agent?

Single-agent systems struggle with:
- Complex tasks requiring diverse expertise
- Verification and quality assurance
- Creative problem-solving from multiple angles

Multi-agent collaboration enables:
- **Specialization**: each agent has a focused role (planning, coding, testing)
- **Verification**: critic agents catch errors before they reach the user
- **Debate**: multiple perspectives lead to better solutions

## RoleAgent

Each `RoleAgent` has:
- `name`, `role` — identity
- `system_prompt` — defines behavior
- `model_role` — which model to use (planner/executor/critic)
- `tool_registry` — optional tools
- `memory_store` — optional memory
- `trace_recorder` — shared event logging

All LLM calls go through `ModelRouter`, never directly to a provider.

## Protocols

### Pipeline
Sequential execution: Agent1 → Agent2 → Agent3 → final result.
Best for: linear workflows (plan → code → test → review).

### Debate
Parallel proposals + judge selection.
Best for: creative problem-solving, architecture decisions.

### Supervisor
Manager decomposes → workers execute → manager synthesizes.
Best for: complex tasks with multiple sub-tasks.

## Shared Resources

- **run_id**: all agents in a protocol share the same run_id
- **trace_recorder**: optional shared event logger
- **memory_store**: optional shared memory
- **tool_registry**: agents can share or have separate tool registries

## Avoiding Empty Loops

- `max_turns` / `max_rounds` limits on all protocols
- Agent failures are caught and reported
- Manager validates worker outputs before synthesis

## Custom Roles

```python
from evoagent.multi_agent.base import RoleAgent, RoleAgentConfig

config = RoleAgentConfig(
    name="SecurityAuditor",
    role="auditor",
    system_prompt="You audit code for security vulnerabilities.",
    model_role="critic",
)
auditor = RoleAgent(config, model_router=router)
```
