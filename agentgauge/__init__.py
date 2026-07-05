"""AgentGauge: evaluation & regression harness for LLM agents."""

from .dataset import Case, load_cases
from .scorers import (
    CheckResult,
    Contains,
    ExactMatch,
    JSONSchemaCheck,
    LLMJudge,
    NumericTolerance,
    Regex,
    Scorer,
    SemanticSimilarity,
)
from .runner import Runner, RunResult
from .regression import diff_runs

__version__ = "0.1.0"

__all__ = [
    "Case", "load_cases",
    "Scorer", "CheckResult", "ExactMatch", "Contains", "Regex",
    "NumericTolerance", "JSONSchemaCheck", "SemanticSimilarity", "LLMJudge",
    "Runner", "RunResult", "diff_runs",
]
