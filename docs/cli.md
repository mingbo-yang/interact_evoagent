# CLI Reference

## Installation

```bash
pip install -e ".[dev]"
```

## API Key Setup

```bash
export DEEPSEEK_API_KEY="sk-your-key-here"
```

## Commands

### `evoagent init`

Initialize EvoAgent in the current directory:

```bash
evoagent init           # Creates evoagent.yaml, .evoagent/, .runs/
evoagent init --force   # Overwrite existing files
```

### `evoagent config show`

```bash
evoagent config show
```

### `evoagent run`

```bash
evoagent run "List all Python files in this project"
evoagent run "What's in the README?" --mock
evoagent run "Fix the bug in calculator.py" --max-steps 10
```

### `evoagent chat`

```bash
evoagent chat
evoagent chat --mock
```

### `evoagent code`

```bash
evoagent code "Fix the division by zero in calc.py"
evoagent code --mock
```

### `evoagent eval`

```bash
evoagent eval --suite examples/eval_toy_tasks.jsonl --mock
evoagent eval --suite my_tasks.jsonl --output report.md
```

### `evoagent memory`

```bash
evoagent memory list
evoagent memory list --type episodic --limit 10
evoagent memory search "python script"
```

### `evoagent trace`

```bash
evoagent trace list
evoagent trace show <run_id>
evoagent trace events <run_id> --type tool_call_finished
```

## Mock Mode

All commands support `--mock` flag for testing without an API key.
Mock mode uses `MockLLMProvider` with fixed responses.
