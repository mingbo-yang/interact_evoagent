"""Eval toy example — load JSONL, run against mock agent, generate report."""

import asyncio
from pathlib import Path

from evoagent.eval.datasets import DatasetLoader
from evoagent.eval.harness import EvalHarness
from evoagent.eval.report import EvalReport


class MockAgent:
    """Simplest possible agent for eval testing — returns fixed text."""
    async def run(self, task: str):
        from evoagent.core.result import AgentResult
        return AgentResult(run_id="mock", task=task, success=True, final_answer="hello world (from mock)")

    async def chat(self, msg: str) -> str:
        return "hello world"


TOY_TASKS = Path(__file__).parent / "eval_toy_tasks.jsonl"


async def main():
    tasks = DatasetLoader.load_jsonl(TOY_TASKS)
    print(f"Loaded {len(tasks)} tasks")

    agent = MockAgent()
    harness = EvalHarness(agent)

    results = await harness.run_suite(tasks)
    for r in results:
        print(f"  {r.task_id}: {'PASS' if r.success else 'FAIL'} ({r.duration_ms}ms)")

    report = EvalReport.to_markdown(results)
    print(f"\n{report}")


if __name__ == "__main__":
    asyncio.run(main())
