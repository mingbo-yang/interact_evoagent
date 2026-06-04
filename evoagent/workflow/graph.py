"""WorkflowGraph — a directed graph of nodes and edges."""

from evoagent.core.errors import EvoAgentError
from evoagent.core.state import RuntimeState
from evoagent.workflow.edge import WorkflowEdge
from evoagent.workflow.node import WorkflowNode


class WorkflowGraph:
    """A directed graph defining agent workflow.

    Supports:
    - Named nodes with async handlers
    - Edges with optional conditions (conditional routing)
    - Entrypoint and finish markers
    - Validation

    Usage:
        graph = WorkflowGraph()
        graph.add_node(WorkflowNode(name="start", handler=start_handler))
        graph.add_node(WorkflowNode(name="end", handler=end_handler))
        graph.add_edge(WorkflowEdge(source="start", target="end"))
        graph.set_entrypoint("start")
        graph.set_finish("end")
        graph.validate()
    """

    def __init__(self):
        self._nodes: dict[str, WorkflowNode] = {}
        self._edges: list[WorkflowEdge] = []
        self._entrypoint: str | None = None
        self._finish_nodes: set[str] = set()

    def add_node(self, node: WorkflowNode) -> None:
        self._nodes[node.name] = node

    def add_edge(self, edge: WorkflowEdge) -> None:
        self._edges.append(edge)

    def set_entrypoint(self, name: str) -> None:
        self._entrypoint = name

    def set_finish(self, name: str) -> None:
        self._finish_nodes.add(name)

    def get_node(self, name: str) -> WorkflowNode:
        if name not in self._nodes:
            raise EvoAgentError(f"Node '{name}' not found in graph.")
        return self._nodes[name]

    def get_next_node(self, current: str, state: RuntimeState) -> str | None:
        """Find the next node by evaluating edges from current.

        Returns:
            Target node name, or None if no matching edge.
        """
        candidates = [e for e in self._edges if e.source == current]
        for edge in candidates:
            if edge.evaluate(state):
                return edge.target
        return None

    def is_finish(self, node_name: str) -> bool:
        return node_name in self._finish_nodes

    def validate(self) -> None:
        """Validate the graph structure.

        Raises:
            EvoAgentError: If the graph is invalid.
        """
        if not self._entrypoint:
            raise EvoAgentError("Graph has no entrypoint. Call set_entrypoint().")
        if self._entrypoint not in self._nodes:
            raise EvoAgentError(f"Entrypoint '{self._entrypoint}' is not a registered node.")
        if not self._finish_nodes:
            raise EvoAgentError("Graph has no finish nodes. Call set_finish().")
        for edge in self._edges:
            if edge.source not in self._nodes:
                raise EvoAgentError(f"Edge source '{edge.source}' is not a registered node.")
            if edge.target not in self._nodes:
                raise EvoAgentError(f"Edge target '{edge.target}' is not a registered node.")

    @property
    def entrypoint(self) -> str | None:
        return self._entrypoint

    @property
    def nodes(self) -> dict[str, WorkflowNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[WorkflowEdge]:
        return list(self._edges)
