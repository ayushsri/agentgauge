"""Test-case dataset: definition and JSONL ingestion."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from .scorers import Scorer, scorer_from_spec


@dataclass
class Case:
    """A single evaluation case.

    Attributes:
        id: stable identifier (used for regression diffing across runs).
        input: prompt / task handed to the agent.
        checks: list of Scorer instances applied to the agent output.
        metadata: free-form tags (suite, owner, severity, ...).
    """

    id: str
    input: str
    checks: List[Scorer] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def load_cases(path: str | Path) -> List[Case]:
    """Load cases from a JSONL file.

    Each line:
        {"id": "...", "input": "...",
         "checks": [{"type": "contains", "value": "30 days"},
                    {"type": "numeric", "expected": 42, "rel_tol": 0.01}],
         "metadata": {...}}
    """
    cases: List[Case] = []
    seen: set[str] = set()
    for line_no, raw in enumerate(Path(path).read_text().splitlines(), 1):
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        obj: dict[str, Any] = json.loads(raw)
        cid: Optional[str] = obj.get("id")
        if not cid:
            raise ValueError(f"{path}:{line_no}: case missing 'id'")
        if cid in seen:
            raise ValueError(f"{path}:{line_no}: duplicate case id {cid!r}")
        seen.add(cid)
        checks = [scorer_from_spec(spec) for spec in obj.get("checks", [])]
        cases.append(Case(id=cid, input=obj["input"], checks=checks,
                          metadata=obj.get("metadata", {})))
    return cases
