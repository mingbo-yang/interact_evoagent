# Changelog

## v0.5.0
- Deep engineering audit: fixed 31 verified bugs across planning, tools, sandbox,
  memory, RAG/retrieval, workflow, models, and CLI (see reports/v0.5.0/audit-findings.md).
- Planner now passes tool parameter schemas to the model so Agent.run can
  actually execute tools (previously all tool calls failed validation).
- Real-provider tool-call message history fixed (parallel tool_calls HTTP 400);
  loop final-answer no longer shadowed by the FINISH placeholder.
- Security: PatchManager workspace containment; ASK permission tier is now
  fail-closed at the execution boundary.
- Reliability: subprocess UTF-8 decoding; retry now actually retries transient
  errors; cost/token tracking wired; eval test_command runs in the task workspace.
- 15 new regression tests; full suite 452 passing; ruff and compileall clean.

## v0.3.0
- Benchmark suites: tool_use (20), toy_code (20), memory (10 pairs), RAG (10)
- Enhanced EvalReport: CSV export, comparison mode
- MkDocs documentation website
- GitHub release readiness: LICENSE, CONTRIBUTING, SECURITY, PR/issue templates
- DockerSandbox with test coverage

## v0.2.0
- Semantic/hybrid retrieval (keyword + vector + hybrid)
- DockerSandbox implementation (docker CLI)
- LLM-powered CodeAgent patch loop (PatchPlan + FileEdit)
- Enhanced Diagnostics (structured error parsing)
- Expanded rule-based code fixes (5+ patterns)
- Extension: evoagent/retrieval/ module

## v0.1.1
- Unified BashTool PermissionPolicy (removed hardcoded keywords)
- RuleMatcher with exact/glob/regex + token-aware shell matching
- EvalHarness TestCommandChecker through Sandbox
- JSONLEventLogger limit/offset/reverse/iter_events
- RuntimeState.plan type restored (Plan | None)
- Pydantic V3 ConfigDict migration
- TestRunner → CodeTestRunner rename
- Configurable evolution thresholds
- Reflector intelligent rule-based recovery
- GrepTool pure Python (no system grep dependency)
- Config loader via importlib.resources

## v0.1.0
- Initial release: core framework with 343 tests
- ModelProvider (DeepSeek/OpenAI-compatible/Mock)
- Tool system (9 built-in tools)
- Sandbox & PermissionPolicy
- EventLogger & TraceRecorder
- Agent Loop (Planner→Executor→Critic→Reflector)
- 5-layer memory system
- RAG pipeline
- Multi-agent collaboration
- Workflow graph engine
- Code agent
- Skill system
- Evaluation harness
- CLI
