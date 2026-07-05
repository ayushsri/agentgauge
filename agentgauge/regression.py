"""Diff two runs case-by-case to surface regressions and fixes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .runner import RunResult


@dataclass
class Diff:
    baseline_id: str
    candidate_id: str
    regressions: List[str] = field(default_factory=list)  # pass -> fail
    fixes: List[str] = field(default_factory=list)        # fail -> pass
    still_failing: List[str] = field(default_factory=list)
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)

    @property
    def has_regressions(self) -> bool:
        return bool(self.regressions)

    def summary(self) -> str:
        lines = [f"{self.baseline_id} -> {self.candidate_id}"]
        for label, ids in (("REGRESSED", self.regressions),
                           ("fixed", self.fixes),
                           ("still failing", self.still_failing),
                           ("added", self.added),
                           ("removed", self.removed)):
            if ids:
                lines.append(f"  {label}: {', '.join(ids)}")
        if not self.regressions:
            lines.append("  no regressions")
        return "\n".join(lines)


def diff_runs(baseline: RunResult, candidate: RunResult) -> Diff:
    base = {r.case_id: r.passed for r in baseline.results}
    cand = {r.case_id: r.passed for r in candidate.results}
    diff = Diff(baseline.run_id, candidate.run_id)
    for cid, passed in cand.items():
        if cid not in base:
            diff.added.append(cid)
        elif base[cid] and not passed:
            diff.regressions.append(cid)
        elif not base[cid] and passed:
            diff.fixes.append(cid)
        elif not passed:
            diff.still_failing.append(cid)
    diff.removed = [cid for cid in base if cid not in cand]
    return diff
