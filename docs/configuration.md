# Configuration

EvoAgent uses `evoagent.yaml` for configuration with environment variable overrides.

## File Location

- Default: `evoagent.yaml` in current directory
- Create with: `evoagent init`
- View with: `evoagent config show`

## Full Reference

### project

```yaml
project:
  name: evoagent        # Project name
  version: "0.1.0"      # Version
  work_dir: .           # Working directory
```

### models

```yaml
models:
  default:              # Fallback for all roles
    provider: deepseek  # deepseek | openai_compatible | mock
    model: deepseek-chat
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
    temperature: 0.0
    max_tokens: 4096
    max_retries: 3
    timeout: 60
  planner:              # Planning model (default: deepseek-reasoner)
    ...
  executor:             # Execution model (default: deepseek-chat)
    ...
  critic:               # Critique model (default: deepseek-reasoner)
    ...
  summarizer:           # Summarization model
    ...
```

### runtime

```yaml
runtime:
  max_turns: 20               # Max steps per AgentLoop
  max_llm_calls: 50           # Max LLM calls per run
  max_tool_calls: 100         # Max tool calls per run
  max_context_tokens: 128000  # Max context window
  checkpoint_enabled: true    # Enable checkpointing
  checkpoint_dir: .evoagent/checkpoints
```

### permissions

```yaml
permissions:
  mode: auto                  # review | auto | yolo
  deny:                       # Always-blocked patterns
    - action: shell
      pattern: "rm -rf*"
  ask:                        # Require confirmation
    - action: shell
      pattern: "*install*"
  allow:                      # Always allowed
    - action: file_read
      pattern: "*"
```

### sandbox

```yaml
sandbox:
  type: local                 # local | docker (future)
  timeout: 60
  workspace: "."
```

### memory

```yaml
memory:
  enabled: true
  store: sqlite               # sqlite (only option for now)
  path: .evoagent/memory.sqlite
  top_k: 5                    # Default retrieval count
  write_after_run: true
  consolidation: true
```

### rag

```yaml
rag:
  enabled: false
  paths: []                   # Document directories to index
  chunk_size: 1000
  chunk_overlap: 100
  top_k: 5
  retriever: keyword
```

### skills

```yaml
skills:
  enabled: true
  paths:
    - "evoagent/skills/builtin"
  top_k: 3
  usage_path: ".evoagent/skills_usage.json"
```

### logging

```yaml
logging:
  enabled: true
  traces_dir: .runs
  save_checkpoints: true
  save_diffs: true
  log_dir: .evoagent/logs
  log_format: jsonl
```

### eval

```yaml
eval:
  benchmark_dir: benchmarks/
  output_dir: .evoagent/eval_results
```

## Environment Variable Overrides

All values can be overridden via `EVOAGENT_<section>__<key>`:

```bash
export EVOAGENT_MODELS__PLANNER__MODEL="deepseek-chat"
export EVOAGENT_PERMISSIONS__MODE="review"
```
