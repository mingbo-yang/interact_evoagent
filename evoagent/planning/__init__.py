"""Planner, Executor, Critic, and Reflector.

Provides the complete agent reasoning loop:
- Planner: task → Plan
- Executor: PlanStep → StepResult
- Critic: evaluate step success
- Reflector: revise failed plans
- AgentLoop: orchestrate Plan → Execute → Critic → Revise

Import sub-modules lazily to avoid circular imports with core.
"""
