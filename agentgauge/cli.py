"""CLI: `agentgauge diff` and `agentgauge report`."""

from __future__ import annotations

import argparse
import sys

from .regression import diff_runs
from .report import save_html
from .runner import RunResult


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="agentgauge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_diff = sub.add_parser("diff", help="compare two saved runs")
    p_diff.add_argument("baseline")
    p_diff.add_argument("candidate")
    p_diff.add_argument("--fail-on-regression", action="store_true")

    p_rep = sub.add_parser("report", help="render an HTML report")
    p_rep.add_argument("run")
    p_rep.add_argument("-o", "--out", default="report.html")

    args = parser.parse_args(argv)

    if args.cmd == "diff":
        diff = diff_runs(RunResult.load(args.baseline),
                         RunResult.load(args.candidate))
        print(diff.summary())
        return 1 if (args.fail_on_regression and diff.has_regressions) else 0

    if args.cmd == "report":
        run = RunResult.load(args.run)
        save_html(run, args.out)
        print(f"wrote {args.out} ({run.pass_rate:.0%} pass rate)")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
