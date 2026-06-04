"""evoagent eval — run evaluation benchmarks."""

import asyncio

import typer

from evoagent.cli.main import app
from evoagent.cli.utils import console


@app.command("eval")
def eval_suite(
    suite: str = typer.Option("examples/eval_toy_tasks.jsonl", "--suite", help="Path to JSONL task file."),
    output: str = typer.Option("eval_report.md", "--output", help="Output report path."),
    mock: bool = typer.Option(False, "--mock", help="Use mock agent."),
):
    """Run an evaluation benchmark suite."""
    from pathlib import Path

    from evoagent.core.agent import Agent
    from evoagent.eval.datasets import DatasetLoader
    from evoagent.eval.harness import EvalHarness
    from evoagent.eval.report import EvalReport
    from evoagent.models.factory import MockLLMProvider
    from evoagent.models.router import ModelRouter
    from evoagent.tools.builtin import create_builtin_registry

    c = console()
    suite_path = Path(suite)
    if not suite_path.exists():
        c.print(f"[red]Suite not found: {suite}[/red]")
        raise typer.Exit(1)

    tasks = DatasetLoader.load_jsonl(suite_path)
    c.print(f"Loaded {len(tasks)} tasks")

    workspace = Path.cwd()
    if mock:
        mock_llm = MockLLMProvider(fixed_text='{"risk_level":"low","steps":[{"goal":"Execute task","action_type":"tool","tool_name":"list_directory","arguments":{"path":"."}},{"goal":"Finish","action_type":"finish"}]}')
        router = ModelRouter(providers={"planner": mock_llm, "default": mock_llm})
        agent = Agent(model_router=router, tool_registry=create_builtin_registry(workspace))
    else:
        from evoagent.cli.utils import create_agent
        agent = create_agent(mock=False)

    async def _run():
        harness = EvalHarness(agent)
        results = await harness.run_suite(tasks)
        for r in results:
            icon = "✅" if r.success else "❌"
            c.print(f"  {icon} {r.task_id} ({r.duration_ms}ms)")
        report_path = EvalReport.save_report(results, output)
        c.print(f"\nReport saved to {report_path}")

    asyncio.run(_run())
