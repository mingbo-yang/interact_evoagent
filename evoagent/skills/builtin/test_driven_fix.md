---
name: test_driven_fix
description: Fix bugs by understanding failing tests first.
triggers:
  - fix bug
  - test driven
  - failing test
  - regression
---

# Test-Driven Bug Fix

## Process

1. **Understand the failing test** — read the test code and expected behavior.
2. **Don't modify the test** unless it's clearly wrong (document why).
3. **Write a minimal fix** — the smallest change that makes the test pass.
4. **Run the specific test** — verify it passes in isolation.
5. **Run the full suite** — check for regressions.
6. **If other tests break** — analyze whether your fix exposed a pre-existing issue.

## Anti-patterns

- Don't add `if` checks that mask the real bug.
- Don't change the test assertion to match broken behavior.
- Don't refactor unrelated code.
- Don't add unnecessary abstractions.
