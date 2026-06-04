"""Workflow agent example — graph-based execution with built-in nodes."""

import asyncio
import tempfile
from pathlib import Path

from evoagent.core.state import RuntimeState
from evoagent.logging.checkpoint import CheckpointManager
from evoagent.workflow.builtin_nodes import make_builtin_nodes
from evoagent.workflow.edge import WorkflowEdge
from evoagent.workflow.graph import WorkflowGraph
from evoagent.workflow.runtime import WorkflowRuntime


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        # Build graph: load_context -> plan -> execute_step -> critic -> memory_write -> finish
        nodes = make_builtin_nodes()
        graph = WorkflowGraph()
        graph.add_node(nodes["load_context"])
        graph.add_node(nodes["plan"])
        graph.add_node(nodes["execute_step"])
        graph.add_node(nodes["critic"])
        graph.add_node(nodes["memory_write"])
        graph.add_node(nodes["finish"])

        graph.add_edge(WorkflowEdge(source="load_context", target="plan"))
        graph.add_edge(WorkflowEdge(source="plan", target="execute_step"))
        graph.add_edge(WorkflowEdge(source="execute_step", target="critic"))
        graph.add_edge(WorkflowEdge(source="critic", target="memory_write"))
        graph.add_edge(WorkflowEdge(source="memory_write", target="finish"))

        graph.set_entrypoint("load_context")
        graph.set_finish("finish")

        # Setup runtime with checkpoint
        chk_mgr = CheckpointManager(Path(tmp) / "checkpoints")
        runtime = WorkflowRuntime(graph, checkpoint_manager=chk_mgr, save_checkpoints=True)

        # Run
        state = RuntimeState(run_id="wf_demo", task="Build a simple web app")
        result = await runtime.run(state, context={"system_prompt": "You build web apps."})

        print(f"Status: {result.status}")
        print(f"Metadata: {dict(result.metadata)}")
        print(f"Errors: {result.errors}")

        # List checkpoints
        chks = chk_mgr.list_checkpoints("wf_demo")
        print(f"Checkpoints: {len(chks)}")


if __name__ == "__main__":
    asyncio.run(main())
