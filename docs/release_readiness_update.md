# EvoAgent Release Readiness Update — v0.3.0

## Current Version
v0.3.0 (pyproject.toml, README, CHANGELOG consistent)

## Test Results
```
376 passed in 19.87s
compileall: ✅
ruff check: ✅ All checks passed
```

## Fixed Issues (v0.3.0 release readiness pass)

| # | Issue | Resolution |
|---|-------|-----------|
| P1 | Repository sanity check | All files valid Python; compileall/pytest/ruff pass |
| P2 | Version inconsistency | pyproject.toml updated from 0.1.0 → 0.3.0; placeholder URLs replaced with mingbo-yang/EvoAgent; benchmark claims marked illustrative |
| P3 | DockerSandbox image duplicated | Fixed _docker_exec() — image now appears once, options before image in correct docker CLI order; added command construction tests |
| P4 | Memory not injected into AgentContext | Agent.run() now retrieves memories, stores in _memory_context, and passes to AgentLoop → Planner via context parameter; added memory injection test |
| P5 | CodeAgent LLM patch validation | Added tests: MockLLM PatchPlan applies, old_text missing rejected, path outside workspace rejected, max_iterations enforced, rule-based ZeroDivisionError fallback |
| P6 | Planner fallback safety | Added tests: invalid JSON raises PlanningError, fallback plan excludes arbitrary bash, Reflector handles unknown_tool/file_not_found/permission_denied, max_reflections enforced |
| P7 | Benchmark claims | Marked all benchmark numbers as "illustrative" not measured; kept benchmark JSONL files loadable |

## Files Modified
- pyproject.toml (version)
- README.md (URLs, benchmark wording)
- README_zh.md (URLs)
- docs/release_readiness_v0.3.0.md (benchmark labels)
- evoagent/sandbox/docker.py (docker command construction)
- evoagent/core/agent.py (memory injection)
- evoagent/planning/loop.py (context passthrough)

## Files Added
- tests/test_code_agent_llm_patch.py (5 tests)
- tests/test_planner_fallback.py (5 tests)

## Remaining Known Limitations
- Hybrid retrieval uses mock embedding (hash-based), not real models
- DockerSandbox requires Docker installed; CI skips docker tests
- CodeAgent LLM patch is experimental (MockLLM tested, real LLM not verified)
- Benchmark numbers are illustrative only (not from measured runs)
- Production hardening not done

## Safety Status
- PermissionPolicy deny rules enforced everywhere
- Test command checker requires sandbox
- API keys from environment only
- No real keys in repository

## Repository Readiness
✅ Ready for public GitHub release as research MVP.

## Implementation vs Design Match
The implementation covers all major modules from the original EvoAgent design:
Core Schema, ModelProvider, Tool System, Sandbox/Permissions, EventLogger,
Planner-Executor-Critic-Reflector, 5-layer Memory, RAG, Multi-Agent,
Workflow Graph, Code Agent, Skill System, Eval Harness, CLI.

Gaps: real embedding models, FAISS/Qdrant, SWE-bench integration, streaming.
