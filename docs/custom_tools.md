# Custom Tools

## Quick Example

```python
from pydantic import BaseModel, Field
from evoagent.tools.base import BaseTool, RiskLevel
from evoagent.tools.schema import ToolResult

class MyToolInput(BaseModel):
    query: str = Field(..., description="Search query.")

class MySearchTool(BaseTool):
    name = "my_search"
    description = "Search a custom knowledge base."
    input_schema = MyToolInput
    risk_level = RiskLevel.LOW

    async def run(self, query: str) -> ToolResult:
        # Your logic here
        results = f"Found results for: {query}"
        return ToolResult(
            call_id="...", name=self.name, success=True,
            output=results,
        )
```

## Registering

```python
from evoagent.tools.registry import ToolRegistry

registry = ToolRegistry(workspace=".")
registry.register(MySearchTool())

# Use with Agent
agent = Agent(tool_registry=registry, ...)
```

## Requirements

1. **Extend `BaseTool`** — set `name`, `description`, `input_schema`, `risk_level`
2. **Define input_schema** — Pydantic BaseModel with Field descriptions
3. **Implement `async run()`** — return a `ToolResult`
4. **Risk level** — `LOW` (safe reads), `MEDIUM` (file writes), `HIGH` (shell/python)

## Workspace Safety

Use `resolve_workspace_path()` for file operations:

```python
from evoagent.tools.base import resolve_workspace_path

resolved = resolve_workspace_path(path_str, workspace)
```

## OpenAI Tool Schema

`BaseTool.to_openai_tool_schema()` auto-generates the OpenAI function-calling schema from your `input_schema`.
