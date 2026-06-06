# v0.5.0 Deep Audit — Findings & Fixes

Systematic engineering audit of EvoAgent. Method: 5 parallel module reviews plus
real-API verification against DeepSeek (env var only; never written to source,
logs, or sessions). All 31 findings below were fixed and verified.

## Verification baseline (after fixes)
- `python -m compileall evoagent`: clean
- `ruff check .`: clean
- `pytest -q`: 452 passed (437 baseline + 15 new regression tests in
  tests/test_audit_regressions.py and updated planner/sandbox tests)
- Real-API end-to-end (DeepSeek): interactive multi-tool turn works; Agent.run +
  eval harness measured 2/3 on a 3-task code-fix sample (was 0/5, could not edit
  any file before); cost/token tracking now non-zero.

## Why these were not caught before
Almost all tests use MockLLMProvider, so bugs in real provider wire-format,
the planning loop, tool argument schemas, subprocess encoding, and permission
enforcement were invisible. The audit added real-API and real-execution checks.

## Critical
1. conversation/runtime.py `_safe_messages` — parallel tool_calls dropped the
   2nd+ tool response, producing an invalid sequence DeepSeek/OpenAI reject
   (HTTP 400). Rewrote to keep one tool message per tool_call_id and drop
   truncated/orphan groups. (regression tests added)
2. planning/planner.py — the planner sent the LLM only tool *names*, not
   parameter schemas, so the model guessed argument names (`file_path` vs the
   real `path`) and every tool call failed input validation; Agent.run could
   not act. Now formats each tool with its parameter schema.
3. planning/loop.py `_build_final_answer` — always returned the FINISH step's
   constant "Task finished.", shadowing the real answer, so eval always scored
   0. Now skips the FINISH placeholder.

## High
4. planning/loop.py — reflection-revised plan was never executed (for-loop kept
   iterating the stale list). Switched to an index loop that re-reads the plan.
5. workflow/builtin_nodes.py — nodes were no-op stubs; a workflow run
   "succeeded" doing nothing. Now delegate to Planner/Executor/Critic/Memory
   from the node context (graceful fallback when absent).
6. memory/consolidation.py — KeyError on clustered/transitive duplicates.
   Track deleted ids and skip.
7. models/openai_compatible.py — retry was dead code (`except httpx.HTTPError`
   caught transient errors before tenacity). Re-raise transient errors.
8. conversation/runtime.py (stream) — record_turn stored the assistant reply as
   the user message (reused `text`). Use a separate variable.
9. subprocess decoding — `text=True` without `encoding=` crashes/loses output
   on non-UTF-8 locales. Added `encoding="utf-8", errors="replace"` across
   shell/python/git/test/code/sandbox modules.
10. code/patch.py — PatchManager could write outside the workspace (arbitrary
    file write). Routed through resolve_workspace_path containment.
11. permission ASK — executors only blocked DENY, so ASK ran silently. Made
    sandbox/bash fail-closed on ASK with an `auto_approve` opt-in for trusted
    callers (eval harness; interactive CLI which gates approval via the runtime).

## Medium
12. reflector counter keyed by plan.id (new id each revision) -> keyed by task.
13. planner `_repair_json` raised instead of using `_fallback_plan` -> falls back.
14. workflow resume() could not resume (no current-node persisted) -> persists a
    resume marker; run() can start from it.
15. workflow false "Max steps" error on boundary finish; dead-end left status
    RUNNING -> only errors on real limit; dead-end -> FAILED.
16. rag/chunker.py infinite loop when chunk_size==0 -> validates size>=1.
17. retrieval/embeddings.py only 8 of 64 dims had signal -> fills all 64.
18. rag/index.py + retrieval/keyword.py ASCII-only tokenizer dropped CJK ->
    Unicode-aware + per-character CJK tokens.
19. reasoning_content echoed back in request payload -> dropped (display only).
20. streaming path never streamed (dead `if step==1 or True`) -> removed.
21. models/factory.py mis-dispatched anthropic/gemini to the OpenAI adapter ->
    fail clearly (safe degradation) until native adapters exist.
22. bash/python/test output never truncated -> capped.
23. core/types.py circular import (core <-> eval) -> lazy re-exports.
24. cost tracking never wired (total_cost/tokens always 0) -> CostSnapshot
    shared across planner/executor/loop and fed from response usage.
25. eval/harness.py ran test_command in the harness workspace, not the task
    workspace -> runs in the task workspace.

## Low
26. stream_chat dropped tool_calls in SSE deltas -> documented text-only.
27. ListDir truncation message showed max_entries as the total -> real total.
28. Grep truncation note was unreachable -> uses a truncated flag.
29. interactive.py EOF (Ctrl-D) infinite loop in the Rich input branch -> breaks.
30. code/agent.py rule-based zerodiv fix produced invalid code for a malformed
    pattern -> removed that pattern.
31. core/cost.py missing deepseek-v4 pricing (tokens tracked, cost 0) -> added.

## Deferred (explicit, per safe-degradation decision)
- Native Anthropic/Gemini adapters: not implemented; selecting them now raises a
  clear error rather than silently 400ing.
- Real token-level streaming with tool-call assembly: the streaming entrypoint
  returns correct buffered output; true incremental streaming is not implemented.
- Agent.run uses a static plan-ahead strategy; it is inherently weaker than the
  interactive iterative tool-calling path for tasks needing to read before edit.