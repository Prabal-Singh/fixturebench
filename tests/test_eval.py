import json
from pathlib import Path

import pytest

from fixturebench.eval.cases import build_goal, load_suite, resolve_cases
from fixturebench.eval.models import EvalDefaults
from fixturebench.eval.scorer import compare_po
from fixturebench.models.po import RawPurchaseOrder

ROOT = Path(__file__).resolve().parents[1]


def test_load_eval_suite() -> None:
    suite = load_suite(ROOT / "eval" / "cases.json")
    assert suite.version == 2
    assert len(suite.cases) >= 23
    assert {case.id for case in suite.cases} >= {
        "v1_po_1042",
        "v2_po_1042",
        "v3_po_1042",
        "v13_empty_orders",
        "v14_po_1042_lazy_accordion",
        "v20_po_1042_mfa",
        "v21_po_1042_virtualized",
    }


def test_resolve_cases_by_tag() -> None:
    suite = load_suite(ROOT / "eval" / "cases.json")
    cases = resolve_cases(suite, tags=["smoke"])
    assert len(cases) >= 2
    assert all("smoke" in case.tags for case in cases)


def test_resolve_cases_by_id() -> None:
    suite = load_suite(ROOT / "eval" / "cases.json")
    cases = resolve_cases(suite, case_ids=["v1_po_1042"])
    assert len(cases) == 1
    assert cases[0].portal == "v1"


def test_build_goal_from_template() -> None:
    suite = load_suite(ROOT / "eval" / "cases.json")
    goal = build_goal(suite.cases[0], suite.defaults)
    assert "PO-1042" in goal
    assert suite.defaults.email in goal


def test_compare_po_passes_on_match() -> None:
    fixture_path = ROOT / "tests" / "fixtures" / "expected_po_1042.json"
    with fixture_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    expected = RawPurchaseOrder.model_validate(payload)
    result = compare_po(expected, expected)
    assert result.passed
    assert result.mismatches == []


def test_compare_po_reports_mismatches() -> None:
    fixture_path = ROOT / "tests" / "fixtures" / "expected_po_1042.json"
    with fixture_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    expected = RawPurchaseOrder.model_validate(payload)
    actual = expected.model_copy(update={"buyer_name": "Wrong Buyer"})
    result = compare_po(actual, expected)
    assert not result.passed
    assert any("buyer_name" in mismatch for mismatch in result.mismatches)


def test_compare_po_line_unit_mismatch() -> None:
    defaults = EvalDefaults()
    v1_fixture = ROOT / "tests" / "fixtures" / "expected_po_1042.json"
    v2_fixture = ROOT / "tests" / "fixtures" / "expected_po_1042_v2.json"
    with v1_fixture.open(encoding="utf-8") as handle:
        v1 = RawPurchaseOrder.model_validate(json.load(handle))
    with v2_fixture.open(encoding="utf-8") as handle:
        v2 = RawPurchaseOrder.model_validate(json.load(handle))
    result = compare_po(v2, v1)
    assert not result.passed
    assert any("unit" in mismatch for mismatch in result.mismatches)
    assert defaults.max_steps == 12


def test_write_report_serializes_datetimes(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    from fixturebench.eval.models import EvalReport, EvalSummary
    from fixturebench.eval.report import utc_now, write_report

    started = datetime(2026, 7, 6, 12, 0, 0, tzinfo=timezone.utc)
    report = EvalReport(
        run_id="20260706T120000Z",
        started_at=started,
        finished_at=utc_now(),
        agent_name="test-agent",
        agent_metadata={"model": "test-model"},
        cases=[],
        summary=EvalSummary(
            total=0,
            passed=0,
            failed=0,
            agent_success_rate=0.0,
            extraction_accuracy=0.0,
            pass_rate=0.0,
            avg_steps=0.0,
            avg_total_duration_ms=0.0,
            avg_llm_duration_ms=0.0,
        ),
    )

    report_path = write_report(report, tmp_path)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    summary_payload = json.loads((tmp_path / report.run_id / "summary.json").read_text(encoding="utf-8"))

    assert isinstance(payload["started_at"], str)
    assert isinstance(summary_payload["finished_at"], str)
