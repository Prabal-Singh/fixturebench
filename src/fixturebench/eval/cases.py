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

    email = case.email or defaults.email
    password = case.password or defaults.password

    if case.outcome == "confirm_empty":
        return (
            f"Log into the buyer portal using email {email} "
            f"and password {password}. "
            "Confirm there are no purchase orders to process and finish successfully "
            "without extracting any PO data."
        )

    if case.outcome == "acknowledge_po":
        return (
            f"Log into the buyer portal using email {email} and password {password}. "
            f"Open purchase order {case.po_number}, click Acknowledge PO to unlock and "
            "persist acknowledgement on the portal, extract the line items, and finish."
        )

    template = defaults.goal_template
    return template.format(email=email, password=password, po_number=case.po_number)


def load_expected_po(root: Path, case: EvalCase) -> RawPurchaseOrder | None:
    if case.outcome == "confirm_empty" or not case.expected_fixture:
        return None

    fixture_path = root / case.expected_fixture
    with fixture_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return RawPurchaseOrder.model_validate(payload)


def load_expected_state(root: Path, case: EvalCase) -> dict | None:
    if case.outcome != "acknowledge_po" or not case.expected_state:
        return None
    fixture_path = root / case.expected_state
    with fixture_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected state fixture must be an object: {fixture_path}")
    return payload


def case_max_steps(case: EvalCase, defaults: EvalDefaults) -> int:
    return case.max_steps if case.max_steps is not None else defaults.max_steps


def case_headless(case: EvalCase, defaults: EvalDefaults) -> bool:
    return case.headless if case.headless is not None else defaults.headless
