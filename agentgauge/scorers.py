"""Scorers: deterministic and model-graded checks over agent outputs.

Every scorer implements `score(output: str) -> CheckResult`. Deterministic
scorers (exact/contains/regex/numeric/schema) are dependency-light and
reproducible; semantic and LLM-judge scorers accept user-supplied callables
so the harness stays provider-agnostic.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence


@dataclass
class CheckResult:
    name: str
    passed: bool
    score: float  # 0.0 - 1.0
    detail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed,
                "score": round(self.score, 4), "detail": self.detail}


class Scorer:
    """Base class. Subclasses set `name` and implement `score()`."""

    name = "scorer"

    def score(self, output: str) -> CheckResult:  # pragma: no cover
        raise NotImplementedError


class ExactMatch(Scorer):
    name = "exact_match"

    def __init__(self, expected: str, case_sensitive: bool = False,
                 strip: bool = True):
        self.expected, self.case_sensitive, self.strip = expected, case_sensitive, strip

    def score(self, output: str) -> CheckResult:
        got, want = output, self.expected
        if self.strip:
            got, want = got.strip(), want.strip()
        if not self.case_sensitive:
            got, want = got.lower(), want.lower()
        ok = got == want
        return CheckResult(self.name, ok, 1.0 if ok else 0.0,
                           "" if ok else f"expected {self.expected!r}")


class Contains(Scorer):
    name = "contains"

    def __init__(self, value: str, case_sensitive: bool = False):
        self.value, self.case_sensitive = value, case_sensitive

    def score(self, output: str) -> CheckResult:
        hay = output if self.case_sensitive else output.lower()
        needle = self.value if self.case_sensitive else self.value.lower()
        ok = needle in hay
        return CheckResult(self.name, ok, 1.0 if ok else 0.0,
                           "" if ok else f"missing {self.value!r}")


class Regex(Scorer):
    name = "regex"

    def __init__(self, pattern: str, flags: int = re.IGNORECASE):
        self.pattern = re.compile(pattern, flags)

    def score(self, output: str) -> CheckResult:
        ok = bool(self.pattern.search(output))
        return CheckResult(self.name, ok, 1.0 if ok else 0.0,
                           "" if ok else f"no match for /{self.pattern.pattern}/")


_NUM_RE = re.compile(r"-?\$?\s*\d[\d,]*\.?\d*\s*[kKmMbB]?")
_SUFFIX = {"k": 1e3, "m": 1e6, "b": 1e9}


def normalize_numbers(text: str) -> list[float]:
    """Extract numbers from text, normalizing $, commas, and k/M/B suffixes.

    '$1.2M' -> 1200000.0 ; '1,240,000' -> 1240000.0 ; '3.5k' -> 3500.0
    """
    values: list[float] = []
    for token in _NUM_RE.findall(text):
        t = token.replace("$", "").replace(",", "").strip()
        mult = 1.0
        if t and t[-1].lower() in _SUFFIX:
            mult, t = _SUFFIX[t[-1].lower()], t[:-1].strip()
        try:
            values.append(float(t) * mult)
        except ValueError:
            continue
    return values


class NumericTolerance(Scorer):
    """Pass if any number in the output is within tolerance of `expected`."""

    name = "numeric_tolerance"

    def __init__(self, expected: float, rel_tol: float = 0.0,
                 abs_tol: float = 0.0):
        self.expected, self.rel_tol, self.abs_tol = expected, rel_tol, abs_tol

    def score(self, output: str) -> CheckResult:
        candidates = normalize_numbers(output)
        for value in candidates:
            if math.isclose(value, self.expected,
                            rel_tol=self.rel_tol, abs_tol=self.abs_tol):
                return CheckResult(self.name, True, 1.0)
        return CheckResult(self.name, False, 0.0,
                           f"expected ~{self.expected}, found {candidates[:5]}")


class JSONSchemaCheck(Scorer):
    """Validate that the output parses as JSON matching a schema."""

    name = "json_schema"

    def __init__(self, schema: dict):
        self.schema = schema

    def score(self, output: str) -> CheckResult:
        import jsonschema
        try:
            payload = json.loads(_extract_json(output))
        except (json.JSONDecodeError, ValueError) as exc:
            return CheckResult(self.name, False, 0.0, f"invalid JSON: {exc}")
        try:
            jsonschema.validate(payload, self.schema)
        except jsonschema.ValidationError as exc:
            return CheckResult(self.name, False, 0.0, exc.message)
        return CheckResult(self.name, True, 1.0)


def _extract_json(text: str) -> str:
    """Pull the first JSON object/array out of possibly-fenced output."""
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    start = min((i for i in (text.find("{"), text.find("[")) if i != -1),
                default=-1)
    if start == -1:
        raise ValueError("no JSON found in output")
    return text[start:]


class SemanticSimilarity(Scorer):
    """Cosine similarity against a reference, via a user-supplied embedder.

    embedder: Callable[[Sequence[str]], Sequence[Sequence[float]]]
    """

    name = "semantic_similarity"

    def __init__(self, reference: str,
                 embedder: Callable[[Sequence[str]], Any],
                 threshold: float = 0.8):
        self.reference, self.embedder, self.threshold = reference, embedder, threshold

    def score(self, output: str) -> CheckResult:
        a, b = self.embedder([output, self.reference])
        dot = sum(x * y for x, y in zip(a, b))
        norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
        sim = dot / norm if norm else 0.0
        return CheckResult(self.name, sim >= self.threshold, max(0.0, min(1.0, sim)),
                           f"cosine={sim:.3f} (threshold {self.threshold})")


class LLMJudge(Scorer):
    """Rubric-based grading via any LLM callable.

    judge: Callable[[str], str] — receives the grading prompt, returns the
    model's raw text. The response must contain 'PASS' or 'FAIL'.
    """

    name = "llm_judge"

    PROMPT = (
        "You are grading an AI agent's answer.\n\nRubric:\n{rubric}\n\n"
        "Agent answer:\n{output}\n\n"
        "Reply with PASS or FAIL on the first line, then one sentence of reasoning."
    )

    def __init__(self, rubric: str, judge: Callable[[str], str]):
        self.rubric, self.judge = rubric, judge

    def score(self, output: str) -> CheckResult:
        reply = self.judge(self.PROMPT.format(rubric=self.rubric, output=output))
        verdict = reply.strip().splitlines()[0].upper() if reply.strip() else ""
        ok = "PASS" in verdict and "FAIL" not in verdict
        return CheckResult(self.name, ok, 1.0 if ok else 0.0, reply.strip()[:300])


_SPEC_MAP = {
    "exact": lambda s: ExactMatch(s["value"], s.get("case_sensitive", False)),
    "contains": lambda s: Contains(s["value"], s.get("case_sensitive", False)),
    "regex": lambda s: Regex(s["pattern"]),
    "numeric": lambda s: NumericTolerance(s["expected"], s.get("rel_tol", 0.0),
                                          s.get("abs_tol", 0.0)),
    "json_schema": lambda s: JSONSchemaCheck(s["schema"]),
}


def scorer_from_spec(spec: dict) -> Scorer:
    """Build a deterministic scorer from a JSONL check spec."""
    kind = spec.get("type")
    if kind not in _SPEC_MAP:
        raise ValueError(
            f"unknown check type {kind!r} (declarative specs support: "
            f"{sorted(_SPEC_MAP)}; semantic/llm_judge are code-only)")
    return _SPEC_MAP[kind](spec)
