# AgentGauge

**Evaluation & regression harness for LLM agents.** Score agent outputs with rule-based, numeric-tolerance, schema, and semantic checks; track quality across runs; catch regressions before they ship.

Built from lessons learned shipping governed agentic AI in production at enterprise scale.

## Why

Agents fail quietly. A prompt tweak that fixes one workflow silently breaks three others. AgentGauge treats agent quality like software quality: **versioned test cases, deterministic scoring, and diffable run reports.**

```
 cases.jsonl ──▶ Runner ──▶ Scorers ──▶ RunResult ──▶ Report (HTML/JSON)
                   │                        │
                   ▼                        ▼
              your agent fn           Regression diff vs. baseline run
```

## Install

```bash
pip install -e .
```

## Quickstart

```python
from agentgauge import Case, Runner, ExactMatch, NumericTolerance, Contains

def my_agent(prompt: str) -> str:
    ...  # call your agent / chain / MCP client here

cases = [
    Case(id="refund-policy", input="What is the refund window?",
         checks=[Contains("30 days")]),
    Case(id="revenue-q3", input="Total Q3 revenue?",
         checks=[NumericTolerance(expected=1_240_000, rel_tol=0.01)]),
]

run = Runner(agent=my_agent).run(cases, run_id="prompt-v2")
print(run.summary())          # pass rate, per-check breakdown
run.save("runs/prompt-v2.json")
```

Compare against a baseline and fail CI on regressions:

```bash
agentgauge diff runs/prompt-v1.json runs/prompt-v2.json --fail-on-regression
agentgauge report runs/prompt-v2.json -o report.html
```

## Scorers

| Scorer | Use case |
|---|---|
| `ExactMatch` | canonical answers |
| `Contains` / `Regex` | key-fact presence, format checks |
| `NumericTolerance` | analytics answers — normalizes `$1.2M`, `1,200,000`, `1.2e6` before comparing |
| `JSONSchemaCheck` | structured/tool-call outputs |
| `SemanticSimilarity` | paraphrase-tolerant checks (pluggable embedder) |
| `LLMJudge` | rubric-based grading via any LLM callable |

All scorers return a `CheckResult(passed, score, detail)` — mix deterministic and model-graded checks per case.

## Regression tracking

`agentgauge diff` compares two runs case-by-case and reports: newly failing (regressions), newly passing (fixes), and score deltas. Exit code is non-zero when regressions exist, so it drops straight into CI.

## Design notes

- **No framework lock-in** — the agent is just a callable. LangGraph, MCP client, raw API loop: all fine.
- **Deterministic first** — semantic/LLM checks are opt-in; core scoring is reproducible.
- **Auditable** — every run serializes inputs, outputs, scores, and timings to JSON.

## Roadmap

- Longitudinal dashboard across runs
- Multi-turn / trajectory scoring (tool-call sequence checks)
- Built-in adapters for MCP servers

## License

MIT
