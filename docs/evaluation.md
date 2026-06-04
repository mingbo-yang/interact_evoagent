# Evaluation Harness

## Why Eval Harness?

Agent behavior is non-deterministic. An evaluation harness provides:
- Reproducible benchmarks
- Standardized success criteria
- Regression detection
- Metrics for research papers

## EvalTask JSONL Format

One JSON object per line:

```json
{"task_id": "text_contains", "instruction": "Say hello", "expected_check": "{\"type\": \"contains\", \"value\": \"hello\"}"}
```

Fields:
- `task_id`: unique identifier
- `instruction`: task description
- `task_type`: text, tool, code, memory, rag
- `expected_check`: checker JSON specification
- `expected_output`: simpler substring check
- `test_command`: shell command to run
- `input_files`: files to create before the task

## Checker Types

| Type | Spec | Description |
|------|------|-------------|
| `contains` | `{"type":"contains","value":"hello"}` | Output contains substring |
| `exact` | `{"type":"exact","value":"OK"}` | Output exactly matches |
| `regex` | `{"type":"regex","value":"1[0-9]{2}"}` | Output matches regex |
| `test_command` | `{"type":"test_command","command":"pytest -q"}` | Shell command exits 0 |

## Metrics

- `success_rate`: fraction of tasks passed
- `average_score`: mean score across all tasks
- `avg_duration_ms`: average execution time
- `avg_steps`: average plan steps per task
- `avg_tool_calls`: average tool calls per task
- `avg_llm_calls`: average LLM calls per task
- `memory_hit_rate`: fraction of memory retrievals used (if trace available)
- `recovery_success_rate`: fraction of failed steps recovered (if trace available)

## Regression Testing

```python
from evoagent.eval.regression import Regression

reg = Regression.compare(old_results, new_results)
if reg["regression_detected"]:
    for w in reg["warnings"]:
        print(f"⚠️ {w}")
```

## Running Toy Benchmark

```bash
python examples/eval_toy.py
```
