---
name: memory_reflection
description: Extract and consolidate memories from task traces.
triggers:
  - memory
  - reflection
  - learn
  - consolidate
  - experience
---

# Memory Reflection

## Process

1. **Review the trace** — read the events.jsonl or RuntimeState.
2. **Identify patterns** — what succeeded? What failed?
3. **Extract episodic memory** — record the task, outcome, and key steps.
4. **Extract reflection memory** — for failures, record root cause and fix strategy.
5. **Deduplicate** — merge memories with similar content.
6. **Update importance** — successful patterns get higher importance.

## Rules

- Don't memorize one-off errors as general rules.
- Filter low-quality memories (single-step failures with no context).
- Tag memories with source_run_id for traceability.
- Update confidence based on repetition.
