"""Multi-agent collaboration protocols: Pipeline, Debate, Supervisor."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from evoagent.multi_agent.base import RoleAgent
from evoagent.multi_agent.messages import MultiAgentMessage


@dataclass
class ProtocolResult:
    """Result from a multi-agent protocol execution."""

    success: bool = False
    final_answer: str = ""
    messages: list[MultiAgentMessage] = field(default_factory=list)
    agent_outputs: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseProtocol(ABC):
    """Abstract protocol for multi-agent collaboration."""

    @abstractmethod
    async def run(self, task: str, agents: dict[str, RoleAgent], run_id: str = "") -> ProtocolResult:
        ...


class PipelineProtocol(BaseProtocol):
    """Sequential pipeline: each agent processes the previous agent's output.

    Flow: Agent1 → Agent2 → Agent3 → ... → final result.
    """

    def __init__(self, max_rounds: int = 1, order: list[str] | None = None):
        self.max_rounds = max_rounds
        self.order = order or []

    async def run(self, task: str, agents: dict[str, RoleAgent], run_id: str = "") -> ProtocolResult:
        agent_names = self.order or list(agents.keys())
        msgs: list[MultiAgentMessage] = []
        outputs: dict[str, str] = {}
        current = task

        for name in agent_names:
            agent = agents.get(name)
            if not agent:
                continue
            try:
                result = await agent.act(current, run_id=run_id)
            except Exception as e:
                return ProtocolResult(success=False, error=f"Agent '{name}' failed: {e}",
                                      messages=msgs, agent_outputs=outputs)

            msg = MultiAgentMessage(
                sender="user" if name == agent_names[0] else agent_names[agent_names.index(name) - 1] if agent_names.index(name) > 0 else "user",
                receiver=name, content=result, role=agent.role,
            )
            msgs.append(msg)
            outputs[name] = result
            current = result

        final = outputs.get(agent_names[-1], "") if agent_names else ""
        return ProtocolResult(success=True, final_answer=final, messages=msgs, agent_outputs=outputs)


class DebateProtocol(BaseProtocol):
    """Debate: multiple agents propose solutions, a judge picks the best.

    Flow: Agents propose → Judge/Critic selects best → final answer.
    """

    def __init__(self, judge_name: str = "Critic", max_turns: int = 2):
        self.judge_name = judge_name
        self.max_turns = max_turns

    async def run(self, task: str, agents: dict[str, RoleAgent], run_id: str = "") -> ProtocolResult:
        msgs: list[MultiAgentMessage] = []
        outputs: dict[str, str] = {}

        # Each agent proposes
        debaters = {k: v for k, v in agents.items() if k != self.judge_name}
        for name, agent in debaters.items():
            try:
                result = await agent.act(f"Propose a solution for: {task}", run_id=run_id)
            except Exception as e:
                return ProtocolResult(success=False, error=f"Agent '{name}' failed: {e}")
            outputs[name] = result
            msgs.append(MultiAgentMessage(sender=name, receiver=self.judge_name, content=result, role=agent.role))

        # Judge selects best
        judge = agents.get(self.judge_name)
        if judge:
            proposals = "\n\n".join(f"=== {name} ===\n{out}" for name, out in outputs.items())
            judge_prompt = f"Task: {task}\n\nProposals:\n{proposals}\n\nSelect the best solution and explain why."
            try:
                final = await judge.act(judge_prompt, run_id=run_id)
            except Exception as e:
                return ProtocolResult(success=False, error=f"Judge failed: {e}")
            outputs[self.judge_name] = final
            msgs.append(MultiAgentMessage(sender=self.judge_name, receiver="all", content=final, role=judge.role))

        final = outputs.get(self.judge_name, list(outputs.values())[-1] if outputs else "")
        return ProtocolResult(success=True, final_answer=final, messages=msgs, agent_outputs=outputs)


class SupervisorProtocol(BaseProtocol):
    """Supervisor: manager decomposes tasks, assigns to workers, collects results.

    Flow: Manager decomposes → Workers execute → Manager synthesizes.
    """

    def __init__(self, manager_name: str = "Manager", max_turns: int = 5):
        self.manager_name = manager_name
        self.max_turns = max_turns

    async def run(self, task: str, agents: dict[str, RoleAgent], run_id: str = "") -> ProtocolResult:
        msgs: list[MultiAgentMessage] = []
        outputs: dict[str, str] = {}

        manager = agents.get(self.manager_name)
        if not manager:
            return ProtocolResult(success=False, error=f"Manager '{self.manager_name}' not found.")

        workers = {k: v for k, v in agents.items() if k != self.manager_name}

        # Manager decomposes
        try:
            plan = await manager.act(f"Decompose this task and assign to workers: {task}\nWorkers: {list(workers.keys())}", run_id=run_id)
        except Exception as e:
            return ProtocolResult(success=False, error=f"Manager planning failed: {e}")
        msgs.append(MultiAgentMessage(sender=self.manager_name, receiver="all", content=plan, role="manager"))

        # Workers execute
        for name, agent in workers.items():
            worker_task = f"Manager's plan:\n{plan}\n\nYour task: Contribute to '{task}' as {name}."
            try:
                result = await agent.act(worker_task, run_id=run_id)
            except Exception as e:
                outputs[name] = f"Error: {e}"
                continue
            outputs[name] = result
            msgs.append(MultiAgentMessage(sender=name, receiver=self.manager_name, content=result, role=agent.role))

        # Manager synthesizes
        worker_results = "\n\n".join(f"=== {name} ===\n{out}" for name, out in outputs.items())
        try:
            final = await manager.act(f"Synthesize worker results for task '{task}':\n{worker_results}", run_id=run_id)
        except Exception as e:
            return ProtocolResult(success=False, error=f"Manager synthesis failed: {e}")
        outputs[self.manager_name] = final

        return ProtocolResult(success=True, final_answer=final, messages=msgs, agent_outputs=outputs)
