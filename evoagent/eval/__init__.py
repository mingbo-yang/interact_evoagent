"""Evaluation harness — benchmarks, tasks, metrics.

Provides:
- EvalTask / EvalResult: task and result schemas
- DatasetLoader: JSONL task loading
- Checkers: exact/contains/regex/test_command
- Metrics: aggregate statistics
- EvalHarness: run tasks against agents
- EvalReport: markdown/JSON reports
- Regression: detect regressions between runs
"""

from evoagent.eval.checkers import (  # noqa: F401
    ContainsChecker,
    ExactMatchChecker,
    RegexChecker,
    TestCommandChecker,
    evaluate_check,
)
from evoagent.eval.datasets import DatasetLoader  # noqa: F401
from evoagent.eval.harness import EvalHarness  # noqa: F401
from evoagent.eval.metrics import Metrics  # noqa: F401
from evoagent.eval.regression import Regression  # noqa: F401
from evoagent.eval.report import EvalReport  # noqa: F401
from evoagent.eval.task import EvalResult, EvalTask  # noqa: F401
