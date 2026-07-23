from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class RawPOLine(BaseModel):
    """A single line item as seen on a buyer portal (pre-normalization)."""

    raw_description: str
    raw_sku: Optional[str] = None
    quantity: float
    unit: Optional[str] = None


class RawPurchaseOrder(BaseModel):
    """Purchase order extracted from a buyer portal before SKU normalization."""

    buyer_name: Optional[str] = None
    po_number: str
    order_date: Optional[date] = None
    lines: list[RawPOLine] = Field(default_factory=list)
