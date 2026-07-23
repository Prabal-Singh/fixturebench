from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field, model_validator

from fixturebench.models.po import RawPurchaseOrder


class EvalTask(BaseModel):
    """Inputs passed to a browser agent for one eval case."""

    case_id: str
    portal_url: str
    goal: str
    po_number: str = ""
    max_steps: int = 12
    headless: bool = True
    email: str
    password: str
    screenshot_dir: Optional[Path] = None
    trace_dir: Optional[Path] = None

    @property
    def url(self) -> str:
        """Alias for portal_url — prefer this in new adapters."""
        return self.portal_url

    @property
    def target_id(self) -> str:
        """Alias for po_number — pack-agnostic target identifier."""
        return self.po_number


class AgentRunResult(BaseModel):
    """Minimal terminal outcome any browser agent should return."""

    success: bool
    po: Optional[RawPurchaseOrder] = None
    payload: Optional[Any] = None
    failure_reason: Optional[str] = None
    total_duration_ms: Optional[float] = None
    step_count: int = 0
    llm_duration_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _sync_payload_and_po(self) -> "AgentRunResult":
        if self.po is None and self.payload is not None:
            if isinstance(self.payload, RawPurchaseOrder):
                self.po = self.payload
            elif isinstance(self.payload, dict):
                self.po = RawPurchaseOrder.model_validate(self.payload)
        if self.payload is None and self.po is not None:
            self.payload = self.po
        return self


@runtime_checkable
class BrowserAgent(Protocol):
    """Plug-in interface for any browser agent implementation.

    Implement ``name`` + ``run(task)`` and FixtureBench handles the rest:
    environment lifecycle, case selection, scoring, and reports.
    """

    @property
    def name(self) -> str:
        ...

    def run(self, task: EvalTask) -> AgentRunResult:
        ...
