# Changelog

## v0.3.0 (current)
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
