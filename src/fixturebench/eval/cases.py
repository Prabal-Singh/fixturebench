from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from fixturebench.eval.models import EvalCase, EvalDefaults, EvalSuite
from fixturebench.models.po import RawPurchaseOrder


def load_suite(path: Path) -> EvalSuite:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return EvalSuite.model_validate(payload)


def resolve_cases(
    suite: EvalSuite,
    *,
    case_ids: Optional[Iterable[str]] = None,
    tags: Optional[Iterable[str]] = None,
) -> list[EvalCase]:
    """Filter suite cases by id and/or tag intersection."""
    selected = list(suite.cases)
    id_set = set(case_ids) if case_ids else None
    tag_set = set(tags) if tags else None

    if id_set is not None:
        selected = [case for case in selected if case.id in id_set]
    if tag_set is not None:
        selected = [case for case in selected if tag_set.intersection(case.tags)]

    return selected


def build_goal(case: EvalCase, defaults: EvalDefaults) -> str:
    if case.goal:
        return case.goal

    template = defaults.goal_template
    email = case.email or defaults.email
    password = case.password or defaults.password
    return template.format(email=email, password=password, po_number=case.po_number)


def load_expected_po(root: Path, case: EvalCase) -> RawPurchaseOrder:
    fixture_path = root / case.expected_fixture
    with fixture_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return RawPurchaseOrder.model_validate(payload)


def case_max_steps(case: EvalCase, defaults: EvalDefaults) -> int:
    return case.max_steps if case.max_steps is not None else defaults.max_steps


def case_headless(case: EvalCase, defaults: EvalDefaults) -> bool:
    return case.headless if case.headless is not None else defaults.headless
