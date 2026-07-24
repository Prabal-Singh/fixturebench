from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from fixturebench.adapters.protocol import BrowserAgent, EvalTask
from fixturebench.eval.cases import (
    build_goal,
    case_headless,
    case_max_steps,
    load_expected_po,
    load_expected_state,
    load_suite,
    resolve_cases,
)
from fixturebench.eval.models import (
    EvalCase,
    EvalCaseMetrics,
    EvalCaseResult,
    EvalDefaults,
    EvalReport,
    EvalSummary,
    EvalSuite,
)
from fixturebench.eval.portal import ManagedPortal, PORTAL_SPECS
from fixturebench.eval.report import new_run_id, utc_now, write_report
from fixturebench.eval.scorer import compare_po, compare_portal_state, fetch_portal_state


class EvalRunner:
    """Run registered eval cases against any BrowserAgent adapter."""

    def __init__(
        self,
        agent: BrowserAgent,
        *,
        root: Optional[Path] = None,
        suite_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        screenshot_dir: Optional[Path] = None,
        trace_dir: Optional[Path] = None,
    ) -> None:
        from fixturebench.paths import default_root

        self.root = Path(root) if root is not None else default_root()
        self.agent = agent
        self.suite_path = suite_path or (self.root / "eval" / "cases.json")
        self.output_dir = output_dir or (Path.cwd() / "eval-results")
        self.screenshot_dir = screenshot_dir or (self.output_dir / "screenshots")
        self.trace_dir = trace_dir or (self.output_dir / "traces")

    def load_suite(self) -> EvalSuite:
        return load_suite(self.suite_path)

    def run(
        self,
        *,
        case_ids: Optional[Iterable[str]] = None,
        tags: Optional[Iterable[str]] = None,
        headless: Optional[bool] = None,
        write_results: bool = True,
    ) -> EvalReport:
        suite = self.load_suite()
        cases = resolve_cases(suite, case_ids=case_ids, tags=tags)
        if not cases:
            raise ValueError("No eval cases matched the requested filters")

        started_at = utc_now()
        case_results: list[EvalCaseResult] = []

        for case in cases:
            case_results.append(self._run_case(case, suite.defaults, headless=headless))

        finished_at = utc_now()
        agent_metadata = _merge_agent_metadata(case_results)
        report = EvalReport(
            run_id=new_run_id(started_at),
            started_at=started_at,
            finished_at=finished_at,
            agent_name=self.agent.name,
            agent_metadata=agent_metadata,
            cases=case_results,
            summary=_build_summary(case_results),
        )

        if write_results:
            write_report(report, self.output_dir)

        return report

    def _run_case(
        self,
        case: EvalCase,
        defaults: EvalDefaults,
        *,
        headless: Optional[bool],
    ) -> EvalCaseResult:
        expected = load_expected_po(self.root, case)
        task = _build_task(
            case,
            defaults,
            headless=headless,
            screenshot_dir=self.screenshot_dir / case.id,
            trace_dir=self.trace_dir / case.id,
        )

        if case.manage_portal and case.portal_url is None:
            with ManagedPortal(case.portal, self.root) as portal_url:
                task = task.model_copy(update={"portal_url": portal_url})
                agent_result = self.agent.run(task)
                return self._score_case(case, portal_url, expected, agent_result)

        portal_url = case.portal_url or _default_portal_url(case.portal)
        task = task.model_copy(update={"portal_url": portal_url})
        agent_result = self.agent.run(task)
        return self._score_case(case, portal_url, expected, agent_result)

    def _score_case(
        self,
        case: EvalCase,
        portal_url: str,
        expected,
        agent_result,
    ) -> EvalCaseResult:
        comparison = None
        state_comparison = None
        extraction_pass = False
        state_pass: bool | None = None
        failure_reason = agent_result.failure_reason

        if case.outcome == "confirm_empty":
            extraction_pass = agent_result.po is None
            passed = agent_result.success and extraction_pass
            if agent_result.success and not extraction_pass:
                failure_reason = failure_reason or "Expected no PO payload for empty-state case"
        elif case.outcome == "acknowledge_po":
            expected_state = load_expected_state(self.root, case)
            if agent_result.po is not None and expected is not None:
                comparison = compare_po(agent_result.po, expected)
                extraction_pass = comparison.passed
            if expected_state is not None:
                try:
                    actual_state = fetch_portal_state(portal_url, case.po_number)
                    state_comparison = compare_portal_state(actual_state, expected_state)
                    state_pass = state_comparison.passed
                except RuntimeError as exc:
                    state_pass = False
                    state_comparison = None
                    failure_reason = failure_reason or str(exc)
            passed = bool(
                agent_result.success and extraction_pass and state_pass is True
            )
            if agent_result.success and extraction_pass and state_pass is False:
                mismatches = (
                    "; ".join(state_comparison.mismatches)
                    if state_comparison and state_comparison.mismatches
                    else "portal state mismatch"
                )
                failure_reason = failure_reason or f"Write-back failed: {mismatches}"
            elif agent_result.success and not extraction_pass:
                mismatches = (
                    "; ".join(comparison.mismatches)
                    if comparison and comparison.mismatches
                    else "PO extraction mismatch"
                )
                failure_reason = failure_reason or mismatches
        elif agent_result.po is not None and expected is not None:
            comparison = compare_po(agent_result.po, expected)
            extraction_pass = comparison.passed
            passed = agent_result.success and extraction_pass
            if agent_result.success and not extraction_pass:
                failure_reason = failure_reason or (
                    "; ".join(comparison.mismatches) if comparison.mismatches else "PO mismatch"
                )
        else:
            passed = False

        metrics = _case_metrics(agent_result)

        return EvalCaseResult(
            case_id=case.id,
            portal=case.portal,
            portal_url=portal_url,
            po_number=case.po_number,
            agent_success=agent_result.success,
            extraction_pass=extraction_pass,
            state_pass=state_pass,
            passed=passed,
            metrics=metrics,
            failure_reason=failure_reason,
            po_comparison=comparison,
            state_comparison=state_comparison,
            agent_metadata=agent_result.metadata,
        )


def _build_task(
    case: EvalCase,
    defaults: EvalDefaults,
    *,
    headless: Optional[bool],
    screenshot_dir: Path,
    trace_dir: Path,
) -> EvalTask:
    resolved_headless = headless if headless is not None else case_headless(case, defaults)
    return EvalTask(
        case_id=case.id,
        portal_url="",
        goal=build_goal(case, defaults),
        po_number=case.po_number,
        max_steps=case_max_steps(case, defaults),
        headless=resolved_headless,
        email=case.email or defaults.email,
        password=case.password or defaults.password,
        screenshot_dir=screenshot_dir,
        trace_dir=trace_dir,
    )


def _default_portal_url(portal: str) -> str:
    default_port = PORTAL_SPECS[portal]["default_port"]
    return f"http://127.0.0.1:{default_port}"


def _case_metrics(agent_result) -> EvalCaseMetrics:
    step_count = agent_result.step_count
    total_duration_ms = agent_result.total_duration_ms or 0.0
    llm_duration_ms = agent_result.llm_duration_ms
    avg_step_duration_ms = total_duration_ms / step_count if step_count else 0.0
    avg_llm_duration_ms = llm_duration_ms / step_count if step_count else 0.0

    return EvalCaseMetrics(
        step_count=step_count,
        total_duration_ms=total_duration_ms,
        llm_duration_ms=llm_duration_ms,
        avg_step_duration_ms=avg_step_duration_ms,
        avg_llm_duration_ms=avg_llm_duration_ms,
    )


def _merge_agent_metadata(case_results: list[EvalCaseResult]) -> dict:
    merged: dict = {}
    for result in case_results:
        for key, value in result.agent_metadata.items():
            if key not in merged:
                merged[key] = value
    return merged


def _build_summary(case_results: list[EvalCaseResult]) -> EvalSummary:
    total = len(case_results)
    passed = sum(1 for result in case_results if result.passed)
    agent_successes = sum(1 for result in case_results if result.agent_success)
    extraction_passes = sum(1 for result in case_results if result.extraction_pass)

    return EvalSummary(
        total=total,
        passed=passed,
        failed=total - passed,
        agent_success_rate=agent_successes / total if total else 0.0,
        extraction_accuracy=extraction_passes / total if total else 0.0,
        pass_rate=passed / total if total else 0.0,
        avg_steps=sum(result.metrics.step_count for result in case_results) / total
        if total
        else 0.0,
        avg_total_duration_ms=sum(result.metrics.total_duration_ms for result in case_results)
        / total
        if total
        else 0.0,
        avg_llm_duration_ms=sum(result.metrics.llm_duration_ms for result in case_results) / total
        if total
        else 0.0,
    )
