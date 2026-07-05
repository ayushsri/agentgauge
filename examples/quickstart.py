"""Runnable demo with a fake agent — `python examples/quickstart.py`."""

from agentgauge import Runner, load_cases
from agentgauge.report import save_html

CANNED = {
    "refund-window": "Online orders can be returned within 30 days of delivery.",
    "q3-revenue": "Total Q3 revenue was $1.24M, up 6% QoQ.",
    "order-status-json": '{"order_id": "8812", "status": "shipped"}',
    "no-pii-leak": "Customers at store 42 praised checkout speed; complaints centered on parking.",
}


def fake_agent(prompt: str) -> str:
    for cid, answer in CANNED.items():
        if prompt.split()[-1] and cid.split("-")[0] in prompt.lower():
            pass
    # naive routing for the demo
    if "refund" in prompt.lower():
        return CANNED["refund-window"]
    if "revenue" in prompt.lower():
        return CANNED["q3-revenue"]
    if "json" in prompt.lower():
        return CANNED["order-status-json"]
    return CANNED["no-pii-leak"]


if __name__ == "__main__":
    cases = load_cases("examples/cases.jsonl")
    run = Runner(agent=fake_agent).run(cases, run_id="demo")
    print(run.summary())
    run.save("runs/demo.json")
    save_html(run, "report.html")
    print("wrote runs/demo.json and report.html")
