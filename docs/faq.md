# FAQ

## No API key — how do I test?

Use `--mock` on any CLI command:

```bash
evoagent run "hello" --mock
evoagent chat --mock
evoagent eval --suite examples/eval_toy_tasks.jsonl --mock
```

Or use `MockLLMProvider` in Python:

```python
from evoagent.models.factory import MockLLMProvider
mock = MockLLMProvider(fixed_text="OK")
```

## How to prevent dangerous commands?

Set `permissions.mode` to `review` in `evoagent.yaml`. The default `auto` mode allows low-risk and asks for medium/high. `rm -rf`, `sudo`, `shutdown`, `mkfs`, and `curl|bash` are always blocked.

## How to view traces?

```bash
evoagent trace list
evoagent trace show <run_id>
evoagent trace events <run_id> --type error
```

Or read the JSONL directly: `cat .runs/<run_id>/events.jsonl | jq .`

## How to disable memory?

Set `memory.enabled: false` in `evoagent.yaml`.

## How to use mock mode?

All CLI commands accept `--mock`. In Python, use `MockLLMProvider` and pass to `ModelRouter`.

## How to configure DeepSeek?

```bash
export DEEPSEEK_API_KEY="sk-your-key"
```

Or set `api_key_env` in `evoagent.yaml` models section.

## How to run tests?

```bash
pytest                          # All 343 tests
pytest tests/test_tools.py       # Specific module
pytest -x                        # Stop on first failure
```

## How to add a new tool?

See [docs/custom_tools.md](custom_tools.md).

## How to use another LLM?

See [docs/custom_models.md](custom_models.md).

## Where are memories stored?

By default: `.evoagent/memory.sqlite` (SQLite database).
