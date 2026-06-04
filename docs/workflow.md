# Workflow Graph

## Design Goals

The Workflow Graph is a lightweight, LangGraph-inspired execution engine that:
- Models agent execution as a directed graph of nodes
- Supports conditional routing
- Provides checkpoint/resume for long-running tasks
- Enables human-in-the-loop via interrupt

## Components

### WorkflowNode
- `name`: unique identifier
- `handler`: async function `(RuntimeState, context) -> RuntimeState`
- `metadata`: optional extra data

### WorkflowEdge
- `source` → `target`
- `condition`: optional `(RuntimeState) -> bool` for conditional routing

### WorkflowGraph
- `add_node()` / `add_edge()`
- `set_entrypoint()` / `set_finish()`
- `get_next_node(current, state)` — evaluates conditions
- `validate()` — checks entrypoint, edge source/target, finish nodes

## RuntimeState Flow

The same `RuntimeState` object is passed through all nodes:
- Node handlers read from and mutate the state
- State accumulates messages, step_results, tool_results, errors
- `state.status` controls flow (RUNNING, WAITING_FOR_HUMAN, SUCCEEDED, FAILED)

## Checkpoint & Resume

- `WorkflowRuntime` uses `CheckpointManager` to save after each node
- `runtime.resume(run_id, checkpoint_id)` loads the latest state
- Checkpoints are named by node: `chk_xxx_node_plan`

## Human Interrupt

- `InterruptRequest` with reason, action, options
- Node sets `state.status = WAITING_FOR_HUMAN`
- Runtime pauses, preserves state
- After human input, resume from checkpoint

## Built-in Nodes

`make_builtin_nodes()` provides lightweight placeholders:
- `load_context`, `retrieve_memory`, `plan`, `execute_step`, `critic`, `memory_write`, `finish`

These can be replaced with full Planner/Executor/Critic implementations.

## vs AgentLoop

| Feature | AgentLoop | WorkflowGraph |
|---------|-----------|---------------|
| Structure | Linear Plan → Execute → Critic | DAG with conditions |
| Routing | Fixed sequence | Dynamic based on state |
| Resume | Not supported | Full checkpoint/resume |
| Human loop | Not supported | WAITING_FOR_HUMAN status |
| Use case | Single task | Complex multi-step pipelines |
