# Skill System

## Goal

EvoAgent's Skill System provides reusable, prompt-injectable skills that guide Agent behavior for specific tasks.

## Skill File Format

Markdown files with optional YAML front matter:

```markdown
---
name: debugging_python
description: How to debug Python pytest failures
triggers:
  - pytest failed
  - traceback
  - assertion error
---

# Debugging Steps
1. Read traceback
2. Locate failing test
...
```

Files without front matter are loaded with the filename as the skill name.

## Components

### SkillLoader
- `load_file(path)` — load a single .md/.yaml skill
- `load_dir(path)` — load all skills from a directory

### SkillRegistry
- `register(skill)` — add/overwrite a skill
- `get(name)` — lookup by name
- `search_by_trigger(query)` — find skills matching keywords

### SkillRetriever
- `retrieve(task, context, error)` — find relevant skills
- `format_for_prompt(skills)` — format for LLM prompt injection
- Scoring: trigger match > name/description match > usage stats

### SkillUsageTracker
- Tracks each skill usage (success/failure)
- Persists to `skills_usage.json`

### SkillEvolution
- Rule-based priority adjustment
- High success rate → higher priority
- Low success rate → lower priority

## Integration with Agent

Skills are injected into `AgentContext.skills` and formatted into the system prompt before task execution.

## Avoiding Skill Pollution

- Skills with high failure rates are deprioritized
- Low-quality skills can be manually removed from the registry
- Built-in skills are carefully curated
