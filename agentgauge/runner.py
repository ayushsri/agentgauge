"""Runner: execute an agent callable over a dataset and collect results."""

from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from .dataset import Case
from .scorers import CheckResult


@dataclass
class CaseResult:
    case_id: str
    output: str
    checks: List[CheckResult]
    latency_ms: float
    error: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.error is None and all(c.passed for c in self.checks)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "output": self.output,
            "checks": [c.to_dict() for c in self.checks],
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
        }


@dataclass
class RunResult:
    run_id: str
    results: List[CaseResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)

    @property
    def pass_rate(self) -> float:
        return (sum(r.passed for r in self.results) / len(self.results)
                if self.results else 0.0)

    def summary(self) -> str:
        n = len(self.results)
        passed = sum(r.passed for r in self.results)
        failed = [r.case_id for r in self.results if not r.passed]
        lines = [f"run {self.run_id}: {passed}/{n} passed "
                 f"({self.pass_rate:.0%})"]
        if failed:
            lines.append("failed: " + ", ".join(failed))
        return "\n".join(lines)

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2))

    def to_dict(self) -> dict:
        return {"run_id": self.run_id, "started_at": self.started_at,
                "pass_rate": round(self.pass_rate, 4),
                "results": [r.to_dict() for r in self.results]}

    @classmethod
    def load(cls, path: str | Path) -> "RunResult":
        obj = json.loads(Path(path).read_text())
        run = cls(run_id=obj["run_id"], started_at=obj.get("started_at", 0.0))
        for r in obj["results"]:
            run.results.append(CaseResult(
                case_id=r["case_id"], output=r.get("output", ""),
                checks=[CheckResult(**c) for c in r.get("checks", [])],
                latency_ms=r.get("latency_ms", 0.0), error=r.get("error")))
        return run


class Runner:
    """Runs `agent(input) -> output` over cases, applying each case's checks.

    Agent exceptions are captured per-case (a crashing case fails; the run
    continues), mirroring how test frameworks isolate failures.
    """

    def __init__(self, agent: Callable[[str], str]):
        self.agent = agent

    def run(self, cases: List[Case], run_id: str = "run") -> RunResult:
        run = RunResult(run_id=run_id)
        for case in cases:
            t0 = time.perf_counter()
            try:
                output = self.agent(case.input)
                error = None
            except Exception:
                output, error = "", traceback.format_exc(limit=3)
            latency = (time.perf_counter() - t0) * 1000
            checks = ([c.score(output) for c in case.checks]
                      if error is None else [])
            run.results.append(CaseResult(case.id, output, checks,
                                          latency, error))
        return run
