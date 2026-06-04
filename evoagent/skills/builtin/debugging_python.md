---
name: debugging_python
description: How to debug Python pytest failures systematically.
triggers:
  - pytest failed
  - traceback
  - assertion error
  - test failure
  - debug
---

# Debugging Python Test Failures

## Steps

1. **Read the full traceback** — copy the error output into context.
2. **Locate the failing test** — find the test function name from the FAILED line.
3. **Locate the function under test** — identify which production code the test exercises.
4. **Make minimal changes** — change only what's necessary to fix the failure.
5. **Run the single test first** — `pytest path/to/test.py::test_name -x`
6. **Then run all tests** — `pytest -q` to verify no regressions.

## Rules

- Never modify the test to make it pass if the test is correct.
- If the test expectation is wrong, comment your reasoning before changing it.
- Add error handling (try/except, guard clauses) only where needed.
- Prefer fixing the root cause over adding workarounds.
