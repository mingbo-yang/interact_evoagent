# Architecture

## Overview

EvoAgent is a **model-agnostic, tool-agnostic, state-driven, observable, resumable** agent framework.

```
User Task
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Runtime                            │
│                                                                 │
│  Context → Planner → Executor → Critic → Reflector              │
│     │                              │                            │
│     ▼                              ▼                            │
│  Memory ◄────────────────────── Event Logger (JSONL)            │
│     │                              │                            │
│     ▼                              ▼                            │
│  RAG (docs)                   Trace / Checkpoint                │
└─────────────────────────────────────────────────────────────────┘
        │              │                │
        ▼              ▼                ▼
  ModelProvider   ToolRegistry    PermissionPolicy
  (DeepSeek/      (file/shell/    (review/auto/yolo)
   OpenAI/Mock)    python/git/...)
```

## Module Boundaries

| Module | Responsibility | Depends On |
|--------|---------------|------------|
| `core` | Types, Agent, RuntimeState, AgentLoop | (foundation) |
| `models` | LLM abstraction (ModelProvider/ModelRouter) | core |
| `tools` | ToolRegistry, built-in tools | core, sandbox |
| `sandbox` | PermissionPolicy, LocalSandbox | core, tools |
| `logging` | JSONL EventLogger, TraceRecorder, Checkpoint | core |
| `planning` | Planner, Executor, Critic, Reflector | models, tools, logging |
| `memory` | SQLiteMemoryStore, Retriever, Writer, Evolution | core, logging |
| `rag` | Document loading, chunking, keyword retrieval | core |
| `multi_agent` | RoleAgent, Pipeline/Debate/Supervisor protocols | models, tools, logging |
| `workflow` | WorkflowGraph, Runtime, Checkpoint, Interrupt | core, logging |
| `code` | CodeAgent (RepoMap, Search, Patch, TestRunner) | tools, sandbox |
| `skills` | SkillLoader, Registry, Retriever, Evolution | core |
| `eval` | EvalHarness, Metrics, Checkers, Regression | core, code |
| `cli` | CLI commands (init/run/chat/code/eval/...) | all above |

## Agent Loop

```
Task → Planner → Plan
                  ↓
       ┌── Execute Step ──┐
       │        ↓          │
       │    Critic         │
       │   ┌────┴────┐     │
       │  passed    failed  │
       │   │         │      │
       │   ↓         ↓      │
       │ Continue   Reflect │
       └────────────────────┘
                  ↓
               Finish
                  ↓
            AgentResult
```

All steps logged via EventLogger → JSONL trace.

## Model Routing

```
Agent
  │
  ▼
ModelRouter
  ├── planner   → deepseek-reasoner
  ├── executor  → deepseek-chat
  ├── critic    → deepseek-reasoner
  └── default   → deepseek-chat
```

Each role maps to a ModelConfig (provider, model, base_url, api_key_env).

## Tool Calling

```
LLM generates tool_calls
  → Executor dispatches via ToolRegistry
    → Tool validates args via Pydantic input_schema
      → PermissionPolicy.check(action_type, risk_level)
        → Sandbox.run_shell / run_python / read_file / write_file
          → ToolResult (success, output, error, artifacts, duration)
            → Event logged
```

## Memory Flow

```
Before run:  MemoryRetriever.retrieve(task) → format → inject into context
During run:  WorkingMemory (short-term, ephemeral)
After run:   MemoryWriter.write_from_run(state)
             ├── EpisodicMemory (success/failure)
             └── ReflectionMemory (if failed)
Periodic:    MemoryConsolidator.merge_duplicates()
             MemoryEvolution.evolve_memories()
```

## Event Log / Trace

```
.runs/<run_id>/
  events.jsonl    ← every action as JSON line
  state.json      ← RuntimeState snapshot
  final_result.json ← AgentResult
  metadata.json   ← run metadata
  patches/        ← file diffs
  artifacts/      ← produced files
```
