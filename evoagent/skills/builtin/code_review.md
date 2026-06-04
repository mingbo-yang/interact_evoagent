---
name: code_review
description: Systematic code review checklist for quality and safety.
triggers:
  - code review
  - review
  - check quality
  - audit
---

# Code Review Checklist

## Coupling

- Are functions small and single-purpose?
- Is there unnecessary coupling between modules?
- Can this change be isolated to fewer files?

## Edge Cases

- What happens with empty input?
- What happens with None/null?
- What happens with very large inputs?
- Are there off-by-one errors?

## Error Handling

- Are exceptions caught and handled appropriately?
- Are error messages clear and actionable?
- Is there a fallback for partial failures?

## Test Coverage

- Does the change have corresponding tests?
- Do tests cover the happy path AND edge cases?
- Are there integration tests if multiple modules are affected?

## Security

- Is user input validated?
- Are file paths sanitized (no path traversal)?
- Are secrets ever logged or exposed?
