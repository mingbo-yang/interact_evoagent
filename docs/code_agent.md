# Code Agent

## Goal

EvoAgent's Code Agent is a specialized agent for software engineering tasks: understanding codebases, locating bugs, editing files, running tests, and iterating until tests pass.

## Components

### RepoMap
Scans a repository and extracts structure:
- File paths, languages, line counts, sizes
- Python class/function symbols via `ast`
- Skips `.git`, `__pycache__`, `.venv`, `node_modules`, `dist`, `build`

### CodeSearch
- `search_text(pattern)` — grep for patterns
- `search_symbol(symbol)` — find Python definitions
- `find_files(glob)` — locate files by pattern
- `summarize_file(path)` — preview + metadata

### PatchManager
- `edit_file(path, old, new)` — text replacement with backup
- `write_file(path, content)` — create/overwrite with backup
- `get_diff()` — git diff or fallback
- `rollback_last()` — undo last edit

### TestRunner
- Runs test command (default: `python -m pytest -q`)
- Captures stdout, stderr, exit_code, duration
- Supports timeout

### Diagnostics
- `parse_failure(output)` — extracts failed test names and assertions
- `extract_error_summary(output)` — last error block
- `identify_likely_files(output)` — file paths from tracebacks

## CodeAgent Loop

```
Scan repo → Locate files → Plan patch → Edit → Run tests
                                              ↓ (fail)
                              Analyze failure ↗ (fix & retry)
                                              ↓ (pass)
                                         Output summary + diff
```

- `max_iterations` default: 5
- Rule-based fallback for zero-division and common patterns
- Full LLM-powered path reserved for future Phase

## Configuration

```yaml
# In evoagent.yaml
code_agent:
  test_command: "python -m pytest -q"
  max_iterations: 5
```

## Avoiding Dangerous Modifications

- PatchManager backs up every file before editing
- `rollback_last()` available for immediate undo
- CodeAgent never deletes files
- Test files are never modified to falsely pass

## Gap to SWE-agent / OpenHands

| Feature | EvoAgent CodeAgent | SWE-agent / OpenHands |
|---------|-------------------|----------------------|
| LLM-powered patch | Planned | Full |
| Docker sandbox | Planned (Phase 5 stub) | Built-in |
| Multi-file refactor | Limited | Full |
| Test generation | Planned | Partial |
| Benchmark integration | Planned | SWE-bench |
