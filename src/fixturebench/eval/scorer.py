from __future__ import annotations

from fixturebench.eval.models import POComparison
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
