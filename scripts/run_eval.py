#!/usr/bin/env python3
"""Run FixtureBench eval cases against a plugged-in browser agent.

Examples:
    python scripts/run_eval.py --list
    python scripts/run_eval.py --agent examples.stub_agent:StubAgent
    python scripts/run_eval.py --agent examples.stub_agent:StubAgent --case v1_po_1042
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fixturebench.eval.cases import load_suite
from fixturebench.eval.runner import EvalRunner


def _load_agent(spec: str):
    module_name, _, attr = spec.partition(":")
    if not attr:
        raise ValueError(f"Expected MODULE:CLASS, got {spec!r}")
    module = importlib.import_module(module_name)
    agent_cls = getattr(module, attr)
    return agent_cls()


def _print_summary(report) -> None:
    summary = report.summary
    print("=== Eval summary ===")
    print(f"run_id: {report.run_id}")
    print(f"agent:  {report.agent_name}")
    if report.agent_metadata:
        print(f"meta:   {report.agent_metadata}")
    print(
        f"passed: {summary.passed}/{summary.total} "
        f"(agent={summary.agent_success_rate:.0%}, "
        f"extraction={summary.extraction_accuracy:.0%})"
    )
    print(
        f"avg steps: {summary.avg_steps:.1f}, "
        f"avg total: {summary.avg_total_duration_ms:.0f} ms, "
        f"avg llm: {summary.avg_llm_duration_ms:.0f} ms"
    )

    print("\n=== Cases ===")
    for case in report.cases:
        status = "PASS" if case.passed else "FAIL"
        print(
            f"[{status}] {case.case_id} "
            f"steps={case.metrics.step_count} "
            f"total={case.metrics.total_duration_ms:.0f}ms "
            f"llm={case.metrics.llm_duration_ms:.0f}ms"
        )
        if case.po_comparison and case.po_comparison.mismatches:
            for mismatch in case.po_comparison.mismatches:
                print(f"  - {mismatch}")
        if case.failure_reason:
            print(f"  - {case.failure_reason}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FixtureBench eval suite")
    parser.add_argument(
        "--suite",
        default=str(ROOT / "eval" / "cases.json"),
        help="Path to eval case registry JSON",
    )
    parser.add_argument("--agent", help="Agent adapter as MODULE:CLASS")
    parser.add_argument("--case", action="append", dest="case_ids", help="Run one case id")
    parser.add_argument("--tag", action="append", dest="tags", help="Run cases with tag")
    parser.add_argument("--list", action="store_true", help="List cases and exit")
    parser.add_argument("--headed", action="store_true", help="Run browser headed")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "eval-results"),
        help="Directory for eval reports",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write report JSON to disk",
    )
    args = parser.parse_args()

    suite_path = Path(args.suite)
    suite = load_suite(suite_path)

    if args.list:
        for case in suite.cases:
            tags = ", ".join(case.tags) if case.tags else "-"
            print(f"{case.id}\tportal={case.portal}\tpo={case.po_number}\ttags={tags}")
        return 0

    if not args.agent:
        print("ERROR: --agent MODULE:CLASS is required unless --list is used", file=sys.stderr)
        return 2

    agent = _load_agent(args.agent)
    runner = EvalRunner(
        ROOT,
        agent,
        suite_path=suite_path,
        output_dir=Path(args.output_dir),
    )

    try:
        report = runner.run(
            case_ids=args.case_ids,
            tags=args.tags,
            headless=not args.headed,
            write_results=not args.no_write,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _print_summary(report)

    if not args.no_write:
        print(f"\nReport: {Path(args.output_dir) / report.run_id / 'report.json'}")

    if args.case_ids is None and args.tags is None:
        print(json.dumps(report.summary.model_dump(mode="json"), indent=2))

    return 0 if report.summary.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
