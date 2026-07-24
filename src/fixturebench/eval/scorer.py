from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from fixturebench.eval.models import POComparison, StateComparison
from fixturebench.models.po import RawPOLine, RawPurchaseOrder


def compare_po(actual: RawPurchaseOrder, expected: RawPurchaseOrder) -> POComparison:
    """Compare extracted PO against a golden fixture."""
    mismatches: list[str] = []

    if actual.po_number != expected.po_number:
        mismatches.append(f"po_number: got {actual.po_number!r}, want {expected.po_number!r}")

    if actual.buyer_name != expected.buyer_name:
        mismatches.append(
            f"buyer_name: got {actual.buyer_name!r}, want {expected.buyer_name!r}"
        )

    if actual.order_date != expected.order_date:
        mismatches.append(
            f"order_date: got {actual.order_date!r}, want {expected.order_date!r}"
        )

    if len(actual.lines) != len(expected.lines):
        mismatches.append(
            f"line_count: got {len(actual.lines)}, want {len(expected.lines)}"
        )

    for index, (actual_line, expected_line) in enumerate(
        zip(actual.lines, expected.lines), start=1
    ):
        mismatches.extend(_compare_line(index, actual_line, expected_line))

    return POComparison(passed=len(mismatches) == 0, mismatches=mismatches)


def compare_portal_state(actual: dict[str, Any], expected: dict[str, Any]) -> StateComparison:
    """Compare portal server state against an expected write-back fixture."""
    mismatches: list[str] = []
    for key, want in expected.items():
        got = actual.get(key)
        if got != want:
            mismatches.append(f"state.{key}: got {got!r}, want {want!r}")
    return StateComparison(
        passed=len(mismatches) == 0,
        mismatches=mismatches,
        actual=actual,
        expected=expected,
    )


def fetch_portal_state(portal_url: str, po_number: str, *, timeout: float = 5.0) -> dict[str, Any]:
    """Read harness-only eval state from a running portal."""
    url = f"{portal_url.rstrip('/')}/api/eval/orders/{po_number}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Portal state fetch failed ({exc.code}): {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Portal state fetch failed: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"Portal state was not a JSON object: {payload!r}")
    return payload


def _compare_line(index: int, actual: RawPOLine, expected: RawPOLine) -> list[str]:
    mismatches: list[str] = []
    prefix = f"line[{index}]"

    if actual.raw_description != expected.raw_description:
        mismatches.append(
            f"{prefix}.raw_description: got {actual.raw_description!r}, "
            f"want {expected.raw_description!r}"
        )
    if actual.raw_sku != expected.raw_sku:
        mismatches.append(
            f"{prefix}.raw_sku: got {actual.raw_sku!r}, want {expected.raw_sku!r}"
        )
    if actual.quantity != expected.quantity:
        mismatches.append(
            f"{prefix}.quantity: got {actual.quantity!r}, want {expected.quantity!r}"
        )
    if actual.unit != expected.unit:
        mismatches.append(
            f"{prefix}.unit: got {actual.unit!r}, want {expected.unit!r}"
        )

    return mismatches
