"""Self-contained HTML report for a run."""

from __future__ import annotations

import html
from pathlib import Path

from .runner import RunResult

_CSS = """
body{font-family:-apple-system,Segoe UI,sans-serif;margin:2rem auto;max-width:960px;color:#1f2328}
h1{font-size:1.4rem} .rate{font-size:2.2rem;font-weight:700}
table{border-collapse:collapse;width:100%;margin-top:1rem}
td,th{border:1px solid #d0d7de;padding:.5rem .7rem;text-align:left;font-size:.9rem;vertical-align:top}
th{background:#f6f8fa} .pass{color:#1a7f37;font-weight:600} .fail{color:#cf222e;font-weight:600}
.detail{color:#57606a;font-size:.8rem} pre{white-space:pre-wrap;margin:0;max-height:8rem;overflow:auto}
"""


def render_html(run: RunResult) -> str:
    rows = []
    for r in run.results:
        status = '<span class="pass">PASS</span>' if r.passed else '<span class="fail">FAIL</span>'
        checks = "<br>".join(
            f'{"✓" if c.passed else "✗"} {html.escape(c.name)}'
            + (f' <span class="detail">{html.escape(c.detail)}</span>' if c.detail else "")
            for c in r.checks) or "—"
        err = (f'<div class="detail">{html.escape(r.error)}</div>' if r.error else "")
        rows.append(
            f"<tr><td>{html.escape(r.case_id)}</td><td>{status}{err}</td>"
            f"<td><pre>{html.escape(r.output[:800])}</pre></td>"
            f"<td>{checks}</td><td>{r.latency_ms:.0f} ms</td></tr>")
    return f"""<!doctype html><meta charset="utf-8">
<title>AgentGauge — {html.escape(run.run_id)}</title><style>{_CSS}</style>
<h1>AgentGauge report — {html.escape(run.run_id)}</h1>
<div class="rate">{run.pass_rate:.0%} <span style="font-size:1rem;font-weight:400">
({sum(r.passed for r in run.results)}/{len(run.results)} cases)</span></div>
<table><tr><th>Case</th><th>Status</th><th>Output</th><th>Checks</th><th>Latency</th></tr>
{''.join(rows)}</table>"""


def save_html(run: RunResult, path: str | Path) -> None:
    Path(path).write_text(render_html(run))
