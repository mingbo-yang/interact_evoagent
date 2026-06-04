# Planning System

## Overview

EvoAgent's planning system implements a structured Plan → Execute → Critic → Revise loop, which is more robust than simple ReAct.

## Components

### Planner
- **Input**: task, available tools, context (memories/docs)
- **Output**: `Plan` with ordered `PlanStep`s
- **How**: Calls LLM (planner role) with a system prompt that requests JSON output
- **Fallback**: If JSON parsing fails, attempts repair; then falls back to a minimal plan

### Executor
- **Input**: `RuntimeState`, `PlanStep`, `ToolRegistry`, LLM
- **Output**: `StepResult`
- **Dispatch** based on `action_type`:
  - `tool` → `ToolRegistry.run_tool()`
  - `llm` → LLM reasoning call
  - `code` → Python execution tool
  - `ask_user` → sets `WAITING_FOR_HUMAN` status
  - `finish` → marks task complete

### Critic
- **Input**: task, step, result
- **Output**: `CriticDecision` (passed, needs_revision, needs_more_info, reason, confidence)
- **Modes**:
  - `rule` (default): simple success/failure check
  - `llm`: uses LLM to evaluate result quality

### Reflector
- **Input**: failed step, critic feedback, current plan
- **Output**: revised `Plan` or None
- **Safety**: limits reflections to `max_reflections` (default 3) to prevent infinite loops

## Agent Loop Flow

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
         │   │         │      │
         │   │    Revised Plan│
         │   └────┬────┘      │
         │        ↓           │
         └── Next Step ───────┘
                    ↓
                 Finish
                    ↓
              AgentResult
```

## Plan JSON Format

```json
{
  "risk_level": "low",
  "steps": [
    {
      "goal": "List the current directory",
      "action_type": "tool",
      "tool_name": "list_directory",
      "arguments": {"path": "."},
      "expected_result": "A list of files and directories"
    },
    {
      "goal": "Finish the task",
      "action_type": "finish"
    }
  ]
}
```

## Step action_type Reference

| action_type | Description | Required fields |
|------------|-------------|----------------|
| `tool` | Invoke a registered tool | `tool_name`, `arguments` |
| `llm` | LLM reasoning step | (none) |
| `code` | Execute Python code | `arguments.code` |
| `ask_user` | Request human input | (none) |
| `finish` | End the plan | (none) |

## Avoiding Infinite Loops

1. `max_steps` limits total steps per run
2. `max_reflections` limits plan revisions
3. Executor catches tool errors
4. Critic detects repeated failures
5. Reflector skips failed steps when no alternative exists

## Testing with MockLLMProvider

All tests use `MockLLMProvider` to avoid real API calls:

```python
from evoagent.models.factory import MockLLMProvider
from evoagent.models.router import ModelRouter

mock = MockLLMProvider(fixed_text='{"risk_level":"low","steps":[...]}')
router = ModelRouter(providers={"planner": mock})
```

## Custom Planner

Implement the same interface:

```python
class MyPlanner:
    async def plan(self, task, tools_schema, context="") -> Plan:
        ...
```

Then pass to `AgentLoop` or `Agent`.
