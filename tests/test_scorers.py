from agentgauge import (Contains, ExactMatch, JSONSchemaCheck,
                        NumericTolerance, Regex, Runner, Case, diff_runs)
from agentgauge.scorers import normalize_numbers


def test_exact_and_contains():
    assert ExactMatch("Yes").score(" yes ").passed
    assert Contains("30 days").score("Returns accepted within 30 DAYS.").passed
    assert not Contains("30 days").score("Returns within two weeks.").passed


def test_numeric_normalization():
    assert normalize_numbers("$1.2M and 3,500") == [1200000.0, 3500.0]
    assert NumericTolerance(1240000, rel_tol=0.05).score("revenue was $1.2M").passed
    assert not NumericTolerance(99, abs_tol=1).score("about 42 items").passed


def test_json_schema():
    check = JSONSchemaCheck({"type": "object", "required": ["status"]})
    assert check.score('```json\n{"status": "ok"}\n```').passed
    assert not check.score("not json at all").passed


def test_regex():
    assert Regex(r"\bshipped\b").score("Order was Shipped today").passed


def test_runner_isolates_crashes_and_diff():
    cases = [Case("a", "in", [Contains("ok")]), Case("b", "in", [Contains("ok")])]

    def good(_):
        return "ok"

    def flaky(prompt):
        raise RuntimeError("boom")

    base = Runner(good).run(cases, "base")
    cand_results = Runner(flaky).run(cases, "cand")
    assert base.pass_rate == 1.0
    assert cand_results.pass_rate == 0.0
    diff = diff_runs(base, cand_results)
    assert set(diff.regressions) == {"a", "b"}
    assert diff.has_regressions
