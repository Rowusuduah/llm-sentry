"""CI/CD quality gate for LLM pipelines.

Run llm-sentry checks as part of your CI/CD pipeline.
Fails the build if AI quality drops below threshold.

Usage:
    python -m llmguardrail.ci_gate --config guardrail.json --threshold 0.7

Config file (guardrail.json):
    {
        "pipeline_name": "my_app",
        "checks": ["rag", "coherence"],
        "threshold": 0.7,
        "rag_queries": [
            ["What is X?", [["X is Y", 0.9]], "X is Y"]
        ]
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from llmguardrail import HealthStatus, ScanStore, scan


def run_gate(config_path: str, threshold: float | None = None, db_path: str | None = None) -> int:
    """Run CI gate check. Returns 0 for pass, 1 for fail."""
    config = json.loads(Path(config_path).read_text())

    pipeline_name = config.get("pipeline_name", "ci_check")
    checks = config.get("checks", [])
    gate_threshold = threshold or config.get("threshold", 0.7)

    # Build kwargs from config
    kwargs: dict = {}
    if "rag_queries" in config:
        kwargs["rag_queries"] = [
            (q, [(c, s) for c, s in chunks], answer)
            for q, chunks, answer in config["rag_queries"]
        ]
    if "coherence_traces" in config:
        kwargs["coherence_traces"] = [
            (steps, conclusion)
            for steps, conclusion in config["coherence_traces"]
        ]
    if "agent_task" in config:
        kwargs["agent_task"] = config["agent_task"]
    if "agent_actions" in config:
        kwargs["agent_actions"] = [
            (action, result) for action, result in config["agent_actions"]
        ]

    report = scan(pipeline_name=pipeline_name, checks=checks, **kwargs)

    # Print summary
    print("=" * 60)
    print("LLM SENTRY CI GATE")
    print("=" * 60)
    print(report.summary())
    print("=" * 60)
    print(f"Threshold: {gate_threshold:.0%}")
    print(f"Score:     {report.overall_score:.0%}")

    # Save to store if db_path provided
    if db_path:
        store = ScanStore(db_path)
        scan_id = store.save(report)
        trend = store.trend(pipeline_name, last_n=5)
        if len(trend) > 1:
            delta = trend[-1] - trend[-2]
            direction = "+" if delta >= 0 else ""
            print(f"Trend:     {direction}{delta:.0%} vs last run")
        print(f"Scan ID:   {scan_id}")
        store.close()

    passed = report.overall_score >= gate_threshold
    if passed:
        print("\nRESULT: PASS")
    else:
        print(f"\nRESULT: FAIL (score {report.overall_score:.0%} < threshold {gate_threshold:.0%})")
        if report.recommendations:
            print("\nRecommendations:")
            for r in report.recommendations[:5]:
                print(f"  - {r}")

    print("=" * 60)
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(
        prog="llm-sentry-gate",
        description="LLM Sentry CI/CD Quality Gate",
    )
    parser.add_argument("--config", required=True, help="Path to gate config JSON")
    parser.add_argument("--threshold", type=float, default=None, help="Override score threshold (0.0-1.0)")
    parser.add_argument("--db", default=None, help="SQLite db path for tracking history")

    args = parser.parse_args()
    sys.exit(run_gate(args.config, args.threshold, args.db))


if __name__ == "__main__":
    main()
