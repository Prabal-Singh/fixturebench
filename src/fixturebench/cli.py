"""FixtureBench CLI — plug in any browser agent and run evals.

Examples:
    fixturebench list
    fixturebench run --agent fixturebench.agents:StubAgent --case v1_po_1042
    fixturebench run --agent my_pkg.agent:MyAgent --tag smoke
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from fixturebench.eval.cases import load_suite
from fixturebench.eval.runner import EvalRunner
from fixturebench.paths import default_root


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fixturebench",
        description="Plug-and-play eval harness for browser agents",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="FixtureBench data root (auto-detected if omitted)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List eval cases")
    list_parser.add_argument("--suite", default=None, help="Path to cases.json")

    run_parser = sub.add_parser("run", help="Run eval cases against an agent")
    run_parser.add_argument("--agent", required=True, help="Agent adapter as MODULE:CLASS")
    run_parser.add_argument("--suite", default=None, help="Path to cases.json")
    run_parser.add_argument("--case", action="append", dest="case_ids", help="Run one case id")
    run_parser.add_argument("--tag", action="append", dest="tags", help="Run cases with tag")
    run_parser.add_argument("--headed", action="store_true", help="Run browser headed")
    run_parser.add_argument(
        "--output-dir",
        default=str(Path.cwd() / "eval-results"),
        help="Directory for eval reports",
    )
    run_parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write report JSON to disk",
    )

    args = parser.parse_args(argv)

    try:
        root = Path(args.root).resolve() if args.root else default_root()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    suite_path = Path(args.suite) if args.suite else (root / "eval" / "cases.json")
    suite = load_suite(suite_path)

    if args.command == "list":
        for case in suite.cases:
            tags = ", ".join(case.tags) if case.tags else "-"
            target = case.po_number or "-"
            print(f"{case.id}\tenv={case.portal}\ttarget={target}\ttags={tags}")
        return 0

    try:
        agent = _load_agent(args.agent)
    except (ImportError, AttributeError, ValueError) as exc:
        print(f"ERROR: could not load agent {args.agent!r}: {exc}", file=sys.stderr)
        return 2

    runner = EvalRunner(
        agent,
        root=root,
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
