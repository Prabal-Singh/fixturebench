from pathlib import Path

from fixturebench.eval.cases import build_goal, load_suite
from fixturebench.eval.models import EvalDefaults
from fixturebench.eval.portal import PORTAL_CHALLENGES, PORTAL_SPECS

ROOT = Path(__file__).resolve().parents[1]


def test_portal_registry_covers_v1_through_v13() -> None:
    expected = {f"v{i}" for i in range(1, 14)}
    assert set(PORTAL_SPECS) == expected
    assert len(PORTAL_CHALLENGES) == 13


def test_each_portal_server_file_exists() -> None:
    for version, spec in PORTAL_SPECS.items():
        server_path = ROOT / str(spec["server"])
        assert server_path.exists(), f"missing server for {version}"


def test_confirm_empty_goal_template() -> None:
    suite = load_suite(ROOT / "eval" / "cases.json")
    empty_case = next(case for case in suite.cases if case.id == "v13_empty_orders")
    goal = build_goal(empty_case, EvalDefaults())
    assert "no purchase orders" in goal.lower()
    assert empty_case.outcome == "confirm_empty"
