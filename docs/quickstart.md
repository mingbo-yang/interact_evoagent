# Quick Start

## Install

```bash
cd agent
pip install -e ".[dev]"
```

## Set API Key

```bash
export DEEPSEEK_API_KEY="sk-your-key-here"
```

## Initialize

```bash
evoagent init
```

Creates `evoagent.yaml`, `.evoagent/`, `.runs/`.

## Run a Task

```bash
evoagent run "List all Python files in this project"

# Without API key? Use --mock
evoagent run "Hello world" --mock
```

## Code Agent

```bash
evoagent code "Fix the division-by-zero bug in calculator.py"
```

## Interactive Chat

```bash
evoagent chat
```

## Run Evaluation

```bash
evoagent eval --suite examples/eval_toy_tasks.jsonl --mock
```

## View Traces

```bash
evoagent trace list
evoagent trace show <run_id>
```

## Python API

```python
from evoagent.core.agent import Agent
from evoagent.tools.builtin import create_builtin_registry
from evoagent.models.router import ModelRouter
from evoagent.models.factory import MockLLMProvider

# Setup
tools = create_builtin_registry(".")
mock = MockLLMProvider(fixed_text="OK")
router = ModelRouter(providers={"default": mock})
agent = Agent(model_router=router, tool_registry=tools)

# Run
result = await agent.run("List files")
print(result.final_answer)
```

## Common Errors

| Error | Solution |
|-------|----------|
| `ModelProviderError: API key not found` | Set `DEEPSEEK_API_KEY` environment variable |
| `Config file not found` | Run `evoagent init` first |
| `No provider registered for role` | Check `evoagent.yaml` models section |
